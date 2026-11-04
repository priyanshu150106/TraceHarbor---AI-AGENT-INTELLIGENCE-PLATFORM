"""
TraceHarbor API — Vercel Serverless Function Entrypoint
Observe. Evaluate. Secure.
"""

import os
import sys

# Ensure the apps/api directory is on sys.path so 'app.*' package imports resolve properly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(CURRENT_DIR)
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from app.main import app  # noqa: E402

__all__ = ["app"]
