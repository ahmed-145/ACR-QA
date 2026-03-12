#!/usr/bin/env python3
"""
ACR-QA CLI entry point.

Usage:
    python3 -m CORE --target-dir ./my-project
    python3 -m CORE --target-dir ./my-project --limit 20
    python3 -m CORE --target-dir ./my-project --repo my-repo --pr 42
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.main import main

if __name__ == "__main__":
    main()
