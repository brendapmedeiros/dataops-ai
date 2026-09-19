from __future__ import annotations

import sys
from pathlib import Path

# adiciono a raiz e src no path para execucao direta no hugging face spaces
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR / "src") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "src"))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.app import main

if __name__ == "__main__":
    main()
