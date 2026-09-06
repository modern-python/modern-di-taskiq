from modern_di import Container
from taskiq import InMemoryBroker

import modern_di_taskiq
from modern_di_taskiq import fetch_di_container
from tests.dependencies import Dependencies


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
