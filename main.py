import sys
import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv(
    dotenv_path=Path(__file__).parent / "API_KEY.env",
    override=True
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from polymer_pipeline.pipeline import main

if __name__ == "__main__":
    main()
