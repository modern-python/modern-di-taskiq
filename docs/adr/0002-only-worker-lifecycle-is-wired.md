# `setup_di` wires only the worker lifecycle events

`setup_di` registers handlers for `WORKER_STARTUP` and `WORKER_SHUTDOWN` only and leaves
`CLIENT_STARTUP` / `CLIENT_SHUTDOWN` unwired, because the worker is the only side that resolves. A
kicker constructs the broker and calls `.kiq()` without ever running a task, so a container opened
on `CLIENT_STARTUP` would hold app-scoped connections and pools for a process that resolves nothing
from them, then close them on a shutdown event a short-lived script often never fires. The cost is
documented in `README.md` rather than hidden: a process that both kicks and executes gets no
lifecycle unless the worker events fire, which `InMemoryBroker.startup()` arranges by firing both
pairs. `container.open()` on worker startup is unconditional and a no-op on a fresh container; it
earns its keep on a second worker cycle, reopening deliberately what the previous `WORKER_SHUTDOWN`
closed instead of leaving modern-di to reopen it implicitly with a `ContainerClosedWarning`.
