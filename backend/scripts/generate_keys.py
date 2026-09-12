"""Generate the RSA-2048 issuer key pair (run once). Usage: python scripts/generate_keys.py [--force]"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.crypto import generate_key_pair  # noqa: E402

if __name__ == "__main__":
    force = "--force" in sys.argv
    priv, pub = generate_key_pair(overwrite=force)
    print("RSA-2048 key pair ready.")
    print(f"   {priv} — NEVER commit this file.")
    print(f"   {pub}  — safe to distribute.")
