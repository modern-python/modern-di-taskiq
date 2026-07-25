# Minimal modern-di + taskiq example.
# run: taskiq worker examples.app:broker  (then trigger via `await greet.kiq("world")`)
import typing

from modern_di import Container, Group, Scope, providers
from taskiq import InMemoryBroker

from modern_di_taskiq import FromDI, setup_di


class Settings:
    def __init__(self) -> None:
        self.greeting = "Hello"


class Greeter:
    def __init__(self, settings: Settings) -> None:  # auto-injected by type
        self._settings = settings

    def greet(self, name: str) -> str:
        return f"{self._settings.greeting}, {name}!"


class AppGroup(Group):
    settings = providers.Factory(Settings, scope=Scope.APP, cache=True)
    greeter = providers.Factory(Greeter, scope=Scope.REQUEST)


broker = InMemoryBroker()
container = Container(groups=[AppGroup], validate=True)
setup_di(broker, container)


@broker.task
async def greet(
    name: str,
    greeter: typing.Annotated[Greeter, FromDI(Greeter)],
) -> str:
    return greeter.greet(name)
