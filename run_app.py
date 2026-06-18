"""Launch the Streamlit review UI:  python run_app.py

(The UI itself is built in Step 6; this launcher is wired now so the entry point
is stable.)
"""

import subprocess
import sys
from pathlib import Path

UI_APP = Path(__file__).resolve().parent / "ui" / "app.py"


def main() -> None:
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(UI_APP)], check=True)


if __name__ == "__main__":
    main()
