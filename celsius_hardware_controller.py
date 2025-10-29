"""
Shim for celsius_hardware_controller to provide a fallback for modules that import
`celsius_hardware_controller` at top-level (legacy imports). This file attempts
to import the real implementation from `src.hardware.celsius_hardware_controller`.
If not present, a lightweight stub implementation is provided so tools and tests
can import the symbol without failing static checks.

NOTE: The real hardware controller contains platform-specific code and should be
used when available. This shim is intentionally minimal.
"""

try:
    from src.hardware.celsius_hardware_controller import CelsiusHardwareController  # type: ignore
except Exception:

    class CelsiusHardwareController:
        """Minimal stub controller used when the real hardware controller is not present."""

        def __init__(self, *args, **kwargs):
            self._ready = False

        def set_rgb_color_simple(self, r: int, g: int, b: int):
            # noop in stub
            return None

        def apply_effect_simple(self, effect: str):
            # noop in stub
            return None

        async def async_noop(self, *args, **kwargs):
            return None

        # Provide any other commonly referenced methods as no-ops to avoid attribute errors.
        def __getattr__(self, name):
            def _noop(*a, **kw):
                return None

            return _noop
