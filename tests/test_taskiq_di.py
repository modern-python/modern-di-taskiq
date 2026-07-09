import typing

from taskiq import InMemoryBroker

from modern_di_taskiq import FromDI
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
