#!/usr/bin/env python3
"""Create one shareable archive from all completed v6.1 future-shadow runs."""
from __future__ import annotations

import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
RUNS_DIR = APP_DIR / "runs" / "future_shadow"
EXPORT_DIR = APP_DIR / "runs"


def main() -> int:
    run_dirs = sorted(path for path in RUNS_DIR.glob("shadow_v61_*") if path.is_dir())
    if not run_dirs:
        print("No completed v6.1 Shadow runs were found yet.")
        return 1

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = EXPORT_DIR / f"signal_lab_shadow_review_{stamp}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for run_dir in run_dirs:
            for path in sorted(run_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, Path(run_dir.name) / path.relative_to(run_dir))

    print(f"COMPLETE: {output}")
    try:
        subprocess.Popen(["explorer.exe", f"/select,{output}"])
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
