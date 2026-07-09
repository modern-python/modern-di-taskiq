import dataclasses

import taskiq
from modern_di import Group, Scope, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class SimpleCreator:
    dep1: str


@dataclasses.dataclass(kw_only=True, slots=True)
class DependentCreator:
    dep1: SimpleCreator


def fetch_task_name(message: taskiq.TaskiqMessage | None = None) -> str:
    return message.task_name if message else ""


class Dependencies(Group):
    app_factory = providers.Factory(creator=SimpleCreator, kwargs={"dep1": "original"})
    request_factory = providers.Factory(scope=Scope.REQUEST, creator=DependentCreator, bound_type=None)
    task_name = providers.Factory(scope=Scope.REQUEST, creator=fetch_task_name)
