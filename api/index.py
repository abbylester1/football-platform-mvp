import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("STORAGE_DIR", "/tmp/data")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/data/football.db")

from backend.main import app
