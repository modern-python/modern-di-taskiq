import types

import modern_di_taskiq


def test_public_surface_is_exactly_the_four_documented_symbols() -> None:
    """INVARIANT: the package exports exactly the four symbols the README documents.

    Broken by promoting a helper to a public name, in ``__all__`` or as an unprefixed binding in
    ``__init__`` -- the latter is public whether or not it was meant to be. ``build_di_container``
    and ``Dependency`` are the standing temptation: they are the seam taskiq resolves through, so
    they read like API, but exporting either would turn the shape of the per-task wiring into a
    semver promise instead of an implementation detail this package can re-cut against a new taskiq.
    """
    public = sorted(
        name
        for name, value in vars(modern_di_taskiq).items()
        if not name.startswith("_") and not isinstance(value, types.ModuleType)
    )

    assert public == ["FromDI", "fetch_di_container", "setup_di", "taskiq_message_provider"]
    assert modern_di_taskiq.__all__ == public
