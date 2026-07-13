import dataclasses
import typing

import taskiq
from modern_di import Container, Scope, integrations, providers
from taskiq import AsyncBroker, Context, TaskiqDepends, TaskiqEvents, TaskiqState


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


T_co = typing.TypeVar("T_co", covariant=True)


async def build_di_container(
    context: typing.Annotated[Context, TaskiqDepends()],
) -> typing.AsyncIterator[Container]:
    match = integrations.bind(taskiq_message_provider, context.message)
    async with fetch_di_container(context.broker).build_child_container(
        scope=match.scope, context=match.context
    ) as container:
        yield container


@dataclasses.dataclass(slots=True, frozen=True)
class Dependency(typing.Generic[T_co]):
    marker: integrations.Marker[T_co]

    async def __call__(self, request_container: typing.Annotated[Container, TaskiqDepends(build_di_container)]) -> T_co:
        return self.marker.resolve(request_container)


def FromDI(  # noqa: N802
    dependency: providers.AbstractProvider[T_co] | type[T_co], *, use_cache: bool = True
) -> T_co:
    return typing.cast(T_co, TaskiqDepends(Dependency(integrations.Marker(dependency)), use_cache=use_cache))
