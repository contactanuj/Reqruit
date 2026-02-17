# ---------------------------------------------------------------------------
# src/ — Application root package.
#
# This project uses a "src as package" layout where `src` is the top-level
# Python package. All imports use the `src.` prefix:
#
#   from src.core.config import settings
#   from src.db.documents.user import User
#   from src.api.main import create_app
#
# Alternative layouts considered:
#   - Named package inside src/ (src/job_hunt/): adds an extra nesting level
#     with no benefit for a single-app project.
#   - Flat layout (no src/): mixes source code with project config files,
#     makes packaging harder.
#
# The src/ layout is the Python Packaging Authority (PyPA) recommendation
# and prevents accidental imports from the working directory.
# ---------------------------------------------------------------------------
