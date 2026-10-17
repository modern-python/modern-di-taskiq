import typing

from modern_di import Container, Group, Scope, providers
from taskiq import AsyncTaskiqDecoratedTask, InMemoryBroker

import modern_di_taskiq
from modern_di_taskiq import FromDI, fetch_di_container, setup_di
from tests.dependencies import Dependencies, SimpleCreator


def test_fetch_returns_the_same_container(broker: InMemoryBroker) -> None:
    assert isinstance(fetch_di_container(broker), Container)


def test_setup_di_returns_the_container() -> None:
    broker_ = InMemoryBroker()
    container = Container(groups=[Dependencies])
    assert modern_di_taskiq.setup_di(broker_, container) is container


async def test_startup_opens_and_shutdown_closes(broker: InMemoryBroker) -> None:
    container = fetch_di_container(broker)
    await broker.startup()
    assert container.closed is False
    await broker.shutdown()
    assert container.closed is True


async def test_restart_reopens_without_error(broker: InMemoryBroker) -> None:
    """INVARIANT: a second worker cycle reopens the root container instead of raising.

    Broken by making the ``WORKER_STARTUP`` handler conditional, or by dropping it on the grounds
    that a fresh ``Container`` is already open -- which it is, so the first cycle passes either way
    and the regression only shows on the second. Worker processes restart: on redeploy, after a
    crash, and between two ``startup()``/``shutdown()`` pairs in one test session. Without the
    reopen the container closed by the previous shutdown stays closed and every task fails.
    """
    container = fetch_di_container(broker)
    await broker.startup()
    await broker.shutdown()
    assert container.closed is True
    await broker.startup()  # second cycle must not raise ContainerClosedError
    assert container.closed is False
    await broker.shutdown()


def _unmanaged_broker(
    teardowns: list[str],
) -> tuple[InMemoryBroker, Container, AsyncTaskiqDecoratedTask[..., typing.Any]]:
    class Resources(Group):
        app_resource = providers.Factory(
            scope=Scope.APP,
            creator=SimpleCreator,
            kwargs={"dep1": "app"},
            bound_type=None,
            cache=providers.CacheSettings(finalizer=lambda _: teardowns.append("app")),
        )
        task_resource = providers.Factory(
            scope=Scope.REQUEST,
            creator=SimpleCreator,
            kwargs={"dep1": "task"},
            bound_type=None,
            cache=providers.CacheSettings(finalizer=lambda _: teardowns.append("task")),
        )

    broker = InMemoryBroker()
    container = setup_di(broker, Container(groups=[Resources]), manage_lifespan=False)

    @broker.task(task_name="use_resources")
    async def use_resources(
        app_resource: typing.Annotated[SimpleCreator, FromDI(Resources.app_resource)],
        task_resource: typing.Annotated[SimpleCreator, FromDI(Resources.task_resource)],
    ) -> str:
        return f"{app_resource.dep1}+{task_resource.dep1}"

    return broker, container, use_resources


async def test_manage_lifespan_false_leaves_the_root_open_across_a_worker_cycle() -> None:
    teardowns: list[str] = []
    broker, container, use_resources = _unmanaged_broker(teardowns)

    await broker.startup()
    result = await (await use_resources.kiq()).wait_result()
    await broker.shutdown()

    assert result.is_err is False
    assert container.closed is False
    assert "app" not in teardowns


async def test_manage_lifespan_false_still_builds_and_closes_the_per_task_child() -> None:
    teardowns: list[str] = []
    broker, _container, use_resources = _unmanaged_broker(teardowns)

    await broker.startup()
    result = await (await use_resources.kiq()).wait_result()
    await broker.shutdown()

    assert result.return_value == "app+task"
    assert teardowns == ["task"]


async def test_manage_lifespan_false_lets_the_caller_own_the_root() -> None:
    teardowns: list[str] = []
    broker, container, use_resources = _unmanaged_broker(teardowns)

    async with container:
        await broker.startup()
        result = await (await use_resources.kiq()).wait_result()
        await broker.shutdown()
        assert teardowns == ["task"]

    assert result.is_err is False
    assert container.closed is True
    assert teardowns == ["task", "app"]
