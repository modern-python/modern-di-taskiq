# Per-task scope rides a taskiq generator dependency, not a middleware

**Decision:** the per-task child is built by a generator `TaskiqDepends` (`build_di_container`); we
will not ship a `TaskiqMiddleware` that opens and closes a container around every task.

A middleware is the obvious place to hang a per-unit-of-work scope, and it is what Dishka's taskiq
integration does, so the option comes back on its own. It was rejected because taskiq already
provides the exact contract: a generator dependency is resolved **once per task** under the default
`use_cache=True`, its yielded value is shared by every dependent in that task, and it is finalized
after the task completes — including when the task raises, because taskiq throws the task's
exception into the generator at the `yield`. That is child-container-per-unit-of-work, already
built.

Taking it as a dependency rather than a middleware buys three things a middleware cannot. It is
**lazy**: a task with no `FromDI` parameter resolves no dependency and therefore builds no child, so
a broker with one wired task pays nothing on the others. It needs **no registry**: the child reaches
the parameters through taskiq's own dependency cache, so there is nothing keyed by task id to
populate, look up, and clean up, and nothing to leak if a task dies between the two halves of a
middleware. And it requires **no installation step beyond `setup_di`** — a middleware would have to
be registered on the broker as well, giving a second way to get the wiring half-done.

The middleware also fails the deletion test in reverse: adding one would not remove the generator
dependency, because `FromDI` parameters still need a container handed to them at resolve time. It
would be a second mechanism layered over the one that already works.

**Revisit trigger:** taskiq changes the caching or finalization semantics of generator dependencies
— a yielded value no longer shared across a task's parameters, or a finalizer no longer run on the
error path — or a required feature genuinely needs to act before the first `FromDI` parameter is
resolved (per-task container setup that must happen even for tasks that inject nothing).
