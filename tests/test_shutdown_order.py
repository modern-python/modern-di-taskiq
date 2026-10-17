import collections.abc

import pytest
from modern_di import Container, Group, Scope, providers
from taskiq import AsyncBroker, BrokerMessage, InMemoryBroker, TaskiqEvents, TaskiqMiddleware, TaskiqState

from modern_di_taskiq import setup_di


class Pool:
    pass


class StubBroker(AsyncBroker):
    def __init__(self) -> None:
        super().__init__()
        self.is_worker_process = True

    async def kick(self, message: BrokerMessage) -> None:  # pragma: no cover
        pass

    async def listen(self) -> collections.abc.AsyncGenerator[bytes]:  # pragma: no cover
        yield b""


def _container(events: list[str]) -> Container:
    class Resources(Group):
        pool = providers.Factory(
            Pool, scope=Scope.APP, cache=providers.CacheSettings(finalizer=lambda _: events.append("finalized"))
        )

    return Container(groups=[Resources])


def _use(container: Container, events: list[str], label: str) -> None:
    container.resolve(Pool)
    events.append(label)


class UserMiddleware(TaskiqMiddleware):
    def __init__(self, container: Container, events: list[str], label: str) -> None:
        super().__init__()
        self.container = container
        self.events = events
        self.label = label

    async def shutdown(self) -> None:
        _use(self.container, self.events, self.label)


def _register_user_code(broker: AsyncBroker, container: Container, events: list[str], label: str) -> None:
    async def hook(_state: TaskiqState) -> None:
        _use(container, events, f"{label} hook")

    broker.add_event_handler(TaskiqEvents.WORKER_SHUTDOWN, hook)
    broker.add_middlewares(UserMiddleware(container, events, f"{label} middleware"))


async def test_root_closes_after_all_shutdown_handlers_and_middlewares() -> None:
    events: list[str] = []
    broker = StubBroker()
    container = _container(events)
    _register_user_code(broker, container, events, "before")
    setup_di(broker, container)
    _register_user_code(broker, container, events, "after")

    await broker.startup()
    container.resolve(Pool)
    await broker.shutdown()

    assert events == ["before hook", "after hook", "before middleware", "after middleware", "finalized"]
    assert container.closed is True


async def test_root_closes_after_a_middleware_added_after_startup() -> None:
    events: list[str] = []
    broker = StubBroker()
    container = setup_di(broker, _container(events))

    await broker.startup()
    broker.add_middlewares(UserMiddleware(container, events, "late middleware"))
    container.resolve(Pool)
    await broker.shutdown()

    assert events == ["late middleware", "finalized"]


async def test_root_closes_once_per_cycle_without_duplicate_middlewares() -> None:
    events: list[str] = []
    broker = StubBroker()
    container = setup_di(broker, _container(events))
    _register_user_code(broker, container, events, "user")

    for _ in range(2):
        await broker.startup()
        middleware_count = len(broker.middlewares)
        container.resolve(Pool)
        await broker.shutdown()
        assert len(broker.middlewares) == middleware_count
        assert container.closed is True

    assert events == ["user hook", "user middleware", "finalized"] * 2


async def test_root_closes_once_when_the_broker_skips_middleware_shutdown() -> None:
    events: list[str] = []
    broker = InMemoryBroker()
    container = setup_di(broker, _container(events))

    async def hook(_state: TaskiqState) -> None:
        _use(container, events, "hook")

    broker.add_event_handler(TaskiqEvents.WORKER_SHUTDOWN, hook)

    for _ in range(2):
        await broker.startup()
        container.resolve(Pool)
        await broker.shutdown()
        assert container.closed is True

    assert events == ["hook", "finalized"] * 2


async def test_root_closes_when_shutdown_runs_without_startup() -> None:
    events: list[str] = []
    broker = StubBroker()
    container = setup_di(broker, _container(events))
    container.resolve(Pool)

    await broker.shutdown()

    assert container.closed is True
    assert events == ["finalized"]


@pytest.mark.parametrize("broker_type", [StubBroker, InMemoryBroker])
async def test_manage_lifespan_false_adds_no_middleware_and_keeps_the_root_open(broker_type: type[AsyncBroker]) -> None:
    events: list[str] = []
    broker = broker_type()
    container = setup_di(broker, _container(events), manage_lifespan=False)
    container.resolve(Pool)

    await broker.startup()
    assert broker.middlewares == []
    await broker.shutdown()

    assert container.closed is False
    assert events == []
