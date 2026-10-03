<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"  srcset="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-taskiq/lockup-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-taskiq/lockup-light.svg">
    <img alt="modern-di-taskiq" src="https://raw.githubusercontent.com/modern-python/.github/main/brand/projects/modern-di-taskiq/lockup.png" width="420">
  </picture>
</p>

[![PyPI version](https://img.shields.io/pypi/v/modern-di-taskiq.svg)](https://pypi.org/project/modern-di-taskiq/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/modern-di-taskiq.svg)](https://pypi.org/project/modern-di-taskiq/)
[![Downloads](https://static.pepy.tech/badge/modern-di-taskiq/month)](https://pepy.tech/projects/modern-di-taskiq)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/modern-python/modern-di-taskiq/actions/workflows/ci.yml)
[![CI](https://github.com/modern-python/modern-di-taskiq/actions/workflows/ci.yml/badge.svg)](https://github.com/modern-python/modern-di-taskiq/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/modern-python/modern-di-taskiq.svg)](https://github.com/modern-python/modern-di-taskiq/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/modern-di-taskiq)](https://github.com/modern-python/modern-di-taskiq/stargazers)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

[modern-di](https://github.com/modern-python/modern-di) integration for [taskiq](https://taskiq-python.github.io).

Full guide: [taskiq integration docs](https://modern-di.modern-python.org/integrations/taskiq/)

Usage example: [examples/](https://github.com/modern-python/modern-di-taskiq/tree/main/examples)

## Installation

```bash
uv add modern-di-taskiq      # or: pip install modern-di-taskiq
```

## Usage

`setup_di` stores the container on `broker.state` and registers `WORKER_STARTUP`/`WORKER_SHUTDOWN` handlers that open/close it. `FromDI` resolves a provider (or type) into a task parameter through a taskiq dependency, which builds a `Scope.REQUEST` child container for the task and closes it when the task finishes. No per-task decorator is needed.

```python
import typing

from modern_di import Container, Group, Scope, providers
from modern_di_taskiq import FromDI, setup_di
from taskiq import InMemoryBroker


class Settings:
    def __init__(self) -> None:
        self.greeting = "hello"


class Greeter:
    def __init__(self, settings: Settings) -> None:  # auto-injected by type
        self._settings = settings

    def greet(self, name: str) -> str:
        return f"{self._settings.greeting}, {name}"


class AppGroup(Group):
    settings = providers.Factory(Settings, scope=Scope.APP, cache=True)
    greeter = providers.Factory(Greeter, scope=Scope.REQUEST)


broker = InMemoryBroker()
container = Container(groups=[AppGroup])
setup_di(broker, container)
container.validate()  # optional fail-fast; must come after setup_di registers its providers


@broker.task
async def greet(
    name: str,
    greeter: typing.Annotated[Greeter, FromDI(Greeter)],  # resolve by type
) -> str:
    return greeter.greet(name)
```

The `WORKER_STARTUP`/`WORKER_SHUTDOWN` events fire when the broker's worker process starts and stops, so a script that calls tasks directly (like `InMemoryBroker` in a test) must drive the container lifecycle itself, for example with `async with broker: ...`. Providers resolve synchronously, but the per-task `Scope.REQUEST` child is closed with `close_async()`, so REQUEST-scoped providers can have async finalizers. `taskiq.TaskiqMessage` is resolvable within DI via the pre-built `taskiq_message_provider` context provider.

## API

| Symbol | Description |
|---|---|
| `setup_di(broker, container)` | Stores the root container on `broker.state`, opens/closes it on worker startup/shutdown, and registers `taskiq_message_provider`. Returns the container |
| `FromDI(dependency, *, use_cache=True)` | taskiq dependency that resolves a provider instance or a type from the task's `Scope.REQUEST` child container, building that child on first use; use it as `Annotated[T, FromDI(...)]` in task signatures. `use_cache` is passed to `TaskiqDepends`. Raises `RuntimeError` naming `setup_di` when a task reaches it without `setup_di` called |
| `fetch_di_container(broker)` | Returns the root container attached to the taskiq broker |
| `taskiq_message_provider` | `ContextProvider` for the current `taskiq.TaskiqMessage` (`REQUEST` scope) |

## 📦 [PyPI](https://pypi.org/project/modern-di-taskiq)

## 📝 [License](https://github.com/modern-python/modern-di-taskiq/blob/main/LICENSE)

## Part of `modern-python`

Built on [`modern-di`](https://github.com/modern-python/modern-di), a dependency-injection framework with an IoC container and scopes.

Browse the full list of templates and libraries in
[`modern-python`](https://github.com/modern-python); the org profile has the categorized index.
