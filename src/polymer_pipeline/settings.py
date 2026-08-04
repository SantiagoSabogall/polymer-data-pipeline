import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv("API_KEY.env", usecwd=True)
if not env_path:
    env_path = find_dotenv("API_KEY.env")
load_dotenv(env_path)

TOTAL_RESULTS_PER_QUERY = 250
BATCH_SIZE = 25
SLEEP_BETWEEN_BATCHES = 0.5
MAX_WORKERS = 5

ELSEVIER_API_KEY = os.getenv("ELSEVIER_API_KEY")
SPRINGER_API_KEY = os.getenv("SPRINGER_META_API_KEY")
CROSSREF_EMAIL = os.getenv("CROSSREF_POLITE_EMAIL", "[EMAIL_ADDRESS]")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "[EMAIL_ADDRESS]")
NCBI_API_KEY = os.getenv("PUBMED_API_KEY")  
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "[EMAIL_ADDRESS]")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")
    