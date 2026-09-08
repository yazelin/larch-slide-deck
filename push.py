#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一份簡報標記檔推成 Larch 專案裡的一張簡報插件卡（沒有就建、有就更新內容，不動別的卡）。

    python3 push.py --project project-xxxx --deck example/0909-larch-vn.md \
        [--card deck-0909] [--title 開場簡報] [--start] [--set brand=週三直播 --set theme=peach ...] [--dry]

- 金鑰讀 ~/.config/larch/key；寫入一律帶 If-Match（讀回來的 ETag），被編輯器改過就會被擋而不是蓋掉。
- 專案沒導入這個插件的話，會把 settings.plugins[slide-deck].enabled 寫進去（整包 PUT 專案前先抓版子、寫完原樣推回）。
- 插件卡的 HTML 存在卡片裡（pluginHtml），所以不必先在網頁上架就能跑；上架後作者在編輯器按更新也會換新版。
- 標記檔開頭可放一段設定（--- 之前，每行 key: value），跟 --set 一樣是 pluginValues 的鍵。
"""
import argparse, glob, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://larch.ink/api/agent"
KEY = open(os.path.expanduser("~/.config/larch/key")).read().strip()
ETAG = {}

def api(method, path, body=None):
    h = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
    if method in ("PUT", "POST", "DELETE") and ETAG.get("v"): h["If-Match"] = ETAG["v"]
    req = urllib.request.Request(API + path, method=method, headers=h,
                                 data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            if r.headers.get("ETag"): ETAG["v"] = r.headers["ETag"]
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("%s %s -> %s %s" % (method, path, e.code, e.read().decode()[:300]))

def load_deck(path):
    """回 (values, content)。檔頭 `key: value` 行到第一個 --- 之前是設定；沒有冒號行就整份都是內容。"""
    text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    parts = text.split("\n---\n", 1)
    head = parts[0]
    if all((not l.strip()) or (":" in l and not l.startswith(("#", "-", "[", "|", ">", "@", "`"))) for l in head.split("\n")) and len(parts) > 1:
        values = {}
        for l in head.split("\n"):
            if ":" in l:
                k, v = l.split(":", 1); values[k.strip()] = v.strip()
        return values, parts[1]
    return {}, text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True); ap.add_argument("--deck", required=True)
    ap.add_argument("--card", default=None, help="卡片 id，預設 deck-<檔名>"); ap.add_argument("--title", default="簡報")
    ap.add_argument("--start", action="store_true", help="設成起點卡"); ap.add_argument("--set", action="append", default=[], help="key=value，覆寫欄位")
    ap.add_argument("--board", default=None, help="版子 id，預設主線"); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    pid = a.project; board = a.board or "board-%s-main" % pid
    mf = sorted(glob.glob(os.path.join(HERE, "dist", "slide-deck-*.json")))
    if not mf: sys.exit("先跑 python3 manifest.py")
    pdef = json.load(open(mf[-1], encoding="utf-8")); card = pdef["cards"][0]
    values = {f["key"]: f.get("defaultValue", "") for f in card["fields"]}
    head, content = load_deck(a.deck)
    values.update(head); values["content"] = content
    for kv in a.set:
        k, v = kv.split("=", 1); values[k] = v
    for k in ("clickNav", "showEnd"):
        if isinstance(values[k], str): values[k] = values[k].lower() in ("1", "true", "yes", "on")
    if isinstance(values["fontScale"], str): values["fontScale"] = float(values["fontScale"])
    nid = a.card or ("deck-" + os.path.splitext(os.path.basename(a.deck))[0])

    # 1. 插件要在專案的 settings.plugins 裡，播放器才會執行這張卡
    proj = api("GET", "/projects/%s" % pid); proj = proj.get("project", proj)
    plugins = (proj.get("settings") or {}).get("plugins") or {}
    need_enable = not (plugins.get(pdef["id"]) or {}).get("enabled")
    print("專案", proj.get("name"), "| 插件已導入" if not need_enable else "| 插件未導入，會寫 settings.plugins")

    # 2. 版子：沿用既有卡的座標，其他卡原樣
    b = api("GET", "/projects/%s/boards/%s" % (pid, board)); b = b.get("board", b)
    nodes = b.get("nodes", []); edges = b.get("edges", [])
    prev = next((n for n in nodes if n["id"] == nid), None)
    d = dict((prev or {}).get("data") or {})
    d.update({"type": "plugin", "pluginId": pdef["id"], "pluginCardId": card["id"], "pluginName": pdef["name"], "pluginCardName": card["name"],
              "pluginIcon": card.get("icon", "presentation"), "pluginColor": card.get("color", "#b8862b"),
              "pluginPresentation": "fullscreen", "pluginSkippable": True, "pluginAssets": [], "platforms": ["web"],
              "voiceMode": "off", "title": a.title, "text": "", "pluginValues": values, "pluginReadVars": [], "pluginWriteVars": []})
    def ver(v): return tuple(int(x) for x in str(v).split(".") if x.isdigit())
    if ver(pdef["version"]) >= ver(d.get("pluginVersion", "0")):
        d["pluginHtml"] = card["html"]; d["pluginVersion"] = pdef["version"]
    else:
        print("  版子上的插件 %s 比本機新，沿用它的 HTML" % d.get("pluginVersion"))
    if a.start:
        for n in nodes: n["data"].pop("start", None)
        d["start"] = True
    node = {"id": nid, "type": "story", "position": (prev or {}).get("position") or {"x": 0, "y": 0}, "data": d}
    if prev and prev.get("parentId"): node["parentId"] = prev["parentId"]
    nodes = [n for n in nodes if n["id"] != nid] + [node]
    print("卡片", nid, "|", "更新" if prev else "新增", "| 內容", len(content), "字 | 其他卡", len(nodes) - 1, "張")
    if a.dry:
        json.dump(node, open(os.path.join(HERE, "dist", "last-node.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("--dry：只寫 dist/last-node.json"); return

    if need_enable:
        # 整包 PUT 只留你送的欄位、boards 送了也會被清，所以：先抓全部版子，PUT 專案，再把版子逐張推回去
        snap = api("GET", "/projects/%s" % pid); snap = snap.get("project", snap)
        json.dump(snap, open(os.path.join(HERE, "dist", "snapshot-%s-%d.json" % (pid[-8:], int(time.time()))), "w", encoding="utf-8"), ensure_ascii=False)
        boards = snap.get("boards") or []
        snap.setdefault("settings", {}).setdefault("plugins", {})[pdef["id"]] = {"enabled": True, "version": pdef["version"]}
        api("PUT", "/projects/%s" % pid, {"project": snap})
        for bd in boards:
            api("GET", "/projects/%s/boards/%s" % (pid, bd["id"]))
            api("PUT", "/projects/%s/boards/%s" % (pid, bd["id"]), {"name": bd.get("name"), "nodes": bd.get("nodes", []), "edges": bd.get("edges", []), "summary": "導入簡報插件後原樣推回"})
        chk = api("GET", "/projects/%s" % pid); chk = chk.get("project", chk)
        assert (chk.get("settings", {}).get("plugins", {}).get(pdef["id"]) or {}).get("enabled"), "settings.plugins 沒寫進去"
        for bd in boards:
            got = api("GET", "/projects/%s/boards/%s" % (pid, bd["id"])); got = got.get("board", got)
            assert len(got.get("nodes", [])) == len(bd.get("nodes", [])), "版子 %s 卡數不符" % bd["id"]
        print("settings.plugins 已寫入，版子原樣推回")

    api("GET", "/projects/%s/boards/%s" % (pid, board))
    api("PUT", "/projects/%s/boards/%s" % (pid, board), {"name": b.get("name"), "nodes": nodes, "edges": edges, "summary": "更新簡報卡 %s" % nid})
    got = api("GET", "/projects/%s/boards/%s" % (pid, board)); got = got.get("board", got)
    mine = next((n for n in got.get("nodes", []) if n["id"] == nid), None)
    assert mine and mine["data"]["pluginValues"]["content"] == content, "回讀內容不符"
    assert len(got.get("nodes", [])) == len(nodes) and len(got.get("edges", [])) == len(edges), "回讀卡數/邊數不符"
    print("回讀 OK: nodes", len(got["nodes"]), "edges", len(got["edges"]))
    pv = api("GET", "/projects/%s/preview?boardId=%s" % (pid, board))
    print("preview:", pv.get("playUrl") or pv.get("url"))

if __name__ == "__main__":
    main()
