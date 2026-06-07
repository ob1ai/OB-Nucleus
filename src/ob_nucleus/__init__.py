"""OB-Nucleus: OB.1 operations layer for Audity and Nucleus.

Rules before tools. Reads are free; writes cost credits and require
an explicit confirm flag plus a credit check. See CLAUDE.md and
knowledge/QUICKREF.md in the repo root.
"""

__version__ = "0.1.0"

from .client import AudityClient, AudityError  # noqa: F401
from .api import Audity  # noqa: F401
