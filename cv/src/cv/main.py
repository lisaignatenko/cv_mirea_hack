import asyncio
import logging

logger = logging.getLogger(__name__)


async def main():
    logger.info("Hello from main.py")


if __name__ == "__main__":
    asyncio.run(main())
