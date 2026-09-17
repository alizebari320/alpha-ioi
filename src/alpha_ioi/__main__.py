"""``python -m alpha_ioi`` entry point.

Kept intentionally tiny: it just delegates to :func:`alpha_ioi.app.main`, the
same function the ``alpha-ioi`` console script calls.
"""

from __future__ import annotations

import sys

from alpha_ioi.app import main

if __name__ == "__main__":
    sys.exit(main())
