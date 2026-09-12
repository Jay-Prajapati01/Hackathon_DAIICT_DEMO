"""Initialise the REC ledger database. Usage: python scripts/init_db.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.ledger import get_db_path, init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print(f"REC Ledger database initialized at {get_db_path()}")
