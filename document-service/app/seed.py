"""document-service/app/seed.py — wait for DB and create storage dirs."""
import sys, time
from sqlalchemy import text
from .database import engine
from .config import settings
import os


def wait_for_db(max_retries=15, delay=3):
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[doc-seed] Database ready")
            return
        except Exception as e:
            print(f"[doc-seed] Waiting for DB... {attempt + 1}/{max_retries}: {e}")
            time.sleep(delay)
    sys.exit(1)


def seed():
    wait_for_db()
    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)
    print(f"[doc-seed] Storage dir ready: {settings.PDF_STORAGE_PATH}")


if __name__ == "__main__":
    seed()
