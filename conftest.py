import sys
from pathlib import Path

# Ensure project root is on sys.path so tests can import modules directly
sys.path.insert(0, str(Path(__file__).parent))
