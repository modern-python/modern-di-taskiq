# modern-di-taskiq

A [`modern-di`](https://github.com/modern-python/modern-di) integration for
[taskiq](https://taskiq-python.github.io): it attaches a container to a taskiq broker, ties that
container's lifecycle to the worker, and resolves task parameters from a child container built for
each task.

## Language

A term is listed only when there is a synonym to reject, or a meaning subtle enough that code and
docs must agree on it. General programming vocabulary does not belong here, however heavily this
package uses it.

The domain terms are `modern-di`'s — `Container`, `Provider`, `Group`, `Scope`, `Resolution`,
`Override` — and taskiq's — broker, worker, task, message, middleware, result backend. Those
projects are the authority for all of them; nothing here redefines one. The two below are this
package's own.

**Root container**:
The `Container` that `setup_di` attaches to `broker.state`: the one a caller constructs and hands
in, the one `fetch_di_container` returns, and the one the worker's startup and shutdown events open
and close.
_Avoid_: APP-scope container — that names a scope where what matters is the position at the top of
the tree, and `Scope.APP` is `modern-di`'s word for a band in the hierarchy, not for this object.

**Per-task child**:
The child container built for one task execution, carrying that task's `TaskiqMessage` as context.
Exactly one exists per task: every `FromDI` parameter in a task shares it, no two tasks share one,
and it is closed when the task ends — including when the task raises.
_Avoid_: request child — `REQUEST` is the scope it sits at, but nothing here is a request; the unit
of work is a task.
