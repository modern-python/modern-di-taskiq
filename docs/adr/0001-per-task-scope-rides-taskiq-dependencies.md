# Per-task scope rides a taskiq generator dependency, not a middleware

The per-task child container is built by `build_di_container`, an async generator `TaskiqDepends`;
no `TaskiqMiddleware` is shipped. A middleware is the obvious place to hang a per-unit-of-work
scope and is what Dishka's taskiq integration does, so the option keeps resurfacing, but taskiq
already provides the contract: under the default `use_cache=True` a generator dependency resolves
once per task, its yielded value is shared by every dependent, and taskiq throws the task's
exception into it at the `yield`, so the child closes on the error path too. Taking it as a
dependency is also lazy, since a task with no `FromDI` parameter builds no child; it needs no
task-id-keyed registry to leak; and it needs no installation step beyond `setup_di`. A middleware
would only add a second mechanism, because `FromDI` parameters still need a container handed to
them at resolve time.
