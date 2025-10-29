"""Async Tkinter event-loop helper.

Provides AsyncTkinter class which runs an asyncio event loop in a background
thread and exposes create_task/stop helpers.
"""

import asyncio
import threading


class AsyncTkinter(threading.Thread):
    """Run an asyncio event loop in a daemon thread for use with Tkinter.

    Usage:
        loop_thread = AsyncTkinter()
        loop_thread.start()
        loop_thread.create_task(coro())
        loop_thread.stop()
    """

    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        """Runs the asyncio event loop."""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    def create_task(self, coro):
        """Schedules a coroutine to be run on the asyncio event loop."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        """Stops the asyncio event loop."""
        self.loop.call_soon_threadsafe(self.loop.stop)
