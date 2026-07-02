import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv("API_KEY.env"))

TOTAL_RESULTS_PER_QUERY = 200
BATCH_SIZE = 25
SLEEP_BETWEEN_BATCHES = 0.5

ELSEVIER_API_KEY = os.getenv("ELSEVIER_API_KEY")
SPRINGER_API_KEY = os.getenv("SPRINGER_META_API_KEY")
CROSSREF_EMAIL = os.getenv("CROSSREF_POLITE_EMAIL", "ssabogal@unal.edu.co")
