#!/usr/bin/env python3
"""Signal Lab model-based editorial judge v6.1. Shadow only."""
import argparse, json, os, re, time
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

MODEL=os.getenv("SIGNAL_LAB_EDITOR_MODEL",os.getenv("SIGNAL_LAB_MODEL","gpt-4.1-mini"))
SPONSORED=("sponsored","in partnership with","/spons/","/sponsored/")
EVENT_RECAP=("overheard from","town hall","event recap","conference recap","highlights from the event")
WEAK_FORMAT=("/podcasts/","podcast","roundtable","interview with","conversation with")
MAX_ITEMS=int(os.getenv("SIGNAL_LAB_EDITOR_MAX_ITEMS","120"))

RUBRIC="""
You are the senior editor of Signal Lab for ContentLab, an Israeli strategy,
content and B2B storytelling agency. The audience does not want a general news
digest. It needs a small number of consequential signals that change how
strategy, marketing, content, media or organizations should operate.

Core territory: marketing and brand strategy; media and publisher economics;
content distribution and discovery; B2B social and LinkedIn; organizational
and work-model change; applied AI only when it changes one of those fields.

Reject generic AI or technology news, funding/M&A/chips/cybersecurity, generic
layoffs or hiring, generic advice, interviews without a strong finding, event
recaps, isolated US consumer campaigns, cosmetic branding, ordinary product
features, speculation, and stories important only because a famous company is
named. Geography or company size does not make a weak item strategic.

Use an audience veto: if a ContentLab strategy team would not plausibly discuss
the item with a client or apply its lesson, core_relevance must be 5 or lower
and the decision must be reject. Do not infer a broad trend from a single weak
activation. Evaluate the reported facts, not inflated trend language in the
summary. Quality is more important than quantity and zero selections is valid.
""".strip()

def load(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def clean(v): return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",str(v or ""))).strip()
def canon(url):
    try:
        p=urlsplit(url or ""); return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip("/"),"",""))
    except Exception: return str(url or "")
def idkey(value):
    value=str(value or "")
    return canon(value) if value.startswith(("http://","https://")) else value
def title(item): return clean(item.get("title") or item.get("source_title"))
def compact(item):
    return {"id":item.get("item_id") or canon(item.get("link")) or title(item),"title":title(item),
            "source_title":clean(item.get("source_title")),"source":clean(item.get("source")),
            "link":item.get("link",""),"summary":clean(item.get("summary") or item.get("article_summary"))[:1400],
            "body":clean(item.get("body"))[:2200],"topic":item.get("delivery_topic") or item.get("theme"),
            "depth_analysis":item.get("depth_analysis") or {}}

def factual_view(item):
    """Facts-only payload for model judgment. Excludes upstream interpretation."""
    row=compact(item)
    return {"id":row["id"],"title":row["title"],"source_title":row["source_title"],
            "source":row["source"],"link":row["link"],"summary":row["summary"]}

def history_items(paths):
    out=[]
    for path in paths:
        data=load(path); date=data.get("date") or Path(path).stem
        for item in data.get("daily_items",[]):
            out.append({"date":date,"title":title(item),"source_title":clean(item.get("source_title")),"link":item.get("link","")})
    return out

def normalized_title(value):
    return re.sub(r"[^a-z0-9א-ת]+"," ",clean(value).lower()).strip()

def token_similarity(a,b):
    aa=set(normalized_title(a).split()); bb=set(normalized_title(b).split())
    return len(aa&bb)/len(aa|bb) if aa and bb else 0

ALIASES={
    "מיקרוסופט":"microsoft","גוגל":"google","מטא":"meta","לינקדאין":"linkedin","טיקטוק":"tiktok",
    "אמזון":"amazon","יוטיוב":"youtube","שבב":"chip","שבבים":"chip","פרסום":"advertising",
    "יוצרים":"creators","חיפוש":"search","מסחר":"commerce","מדיה":"media","מותג":"brand","מותגים":"brand"
}

def concept_signature(value):
    tokens=normalized_title(value).split(); return {ALIASES.get(x,x) for x in tokens if len(x)>2 or x in ("ai",)}

def same_story(a,b):
    if canon(a.get("link")) and canon(a.get("link"))==canon(b.get("link")): return True
    a_titles=[title(a),clean(a.get("source_title"))]; b_titles=[title(b),clean(b.get("source_title"))]
    pairs=[(left,right) for left in a_titles for right in b_titles]
    for left,right in pairs:
        left=normalized_title(left); right=normalized_title(right)
        if not left or not right: continue
        sequence=max(SequenceMatcher(None,left,right).ratio(),SequenceMatcher(None,right,left).ratio())
        if sequence>=.72 or token_similarity(left,right)>=.58: return True
    sa=concept_signature(title(a)+" "+clean(a.get("source_title")))
    sb=concept_signature(title(b)+" "+clean(b.get("source_title")))
    shared=sa&sb
    entities={"microsoft","google","meta","linkedin","tiktok","amazon","youtube","ruggable"}
    concepts={"chip","advertising","creators","search","commerce","media","brand","ai"}
    if shared&entities and len(shared&concepts)>=2: return True
    return False

def story_cluster(item):
    text=normalized_title(title(item)+" "+clean(item.get("source_title"))+" "+clean(item.get("summary")))
    publisher_terms=("publisher","publishers","מו לים","forbes","verge","newsroom")
    google_terms=("google","גוגל","traffic","תנועה","click","קליק","search","חיפוש")
    if any(x in text for x in publisher_terms) and any(x in text for x in google_terms):
        return "publisher_google_shift"
    return ""

def repeat_of(item,history):
    for old in reversed(history):
        if same_story(item,old): return old
    return None

def hygiene(items,history):
    clean_items=[]; removed=[]
    for item in items:
        text=(title(item)+" "+str(item.get("link",""))).lower(); reason=None
        repeat=repeat_of(item,history)
        duplicate=next((old for old in clean_items if same_story(item,old)),None)
        if any(x in text for x in SPONSORED): reason="sponsored"
        elif any(x in text for x in WEAK_FORMAT): reason="weak_format"
        elif any(x in text for x in EVENT_RECAP): reason="event_recap"
        elif repeat: reason=f"repeat:{repeat['date']}"
        elif duplicate: reason=f"same_day_duplicate:{compact(duplicate)['id']}"
        if reason: removed.append({"title":title(item),"link":item.get("link",""),"reason":reason})
        else: clean_items.append(item)
    return clean_items,removed

def json_call(system,user):
    from openai import OpenAI
    client=OpenAI(); last_error=None
    for attempt in range(3):
        try:
            response=client.chat.completions.create(model=MODEL,temperature=0,
                response_format={"type":"json_object"},messages=[{"role":"system","content":system},{"role":"user","content":user}])
            return json.loads(response.choices[0].message.content)
        except Exception as exc:
            last_error=exc
            if attempt<2: time.sleep(attempt+1)
    raise last_error

def judge_items(items,gold):
    positives=[{"title":x.get("title"),"text":clean(x.get("text"))[:260]} for x in gold.get("positive_examples",[])]
    negatives=[{"title":x.get("title"),"text":clean(x.get("text"))[:220]} for x in gold.get("negative_examples",[])]
    results=[]
    for start in range(0,len(items),15):
        batch=[factual_view(x) for x in items[start:start+15]]
        prompt=f"""Evaluate every candidate independently. Return JSON only:
{{"evaluations":[{{"id":"exact input id","decision":"select|borderline|reject","score":1-10,
"core_relevance":1-10,"meaningful_change":1-10,"evidence":1-10,"transferability":1-10,
"reason":"one concise Hebrew sentence","risk_flags":["..."]}}]}}
Judge only the factual fields supplied. Ignore any strategic framing implied by
the translated title if the source title and factual summary do not support it.
Do not omit candidates. Select requires score >=8, core_relevance >=8 and transferability >=7.
Borderline requires score 6-7 and core_relevance >=7. Otherwise reject.

POSITIVE EXAMPLES
{json.dumps(positives,ensure_ascii=False)}

NEGATIVE EXAMPLES
{json.dumps(negatives,ensure_ascii=False)}

CANDIDATES
{json.dumps(batch,ensure_ascii=False)}"""
        data=json_call(RUBRIC,prompt); results.extend(data.get("evaluations",[]))
    return results

def eligibility(ev,item=None):
    try:
        score=int(ev.get("score",0)); core=int(ev.get("core_relevance",0)); transfer=int(ev.get("transferability",0))
    except (TypeError,ValueError): return None
    # The model judge is the clean editorial authority in v6.1. Do not let the
    # legacy upstream depth classifier veto a candidate that independently met
    # the strong evidence, relevance and transferability thresholds. In v6 this
    # veto removed several items that were themselves positive gold examples.
    if ev.get("decision")=="select" and score>=8 and core>=8 and transfer>=7: return "strong"
    if ev.get("decision")=="borderline" and 6<=score<=7 and core>=7 and transfer>=6: return "borderline"
    return None

def choose_portfolio(items,evaluations):
    by_id={idkey(e.get("id")):e for e in evaluations}; eligible=[]
    for item in items:
        row=factual_view(item); ev=by_id.get(idkey(row["id"]),{}); tier=eligibility(ev,item)
        row["story_cluster"]=story_cluster(item)
        if tier: eligible.append({"item":row,"evaluation":ev,"tier":tier})
    prompt=f"""Build the final daily portfolio. Return JSON only:
{{"selected_ids":["..."],"borderline_ids":["..."],"portfolio_reason":"concise Hebrew"}}
Choose 0-8 items. Use strong candidates first. A small portfolio is valid, but
do not discard a strong item merely to make the brief shorter. You may include
at most one candidate marked borderline. Avoid source and topic domination and
overlapping versions of one change. Never add an ID not shown below.

ELIGIBLE
{json.dumps(eligible,ensure_ascii=False)}"""
    return json_call(RUBRIC,prompt),eligible

def enforce_portfolio(portfolio,eligible):
    tiers={idkey(x["item"]["id"]):x["tier"] for x in eligible}; rows={idkey(x["item"]["id"]):x["item"] for x in eligible}
    evaluations={idkey(x["item"]["id"]):x["evaluation"] for x in eligible}
    final=[]; borderline_used=False; used_clusters=set(); source_counts={}; topic_counts={}
    strong=[idkey(x["item"]["id"]) for x in eligible if x["tier"]=="strong"]
    strong.sort(key=lambda ident:(int(evaluations[ident].get("score",0)),int(evaluations[ident].get("core_relevance",0)),int(evaluations[ident].get("meaningful_change",0)),int(evaluations[ident].get("evidence",0))),reverse=True)
    # Respect the portfolio editor's ordering, then deterministically restore
    # any independently strong candidates it omitted. v6 did this in the
    # reverse order, which weakened the portfolio-level diversity judgment.
    portfolio_requested=[idkey(x) for x in list(portfolio.get("selected_ids",[]))[:16]]
    requested=([x for x in portfolio_requested if tiers.get(x)=="strong"]+
               [x for x in strong if x not in portfolio_requested]+
               [x for x in portfolio_requested if tiers.get(x)=="borderline"])
    for ident in requested:
        ident=idkey(ident); tier=tiers.get(ident)
        if not tier or ident in final: continue
        if any(same_story(rows[ident],rows[old]) for old in final): continue
        cluster=rows[ident].get("story_cluster")
        if cluster and cluster in used_clusters: continue
        source=clean(rows[ident].get("source")).lower()
        topic=clean(rows[ident].get("topic"))
        if source and source_counts.get(source,0)>=2: continue
        if topic and topic_counts.get(topic,0)>=4: continue
        if tier=="borderline":
            if borderline_used: continue
            borderline_used=True
        final.append(ident)
        if cluster: used_clusters.add(cluster)
        if source: source_counts[source]=source_counts.get(source,0)+1
        if topic: topic_counts[topic]=topic_counts.get(topic,0)+1
        if len(final)==8: break
    portfolio=dict(portfolio); portfolio["selected_ids"]=final
    portfolio["borderline_ids"]=[x for x in final if tiers.get(x)=="borderline"]
    return portfolio

def run(pool_path,gold_path,history_paths,output_dir,run_date=None):
    pool=load(pool_path); items=pool.get("items",pool); history=history_items(history_paths)
    clean_items,removed=hygiene(items,history); clean_items=clean_items[:MAX_ITEMS]
    evaluations=judge_items(clean_items,load(gold_path))
    portfolio,eligible=choose_portfolio(clean_items,evaluations); portfolio=enforce_portfolio(portfolio,eligible)
    by_id={idkey(compact(x)["id"]):x for x in clean_items}; ev_by_id={idkey(e.get("id")):e for e in evaluations}; selected=[]
    for ident in portfolio.get("selected_ids",[]):
        item=by_id.get(idkey(ident))
        if item: selected.append({**compact(item),"editorial_evaluation":ev_by_id.get(idkey(ident),{})})
    selected_ids={idkey(x["id"]) for x in selected}
    eligible_ids={idkey(x["item"]["id"]):x["tier"] for x in eligible}
    out={"schema_version":"signal-lab-model-editor-v6.1","run_date":run_date or pool.get("run_date"),
         "production_effect":"none","model":MODEL,"candidate_count":len(items),"judged_count":len(clean_items),
         "selected":selected,"portfolio":portfolio,"evaluations":evaluations,"hygiene_removed":removed,
         "selection_audit":{"eligible_strong":sum(1 for x in eligible_ids.values() if x=="strong"),
                            "eligible_borderline":sum(1 for x in eligible_ids.values() if x=="borderline"),
                            "selected_count":len(selected_ids),
                            "eligible_not_selected":[ident for ident in eligible_ids if ident not in selected_ids]}}
    Path(output_dir).mkdir(parents=True,exist_ok=True)
    Path(output_dir,"result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument("--pool",required=True); p.add_argument("--gold",required=True)
    p.add_argument("--history",nargs="*",default=[]); p.add_argument("--output-dir",required=True); p.add_argument("--run-date")
    a=p.parse_args(); out=run(a.pool,a.gold,a.history,a.output_dir,a.run_date)
    print(f"Selected {len(out['selected'])} of {out['candidate_count']}")
    for i,x in enumerate(out["selected"],1): print(f"{i}. {x['title']} [{x['editorial_evaluation'].get('score')}]")
if __name__=="__main__": main()
