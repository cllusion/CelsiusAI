from pathlib import Path
import sys
import logging
import asyncio

# Ensure project root is on sys.path so 'src.*' imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger("auth_reproducer")

async def main():
    try:
        from src.utils.celsius_auth import CelsiusAuth
    except Exception as e:
        logger.exception("Failed to import CelsiusAuth: %s", e)
        return

    data_dir = PROJECT_ROOT / "data"
    auth = CelsiusAuth(data_dir)

    logger.info("Calling initialize()")
    import time
    t0 = time.time()
    await auth.initialize()
    t1 = time.time()
    logger.info("initialize() finished in %.3f sec", t1 - t0)

    logger.info("Authenticating admin user")
    t0 = time.time()
    success, result = await auth.authenticate("cllusion001", "T3qy22ny*@dyu0ppn*pG")
    t1 = time.time()
    logger.info("authenticate() finished in %.3f sec", t1 - t0)
    logger.info("Result: success=%s, result=%s", success, result)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        logger.exception("Reproducer failed")
