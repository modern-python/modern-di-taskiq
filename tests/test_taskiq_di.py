import typing

from modern_di import Container, Group, Scope, providers
from taskiq import InMemoryBroker

from modern_di_taskiq import FromDI, setup_di
from tests.dependencies import Dependencies, DependentCreator, SimpleCreator


async def test_resolves_app_request_and_context(broker: InMemoryBroker) -> None:
    # Explicit startup/shutdown (not `async with broker`) so the suite runs on
    # the whole taskiq>=0.11 floor — InMemoryBroker gained async-context-manager
    # support only in 0.12.3, and the integration itself needs neither.
    @broker.task(task_name="my_task")
    async def my_task(
        app_instance: typing.Annotated[SimpleCreator, FromDI(SimpleCreator)],
        request_instance: typing.Annotated[DependentCreator, FromDI(Dependencies.request_factory)],
        task_name: typing.Annotated[str, FromDI(Dependencies.task_name)],
    ) -> dict[str, typing.Any]:
        return {
            "app_ok": isinstance(app_instance, SimpleCreator),
            "request_ok": isinstance(request_instance, DependentCreator),
            # a plain (uncached) Factory yields a fresh instance each resolve
            "distinct": request_instance.dep1 is not app_instance,
            "task_name": task_name,
        }

    await broker.startup()
    try:
        # my_task's params are all TaskiqDepends-injected (no caller-supplied
        # positional/keyword args), but ty's kiq() overloads are typed against the
        # decorated function's full ParamSpec, which doesn't know that.
        result = await (await my_task.kiq()).wait_result()  # ty: ignore[no-matching-overload]
    finally:
        await broker.shutdown()

    assert result.is_err is False
    data = result.return_value
    assert data["app_ok"] is True
    assert data["request_ok"] is True
    assert data["distinct"] is True
    assert data["task_name"] == "my_task"


async def test_per_task_child_shared_within_task_isolated_across_tasks(broker: InMemoryBroker) -> None:
    """INVARIANT: one per-task child per task execution, shared by its parameters, never across tasks.

    Broken by anything that stops the container builder being resolved exactly once per task:
    taking the child with ``use_cache=False``, hoisting it out to broker or worker lifetime to save
    an allocation, or moving it under a middleware that keys children by anything coarser than a
    single execution. Sharing within the task is what makes a cached REQUEST-scoped provider mean
    one instance per task; isolation across tasks is what stops one task's message context, cached
    values and finalizers leaking into the next task the worker picks up.

    The two parameters name *different* providers deliberately. Two parameters naming the same one
    collapse into a single taskiq dependency node, resolved once whatever the child count, so such a
    test would stay green while every parameter got its own child.
    """

    @broker.task(task_name="shared")
    async def collect(
        direct: typing.Annotated[SimpleCreator, FromDI(Dependencies.request_singleton)],
        holder: typing.Annotated[DependentCreator, FromDI(Dependencies.request_singleton_holder)],
    ) -> tuple[bool, SimpleCreator]:
        return (direct is holder.dep1, direct)

    await broker.startup()
    try:
        r1 = await (await collect.kiq()).wait_result()  # ty: ignore[no-matching-overload]
        r2 = await (await collect.kiq()).wait_result()  # ty: ignore[no-matching-overload]
    finally:
        await broker.shutdown()

    assert r1.is_err is False
    assert r2.is_err is False
    shared1, inst1 = r1.return_value
    shared2, inst2 = r2.return_value
    assert shared1 is True  # two FromDI params in one task share ONE per-task child
    assert shared2 is True
    assert inst1 is not inst2  # each task gets its own child (cross-task isolation)


async def test_per_task_child_closed_on_task_error() -> None:
    """INVARIANT: the per-task child is closed when the task raises, not only when it returns.

    Broken by closing the child anywhere but the exit of the ``async with`` in the generator
    dependency -- after the ``yield`` without a try, or from a caller that only runs on the success
    path. taskiq throws the task's exception into the generator at the ``yield``, so the error path
    is the one that silently regresses: a worker survives failing tasks, so a finalizer that stops
    running on errors leaks a connection per failure until the process dies rather than at once.
    """
    teardowns: list[str] = []

    class Boom(Group):
        resource = providers.Factory(
            scope=Scope.REQUEST,
            creator=SimpleCreator,
            kwargs={"dep1": "x"},
            bound_type=None,
            cache=providers.CacheSettings(finalizer=lambda _: teardowns.append("closed")),
        )

    broker = InMemoryBroker()
    setup_di(broker, Container(groups=[Boom]))

    @broker.task(task_name="boom")
    async def boom(_res: typing.Annotated[SimpleCreator, FromDI(Boom.resource)]) -> None:
        msg = "kaboom"
        raise ValueError(msg)

    await broker.startup()
    try:
        result = await (await boom.kiq()).wait_result()  # ty: ignore[no-matching-overload]
    finally:
        await broker.shutdown()

    assert result.is_err is True  # the task raised
    assert teardowns == ["closed"]  # per-task child was still closed (finalizer ran) on the error path
