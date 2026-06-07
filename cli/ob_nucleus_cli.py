"""Direct CLI entrypoint for environments without pip install -e .

From the repo root:
    python cli\\ob_nucleus_cli.py account credits
Equivalent to the installed console script: ob-nucleus account credits
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ob_nucleus.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
