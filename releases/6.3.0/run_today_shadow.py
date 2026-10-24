#!/usr/bin/env python3
"""Run Signal Lab editor v6.1 once for each new Daily review bundle."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from model_editor import run


APP_DIR = Path(__file__).resolve().parent
SYSTEM_DIR = APP_DIR.parent
RUNS_DIR = APP_DIR / "runs" / "future_shadow"
STATE_PATH = APP_DIR / "daily_shadow_state.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def newest_bundle() -> Path:
    roots = [
        SYSTEM_DIR / "output" / "review_bundles",
        Path.home() / "Downloads",
        Path.home() / "Desktop",
    ]
    found: list[Path] = []
    for root in roots:
        if root.exists():
            found.extend(root.glob("signal_lab_daily_review_bundle_*.zip"))
    if not found:
        raise FileNotFoundError("No Daily review bundle was found.")
    return max(found, key=lambda path: path.stat().st_mtime)


def bundle_key(path: Path) -> str:
    stat = path.stat()
    return f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"


def prior_histories(run_date: str) -> list[str]:
    history_dir = SYSTEM_DIR / "history"
    paths = []
    if history_dir.exists():
        for path in sorted(history_dir.glob("*.json")):
            if path.stem < run_date:
                paths.append(path)
    return [str(path) for path in paths[-30:]]


def item_key(item: dict) -> str:
    return str(item.get("link") or item.get("title") or "").strip().lower().rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--automatic", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        bundle = newest_bundle()
    except FileNotFoundError:
        if args.automatic:
            print("No Daily bundle found yet.")
            return 0
        raise
    current_key = bundle_key(bundle)
    state = load(STATE_PATH) if STATE_PATH.exists() else {}
    if not args.force and state.get("last_bundle_key") == current_key:
        print(f"No new Daily bundle. Already processed: {bundle.name}")
        return 0

    with tempfile.TemporaryDirectory(prefix="signal_lab_v61_today_") as temp:
        temp_dir = Path(temp)
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(temp_dir)

        summary_path = temp_dir / "review_summary.json"
        unified_path = temp_dir / "quality" / "unified_editorial_shadow_input.json"
        daily_pool_path = temp_dir / "daily" / "daily_candidate_pool.json"
        pool_path = unified_path if unified_path.exists() else daily_pool_path
        history_dir = temp_dir / "history"
        if not pool_path.exists():
            raise FileNotFoundError("The Daily bundle has no Shadow input or candidate pool.")

        summary = load(summary_path) if summary_path.exists() else {}
        pool = load(pool_path)
        run_date = str(summary.get("run_date") or pool.get("run_date") or "").strip()
        if not run_date:
            raise ValueError("Could not determine the Daily run date.")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = RUNS_DIR / f"shadow_v61_{run_date}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        result = run(
            str(pool_path),
            str(APP_DIR / "gold_standard.json"),
            prior_histories(run_date),
            output_dir,
            run_date,
        )

        production = []
        current_history = history_dir / f"{run_date}.json"
        if current_history.exists():
            production = load(current_history).get("daily_items", [])

        production_by_key = {item_key(item): item for item in production}
        shadow_by_key = {item_key(item): item for item in result.get("selected", [])}
        comparison = {
            "schema_version": "signal-lab-v6.1-live-shadow-comparison-v1",
            "run_date": run_date,
            "source_bundle": bundle.name,
            "production_count": len(production),
            "shadow_count": len(result.get("selected", [])),
            "overlap": [shadow_by_key[k].get("title") for k in shadow_by_key if k in production_by_key],
            "shadow_only": [item.get("title") for k, item in shadow_by_key.items() if k not in production_by_key],
            "production_only": [item.get("title") for k, item in production_by_key.items() if k not in shadow_by_key],
        }
        (output_dir / "comparison.json").write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        zip_path = Path(shutil.make_archive(str(output_dir), "zip", output_dir.parent, output_dir.name))

        STATE_PATH.write_text(
            json.dumps(
                {
                    "last_bundle_key": current_key,
                    "last_bundle": str(bundle),
                    "run_date": run_date,
                    "result_zip": str(zip_path),
                    "completed_at": datetime.now().isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"COMPLETE: {zip_path}")
        if not args.automatic:
            try:
                subprocess.Popen(["explorer.exe", f"/select,{zip_path}"])
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
