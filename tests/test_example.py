from examples.app import broker, greet


async def test_example_greet_task_resolves_and_greets() -> None:
    await broker.startup()
    try:
        result = await (await greet.kiq("world")).wait_result()  # ty: ignore[no-matching-overload]
    finally:
        await broker.shutdown()

    assert result.is_err is False
    assert result.return_value == "Hello, world!"
