"""Validate episode.json files before rendering.

Usage: python src/validate_episode.py episodes/<dir>/episode.json [more...]
Exit code 1 if any ERROR. WARNINGs do not fail.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERIC = {"card": ["title", "lines"], "steps": ["steps"], "compare": ["left", "right"], "bigword": ["word"], "loop": ["nodes"],
           "stack": ["layers"], "chat": ["messages"], "checklist": ["items"], "hub": ["spokes"]}
LEGACY = {"spam": 3, "cats": 3, "flow": 3, "breaks": 2, "takeaway": 3, "jargon": 3, "roadmap": 4, "recipe": 2, "chef": 3}
OK_VISUALS = set(GENERIC) | {"endcard"}
REQUIRED = ["episode", "slug", "level", "title", "status", "status_note", "prerequisites", "learning_objective", "analogy",
            "analogy_breaks", "actual_tech", "fact_check_notes", "takeaway", "voice", "scenes", "publishing"]
STATUSES = ["IDEA", "RESEARCH", "SCRIPTED", "FACT_CHECKED", "APPROVED_FOR_RENDER", "ASSETS_READY", "RENDERED", "QA_PASSED",
            "READY_TO_PUBLISH", "PUBLISHED"]


def check(path):
    errs, warns = [], []
    try:
        ep = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"invalid JSON: {e}"], []
    for k in REQUIRED:
        if k not in ep:
            errs.append(f"missing key: {k}")
    if errs:
        return errs, warns
    if ep["status"] not in STATUSES:
        errs.append(f"bad status {ep['status']}")
    if ep["status"] in ("FACT_CHECKED", "APPROVED_FOR_RENDER") and not ep.get("sources"):
        errs.append("status FACT_CHECKED requires a non-empty 'sources' list of official URLs actually consulted")
    cur = json.load(open(os.path.join(ROOT, "curriculum", "curriculum.json"), encoding="utf-8"))
    c_ep = next((e for e in cur["episodes"] if e["n"] == ep["episode"]), None)
    if not c_ep:
        errs.append("episode number not in curriculum")
    elif c_ep.get("fv") and ep["status"] == "SCRIPTED" and "verif" not in (ep["fact_check_notes"] + ep["status_note"]).lower():
        errs.append("fv episode must say 'Needs verification before publishing' (or cite sources) in fact_check_notes/status_note")
    if "pilot" in ep or True:
        pass
    scenes = ep["scenes"]
    if not scenes or scenes[-1]["visual"] != "endcard":
        errs.append("last scene must use visual 'endcard'")
    words = 0
    for si, sc in enumerate(scenes):
        v = sc.get("visual")
        phs = sc.get("phrases", [])
        if v not in OK_VISUALS and v not in LEGACY:
            errs.append(f"scene {si}: unknown visual '{v}'")
        if v in LEGACY and ep["episode"] > 3:
            errs.append(f"scene {si}: legacy visual '{v}' is only for episodes 0-3; use {sorted(OK_VISUALS)}")
        if v in GENERIC:
            c = sc.get("card")
            if not c:
                errs.append(f"scene {si}: visual '{v}' needs a 'card' object")
            else:
                for k in GENERIC[v]:
                    if k not in c:
                        errs.append(f"scene {si}: card missing '{k}'")
        if not phs:
            errs.append(f"scene {si}: no phrases")
        for pi, ph in enumerate(phs):
            t = ph.get("text", "")
            n = len(t.split())
            words += n
            if n > 24:
                warns.append(f"scene {si} phrase {pi}: {n} words (long)")
            toks = {"".join(ch for ch in w.lower() if ch.isalnum()) for w in t.split()}
            for h in ph.get("hl", []):
                if "".join(ch for ch in h.lower() if ch.isalnum()) not in toks:
                    warns.append(f"scene {si} phrase {pi}: highlight '{h}' not in text")
        # list-reveal visuals look best when items <= phrases
        c = sc.get("card") or {}
        for key in ("steps", "layers", "nodes", "spokes", "items", "messages"):
            if key in c and len(c[key]) > 5 + (key == "spokes"):
                errs.append(f"scene {si}: too many {key} ({len(c[key])})")
            for it in c.get(key, []):
                s = it if isinstance(it, str) else it.get("text", "")
                if isinstance(s, str) and key != "messages" and len(s) > 26:
                    warns.append(f"scene {si}: label '{s}' long ({len(s)} chars)")
        for stk in sc.get("stickers", []) or []:
            if len(stk) != 5:
                errs.append(f"scene {si}: sticker needs [emoji,x,y,size,t0]")
    first = scenes[0]["phrases"][0]["text"].lower()
    if "zillenial" not in first and "techies" not in first:
        warns.append("first phrase should be the short Zillenial Talk greeting")
    est = words / 2.5 + 0.5 * sum(len(s["phrases"]) for s in scenes) * 0.6 + len(scenes) * 0.35
    if words > 190:
        errs.append(f"narration too long: {words} words (~{est:.0f}s). Aim 110-170")
    elif words < 70:
        warns.append(f"narration short: {words} words")
    last_text = " ".join(p["text"] for p in scenes[-1]["phrases"]).lower()
    if "zillenial" not in last_text:
        warns.append("end card narration should include the Zillenial Talk sign-off")
    pub = ep["publishing"]
    for k in ("instagram_caption", "youtube_title", "youtube_description", "hashtags", "thumbnail_text"):
        if k not in pub:
            errs.append(f"publishing missing {k}")
    if pub.get("thumbnail_text") and len(pub["thumbnail_text"]) > 14:
        warns.append("thumbnail_text > 14 chars may overflow the cover")
    return errs, warns


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        e, w = check(p)
        print(("FAIL " if e else "ok   ") + p)
        for x in e:
            print("   ERROR:", x)
        for x in w:
            print("   warn :", x)
        bad += bool(e)
    sys.exit(1 if bad else 0)
