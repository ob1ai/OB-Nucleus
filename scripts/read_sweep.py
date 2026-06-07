"""Runner for the daily read-only sweep (brief Section 10 step 4).

From the repo root:
    python scripts\\read_sweep.py
Or via the CLI: ob-nucleus sweep run
Output: prints the digest and saves verification\\read_sweep_<date>.md
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ob_nucleus.sweep import run_sweep  # noqa: E402

if __name__ == "__main__":
    print(run_sweep())
