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


async def test_request_child_shared_within_task_isolated_across_tasks(broker: InMemoryBroker) -> None:
    @broker.task(task_name="shared")
    async def collect(
        a: typing.Annotated[SimpleCreator, FromDI(Dependencies.request_singleton)],
        b: typing.Annotated[SimpleCreator, FromDI(Dependencies.request_singleton)],
    ) -> tuple[bool, SimpleCreator]:
        return (a is b, a)

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
    assert shared1 is True  # two FromDI params in one task share ONE request child
    assert shared2 is True
    assert inst1 is not inst2  # each task gets its own child (cross-task isolation)


async def test_request_child_closed_on_task_error() -> None:
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
    setup_di(broker, Container(groups=[Boom], validate=True))

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
