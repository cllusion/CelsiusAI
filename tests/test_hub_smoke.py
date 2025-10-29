import importlib


def test_import_hub_and_async_shim():
    """Smoke test: importing the hub module should not raise and the AsyncTkinter
    shim (if used) can be instantiated.
    """
    mod = importlib.import_module("src.hub.celsius_ultimate_hub")

    # Try to instantiate the AsyncTkinter shim if available
    AsyncTk = getattr(mod, "AsyncTkinter", None)
    assert AsyncTk is not None

    loop = AsyncTk()
    # start/stop should be available methods
    if hasattr(loop, "start"):
        loop.start()
    if hasattr(loop, "stop"):
        loop.stop()
