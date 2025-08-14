import os

from dotenv import load_dotenv

load_dotenv()

IONIC_API_KEY = os.getenv("IONIC_API_KEY")
IONIC_API_HOST = os.getenv("IONIC_API_HOST")
