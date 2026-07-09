# Dependency injection

The capability this package exists for: wiring a `modern-di` `Container` into a
taskiq broker so task parameters resolve from it, scoped per task. Everything
lives in `modern_di_taskiq/main.py`; the public surface is `setup_di`,
`FromDI`, `fetch_di_container`, and `taskiq_message_provider`.

## Setup

`setup_di(broker, container)` is the single entry point. It:

1. Stores the container on `broker.state` under `_ROOT_CONTAINER_ATTR`
   (`"modern_di_container"`), a named constant — writer and reader stay in
   provable agreement instead of relying on a bare string literal.
2. Registers `taskiq_message_provider` (a `ContextProvider` binding
   `taskiq.TaskiqMessage` at `Scope.REQUEST`) so the current message is
   resolvable inside DI.
3. Wires `container.open` to `WORKER_STARTUP` and `container.close_async` to
   `WORKER_SHUTDOWN`, so the root container's lifecycle tracks the worker.

## Lifecycle

The worker owns resolution, so only the **worker** events are wired. Reopening
on `WORKER_STARTUP` is a no-op when the container is already open (a fresh
`Container` is open on construction) and lets a second worker cycle — a restart,
a test re-entry — reopen a container closed on the previous `WORKER_SHUTDOWN`
instead of raising `ContainerClosedError`.

## Per-task scope

taskiq resolves a generator `TaskiqDepends` **once per task** and shares the
yielded value across every dependent. `build_di_container` exploits this: it
builds one `Scope.REQUEST` child container per task — seeded with the
`TaskiqMessage` as context — `yield`s it, and closes it in `finally`. Every
`FromDI` parameter in a task therefore shares one child, and the child is closed
after the task completes, including when the task raises (taskiq throws the task
exception into the generator at the `yield`).

## Resolution

`FromDI(dependency, *, use_cache=True)` returns a taskiq `TaskiqDepends` wrapping
a frozen `Dependency`. At resolution time `Dependency.__call__` receives the
per-task child (via `TaskiqDepends(build_di_container)`) and resolves through it
with `resolve_dependency`, which dispatches on the argument kind:

- an `AbstractProvider` → `resolve_provider(...)`,
- a bare `type` → `resolve(...)`.

`Dependency` is the deep part of the seam — the provider-vs-type branch and the
container lookup sit behind a single `__call__`. `FromDI` is just its constructor.
