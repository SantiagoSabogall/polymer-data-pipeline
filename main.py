import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(
    dotenv_path=Path(__file__).parent / "API_KEY.env",
    override=True
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from polymer_pipeline.pipeline import main

if __name__ == "__main__":
    asyncio.run(main())
