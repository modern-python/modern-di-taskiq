import typing

import taskiq
from modern_di import Container, Scope, providers
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState


taskiq_message_provider = providers.ContextProvider(taskiq.TaskiqMessage, scope=Scope.REQUEST)

# The root container lives on ``broker.state`` under this named attribute. One
# writer (``setup_di``), one reader (``fetch_di_container``) — naming it keeps
# them in provable agreement instead of relying on a bare string literal.
_ROOT_CONTAINER_ATTR = "modern_di_container"

_CONNECTION_PROVIDERS = (taskiq_message_provider,)


def setup_di(broker: AsyncBroker, container: Container) -> Container:
    setattr(broker.state, _ROOT_CONTAINER_ATTR, container)
    container.add_providers(*_CONNECTION_PROVIDERS)

    def _open_root(_state: TaskiqState) -> None:
        container.open()

    async def _close_root(_state: TaskiqState) -> None:
        await container.close_async()

    broker.add_event_handler(TaskiqEvents.WORKER_STARTUP, _open_root)
    broker.add_event_handler(TaskiqEvents.WORKER_SHUTDOWN, _close_root)
    return container


def fetch_di_container(broker: AsyncBroker) -> Container:
    return typing.cast(Container, getattr(broker.state, _ROOT_CONTAINER_ATTR))
