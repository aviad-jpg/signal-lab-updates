from model_editor import hygiene,enforce_portfolio,factual_view,idkey,eligibility

def test_same_day_duplicate():
    items=[{"title":"רוגבל משנה את תקציב הפרסום ומעבירה השקעה ליוצרי ShopMy","link":"https://a/1"},
           {"title":"רוגבל מעבירה תקציבי פרסום ממטא ליוצרי ShopMy","link":"https://a/2"}]
    clean,removed=hygiene(items,[])
    assert len(clean)==1 and removed[0]["reason"].startswith("same_day_duplicate")

def test_portfolio_guards():
    eligible=[{"item":{"id":"s1"},"tier":"strong","evaluation":{"score":8,"core_relevance":8,"meaningful_change":8,"evidence":8}},
              {"item":{"id":"b1"},"tier":"borderline","evaluation":{"score":7}},
              {"item":{"id":"b2"},"tier":"borderline","evaluation":{"score":6}}]
    out=enforce_portfolio({"selected_ids":["bad","b1","b2","s1","s1"]},eligible)
    assert out["selected_ids"]==["s1","b1"] and out["borderline_ids"]==["b1"]

def test_legacy_depth_cannot_veto_model_selection():
    ev={"decision":"select","score":8,"core_relevance":8,"transferability":8}
    item={"depth_analysis":{"type":"feature_update","post_potential":2}}
    assert eligibility(ev,item)=="strong"

def test_source_concentration_cap():
    eligible=[]
    for n in range(3):
        eligible.append({"item":{"id":f"s{n}","source":"Same Source","topic":"Marketing"},
                         "tier":"strong","evaluation":{"score":9-n,"core_relevance":9,"meaningful_change":8,"evidence":8}})
    out=enforce_portfolio({"selected_ids":["s0","s1","s2"]},eligible)
    assert out["selected_ids"]==["s0","s1"]

def test_event_recap_removed():
    clean,removed=hygiene([{"title":"Overheard from publishers at a London Town Hall","link":"https://event"}],[])
    assert not clean and removed[0]["reason"]=="event_recap"

def test_url_id_normalization():
    assert idkey("https://example.com/story/")==idkey("https://example.com/story?utm=x")

def test_factual_view_excludes_upstream_framing():
    row=factual_view({"title":"t","source_title":"s","summary":"fact","body":"inflated","depth_analysis":{"core_claim":"inflated"}})
    assert row["summary"]=="fact" and "body" not in row and "depth_analysis" not in row

def test_source_title_repeat():
    items=[{"title":"ניסוח עברי אחר","source_title":"Ruggable shifts spend to ShopMy","link":"https://new"}]
    history=[{"date":"2026-10-16","title":"כותרת עברית","source_title":"Ruggable shifts spend to ShopMy","link":"https://old"}]
    clean,removed=hygiene(items,history)
    assert not clean and removed[0]["reason"]=="repeat:2026-10-16"

if __name__=="__main__":
    test_same_day_duplicate(); test_portfolio_guards(); test_legacy_depth_cannot_veto_model_selection(); test_source_concentration_cap(); test_event_recap_removed(); test_url_id_normalization(); test_factual_view_excludes_upstream_framing(); test_source_title_repeat(); print("All guard tests passed")
