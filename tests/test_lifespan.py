from modern_di import Container
from taskiq import InMemoryBroker

import modern_di_taskiq
from modern_di_taskiq import fetch_di_container
from tests.dependencies import Dependencies


def test_fetch_returns_the_same_container(broker: InMemoryBroker) -> None:
    assert isinstance(fetch_di_container(broker), Container)


def test_setup_di_returns_the_container() -> None:
    broker_ = InMemoryBroker()
    container = Container(groups=[Dependencies], validate=True)
    assert modern_di_taskiq.setup_di(broker_, container) is container


async def test_startup_opens_and_shutdown_closes(broker: InMemoryBroker) -> None:
    container = fetch_di_container(broker)
    await broker.startup()
    assert container.closed is False
    await broker.shutdown()
    assert container.closed is True


async def test_restart_reopens_without_error(broker: InMemoryBroker) -> None:
    container = fetch_di_container(broker)
    await broker.startup()
    await broker.shutdown()
    assert container.closed is True
    await broker.startup()  # second cycle must not raise ContainerClosedError
    assert container.closed is False
    await broker.shutdown()
