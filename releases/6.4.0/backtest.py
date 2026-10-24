#!/usr/bin/env python3
"""Frozen walk-forward backtest for model_editor.py v6.4."""
import argparse,json,traceback
from pathlib import Path
from model_editor import run

def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",required=True); p.add_argument("--output-dir",required=True)
    a=p.parse_args(); manifest=json.loads(Path(a.manifest).read_text(encoding="utf-8-sig"))
    root=Path(a.output_dir); root.mkdir(parents=True,exist_ok=True)
    histories=list(manifest.get("history_before_start",[])); summary=[]
    for day in manifest["days"]:
        print(f"Running {day['date']}...",flush=True)
        pool_path=Path(day["pool"])
        if not pool_path.exists():
            skipped={"date":day["date"],"status":"skipped","reason":f"missing input: {day['pool']}"}
            summary.append(skipped)
            print(f"SKIPPED {day['date']}: input file is not available",flush=True)
            (root/"backtest_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
            continue
        try:
            outdir=root/day["date"]; result=run(day["pool"],manifest["gold"],histories,outdir,day["date"])
            synthetic=root/f"history_{day['date']}.json"
            synthetic.write_text(json.dumps({"date":day["date"],"daily_items":[{"title":x["title"],"source_title":x.get("source_title","") ,"link":x["link"],"source":x["source"]} for x in result["selected"]]},ensure_ascii=False,indent=2),encoding="utf-8")
            histories.append(str(synthetic)); summary.append({"date":day["date"],"status":"ok","selected_count":len(result["selected"]),"titles":[x["title"] for x in result["selected"]]})
        except Exception as exc:
            error={"date":day["date"],"status":"error","error":str(exc),"traceback":traceback.format_exc()}
            (root/f"error_{day['date']}.json").write_text(json.dumps(error,ensure_ascii=False,indent=2),encoding="utf-8")
            summary.append(error); print(f"ERROR on {day['date']}: {exc}",flush=True)
        (root/"backtest_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    completed=[x for x in summary if x.get("status")=="ok"]
    failed=[x for x in summary if x.get("status")=="error"]
    acceptance={"status":"PASS" if len(completed)>=7 and not failed else "FAIL",
                "completed_days":len(completed),"skipped_days":sum(x.get("status")=="skipped" for x in summary),
                "failed_days":len(failed),"rule":"At least 7 completed frozen days and no execution errors."}
    (root/"acceptance_report.json").write_text(json.dumps(acceptance,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print("BACKTEST "+acceptance["status"]+": "+json.dumps(acceptance,ensure_ascii=False))
if __name__=="__main__": main()
