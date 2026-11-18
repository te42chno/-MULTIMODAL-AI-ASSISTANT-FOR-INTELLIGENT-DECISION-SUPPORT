"""Vercel serverless entrypoint for the MedReason FastAPI application.

The Python function lives at the repository root so Vercel can discover the root
``requirements.txt``. The backend package is added to sys.path explicitly.
"""

import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from app.main import app  # noqa: E402
from mangum import Mangum  # noqa: E402

# Lifespan is disabled because serverless invocations are short-lived; tables are
# created at module import instead (see app.main).
handler = Mangum(app, lifespan="off")
