#!/usr/bin/env python3
"""Create a shareable archive with Shadow results and diagnostics."""
from __future__ import annotations

import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
RUNS_DIR = APP_DIR / "runs" / "future_shadow"
EXPORT_DIR = APP_DIR / "runs"


def main() -> int:
    run_dirs = sorted(path for path in RUNS_DIR.glob("shadow_*") if path.is_dir())

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = EXPORT_DIR / f"signal_lab_shadow_review_{stamp}.zip"
    installed_path = APP_DIR / "installed_version.txt"
    state_path = APP_DIR / "daily_shadow_state.json"
    bundle_roots = [APP_DIR.parent / "output" / "review_bundles", Path.home() / "Downloads", Path.home() / "Desktop"]
    bundles = [p for root in bundle_roots if root.exists() for p in root.glob("signal_lab_daily_review_bundle_*.zip")]
    newest = max(bundles,key=lambda p:p.stat().st_mtime) if bundles else None
    diagnostic = {
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "installed_version": installed_path.read_text(encoding="utf-8-sig").strip() if installed_path.exists() else "missing",
        "state_file_present": state_path.exists(),
        "completed_run_count": len(run_dirs),
        "newest_bundle": str(newest) if newest else None,
        "newest_bundle_modified_at": datetime.fromtimestamp(newest.stat().st_mtime).isoformat(timespec="seconds") if newest else None,
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics/diagnostic_report.json",json.dumps(diagnostic,ensure_ascii=False,indent=2))
        if state_path.exists(): archive.write(state_path,"diagnostics/daily_shadow_state.json")
        if installed_path.exists(): archive.write(installed_path,"diagnostics/installed_version.txt")
        try:
            task_status=subprocess.run(["schtasks.exe","/Query","/TN","Signal Lab Daily Shadow v6.5","/V","/FO","LIST"],capture_output=True,text=True,timeout=15)
            archive.writestr("diagnostics/task_status.txt",task_status.stdout+task_status.stderr)
        except Exception as exc:
            archive.writestr("diagnostics/task_status.txt",f"Could not query scheduled task: {exc}")
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
