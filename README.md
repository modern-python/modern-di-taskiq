# modern-di-taskiq

[Modern-DI](https://github.com/modern-python/modern-di) integration for [taskiq](https://taskiq-python.github.io).

## Quickstart

```python
import typing

from modern_di import Container, Group, Scope, providers
from modern_di_taskiq import FromDI, setup_di
from taskiq import InMemoryBroker


class Settings:
    def __init__(self) -> None:
        self.greeting = "hello"


class Dependencies(Group):
    settings = providers.Factory(scope=Scope.APP, creator=Settings)


broker = InMemoryBroker()
setup_di(broker, Container(groups=[Dependencies], validate=True))


@broker.task
async def greet(name: str, settings: typing.Annotated[Settings, FromDI(Dependencies.settings)]) -> str:
    return f"{settings.greeting}, {name}"
```

See the [documentation](https://modern-di.modern-python.org) for the full guide.
