# `setup_di` wires only the worker lifecycle events

**Decision:** `setup_di` registers handlers for `WORKER_STARTUP` and `WORKER_SHUTDOWN` only; the
`CLIENT_STARTUP` / `CLIENT_SHUTDOWN` pair is deliberately left unwired.

taskiq fires two independent lifecycle pairs, and wiring both looks like the safe default. It was
rejected because the worker is the only side that resolves. A kicker process constructs the broker
and calls `.kiq()`; it never runs a task, so a container opened on `CLIENT_STARTUP` would hold app
scoped resources — connections, pools, whatever the providers create at open — for a process that
resolves nothing from them, and would have to close them again on a shutdown event that a
short-lived client script frequently never fires. Wiring the pair that matches where resolution
happens keeps the container's lifetime equal to the span in which it is used.

The cost is a real one, so it is stated rather than hidden: a process that both kicks and executes
in-process, which is what `InMemoryBroker` does in a test or a script, gets no lifecycle from
`setup_di` unless the worker events actually fire. `InMemoryBroker.startup()` fires both pairs, so
the in-process case works; a caller driving tasks by other means opens and closes the root container
itself. This is documented in `README.md`, because it is the one place the choice is visible to a
user.

`container.open()` on `WORKER_STARTUP` is unconditional for the same reason. A fresh `Container` is
already open, so the first call is a no-op; the call earns its keep on the **second** worker cycle —
a restart, or a test that starts and stops the same broker twice — where the container was closed by
the previous `WORKER_SHUTDOWN` and resolving without reopening would raise `ContainerClosedError`.

**Revisit trigger:** a client-side capability appears that resolves from the container before any
task runs — for instance a kicker-side provider used to build task arguments, or middleware on the
client path that needs DI. At that point the client is a resolving context and needs its own
lifecycle.
