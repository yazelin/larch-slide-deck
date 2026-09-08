#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一份簡報標記檔切成好幾張插件卡，依序接線推上同一個版子。

    python3 split.py --project project-xxxx --deck example/0909-larch-vn.md \
        --breaks 6,7,8,9,10,13 --prefix deck-0909 [--after deck-0909-after] [--dry]

為什麼要切：一場邊講邊帶的直播，講述與動手是交錯的。一張卡一整份簡報的話，
動手那十分鐘簡報就停在那裡；切成一段一張卡，講完那一段按「結束」就交還給白板，
下一段再從下一張卡開始。

--breaks 給的是「新的一段從第幾頁開始」（1 起算）。上面那組會切成七段：
1-5 開場、6 動手一、7 動手二、8 平台 AI、9 共用白板、10-12 Agent、13-17 收尾。

每一段會自動處理三件事：
- **節奏歸零**：原檔的 [pace=N] 是從開場算起的累積分鐘，切段後每張卡的計時器都從 0 開始，
  所以把它改寫成「這一段自己的分鐘數」，超時才會正確轉紅。
- **結束鈕**：自動寫成「下一段：<下一段的標題>」，最後一段用檔頭的 endLabel。
- **副標**：左上角顯示「第 N / 共 M 段 · 這一段的標題」，講到哪一段一眼看得到。
- **銜接卡**：兩張連續的同種插件卡，播放器會沿用前一張留下的 iframe，第二張不會啟動
  （larch-vn skill 記過同樣的坑）。所以每兩段之間自動插一張旁白卡隔開，順便報下一段要做什麼。
  `--no-bridge` 可以關掉。
"""
import argparse, json, os, re, sys
import push   # 共用 api()、load_deck()、build_node()、load_plugin()、enable_plugin()

HERE = os.path.dirname(os.path.abspath(__file__))

def slides_of(content):
    """切成一頁一段，保留原文（含頁首標籤與 > 講稿）。"""
    return [s for s in re.split(r"\n---\s*\n", "\n" + content.strip() + "\n") if s.strip()]

def title_of(slide):
    m = re.search(r"^# (.+)$", slide, re.M)
    return re.sub(r"\*\*|\s+", lambda x: "" if x.group(0) == "**" else " ", m.group(1)).strip() if m else "（無標題）"

def pace_of(slide):
    m = re.search(r"^\[([^\]]*)\]", slide, re.M)
    if not m: return None
    m2 = re.search(r"pace=([\d.]+)", m.group(1))
    return float(m2.group(1)) if m2 else None

def set_pace(slide, minutes):
    """把頁首的 pace 換成新的值；沒有頁首標籤就補一個。"""
    def repl(m):
        tags = re.sub(r"\s*pace=[\d.]+", "", m.group(1)).strip()
        return "[%s]" % (tags + (" " if tags else "") + "pace=%g" % minutes)
    if re.search(r"^\[[^\]]*\]", slide, re.M):
        return re.sub(r"^\[([^\]]*)\]", repl, slide, count=1, flags=re.M)
    return re.sub(r"^(\s*)", r"\1[pace=%g]\n" % minutes, slide, count=1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True); ap.add_argument("--deck", required=True)
    ap.add_argument("--breaks", required=True, help="新的一段從第幾頁開始，逗號分隔，例如 6,7,8,9,10,13")
    ap.add_argument("--prefix", default=None, help="卡片 id 前綴，預設用檔名")
    ap.add_argument("--board", default=None); ap.add_argument("--after", default=None, help="最後一段之後要接的既有卡片 id")
    ap.add_argument("--dry", action="store_true", help="只產檔與印出切法，不寫 Larch")
    ap.add_argument("--no-bridge", action="store_true", help="不要在兩段之間插旁白銜接卡（連兩張插件卡播放器會卡住，除非你自己隔開）")
    ap.add_argument("--narrator", default="旁白", help="銜接卡的說話者，預設「旁白」")
    a = ap.parse_args()

    pid = a.project; board = a.board or "board-%s-main" % pid
    prefix = a.prefix or ("deck-" + os.path.splitext(os.path.basename(a.deck))[0])
    head, content = push.load_deck(a.deck)
    slides = slides_of(content)
    breaks = sorted({int(x) for x in a.breaks.split(",") if x.strip()})
    starts = [1] + [b for b in breaks if 1 < b <= len(slides)]
    bounds = list(zip(starts, [s - 1 for s in starts[1:]] + [len(slides)]))

    segs = []
    for i, (lo, hi) in enumerate(bounds):
        part = slides[lo - 1:hi]
        base = pace_of(slides[lo - 2]) if lo > 1 else 0          # 這一段開始時，整場已經過了幾分鐘
        rewritten = []
        for s in part:
            p = pace_of(s)
            rewritten.append(set_pace(s, round((p - (base or 0)), 2)) if p is not None and base is not None else s)
        segs.append({"no": i + 1, "lo": lo, "hi": hi, "title": title_of(part[0]),
                     "budget": (pace_of(part[-1]) or 0) - (base or 0), "text": "\n---\n".join(rewritten)})

    print("《%s》%d 頁 → %d 段" % (os.path.basename(a.deck), len(slides), len(segs)))
    for s in segs:
        print("  %d. 第 %2d-%-2d 頁  %5.0f 分  %s" % (s["no"], s["lo"], s["hi"], s["budget"], s["title"]))

    outdir = os.path.join(HERE, "dist", "segments"); os.makedirs(outdir, exist_ok=True)
    pdef, card = push.load_plugin()
    nodes_new = []
    for s in segs:
        v = {f["key"]: f.get("defaultValue", "") for f in card["fields"]}
        v.update(head)
        v["content"] = s["text"]
        v["subtitle"] = "%s · %d/%d %s" % (head.get("subtitle", "").strip() or "簡報", s["no"], len(segs), s["title"])
        nxt = next((x for x in segs if x["no"] == s["no"] + 1), None)
        v["endLabel"] = ("下一段：" + nxt["title"]) if nxt else (head.get("endLabel") or "簡報結束")
        # 開播前清單與常見問答只放第一段，其他段的主控台不重複塞
        if s["no"] != 1: v["flight"] = ""; v["faq"] = ""
        s["values"] = v; s["id"] = "%s-%d" % (prefix, s["no"])
        open(os.path.join(outdir, "%s.md" % s["id"]), "w", encoding="utf-8").write(s["text"])

    if a.dry:
        print("--dry：切好的段落寫在 %s，沒有動 Larch" % outdir); return

    proj = push.api("GET", "/projects/%s" % pid); proj = proj.get("project", proj)
    if not ((proj.get("settings") or {}).get("plugins") or {}).get(pdef["id"], {}).get("enabled"):
        print("插件未導入，寫 settings.plugins"); push.enable_plugin(pid, pdef)

    b = push.api("GET", "/projects/%s/boards/%s" % (pid, board)); b = b.get("board", b)
    old = {n["id"]: n for n in b.get("nodes", [])}
    ids = [s["id"] for s in segs]
    keep = [n for n in b.get("nodes", []) if n["id"] not in ids and n["id"] != a.prefix]   # 舊的單張大卡一併換掉
    for i, s in enumerate(segs):
        prev = old.get(s["id"])
        n = push.build_node(pdef, card, s["id"], "%d. %s" % (s["no"], s["title"]), s["values"], prev, start=(i == 0))
        if not prev: n["position"] = {"x": 360 * i, "y": 0}
        nodes_new.append(n)
    for n in keep: n["data"].pop("start", None)
    nodes = keep + nodes_new

    # 銜接卡：兩張連續的同種插件卡，播放器會沿用前一張的 iframe，第二張不啟動。中間隔一張對話卡就正常。
    bridges = []
    if not a.no_bridge and len(segs) > 1:
        chars = push.api("GET", "/projects/%s/characters" % pid); chars = chars.get("characters", chars)
        who = next((c for c in chars if c["name"] == a.narrator), None)
        if not who:
            push.api("POST", "/projects/%s/characters" % pid, {"name": a.narrator, "role": "旁白", "summary": "簡報段落之間的銜接。"})
            chars = push.api("GET", "/projects/%s/characters" % pid); chars = chars.get("characters", chars)
            who = next(c for c in chars if c["name"] == a.narrator)
        for i, s2 in enumerate(segs[1:], start=1):
            bid = "%s-br%d" % (prefix, i)
            line = "接下來：%s（約 %.0f 分鐘）" % (s2["title"], s2["budget"])
            prev = old.get(bid)
            d = dict((prev or {}).get("data") or {})
            d.update({"type": "dialogue", "title": "銜接 → %s" % s2["title"], "speaker": a.narrator, "characterId": who["id"],
                      "text": line, "dialogueLines": [{"id": "l0", "speaker": a.narrator, "text": line, "emotion": ""}],
                      "stage": {"actors": []}, "characterLayers": []})
            n = {"id": bid, "type": "story", "position": (prev or {}).get("position") or {"x": 360 * i - 180, "y": 160}, "data": d}
            bridges.append(n); nodes.append(n)

    chain = []
    for i, s2 in enumerate(segs):
        if i: chain.append("%s-br%d" % (prefix, i)) if not a.no_bridge and len(segs) > 1 else None
        chain.append(s2["id"])
    if a.after and any(n["id"] == a.after for n in nodes): chain.append(a.after)
    edges = [e for e in b.get("edges", []) if e.get("source") not in chain]
    for x, y in zip(chain, chain[1:]):
        edges.append({"id": "e-%s-%s" % (x, y), "source": x, "target": y})

    push.api("GET", "/projects/%s/boards/%s" % (pid, board))
    push.api("PUT", "/projects/%s/boards/%s" % (pid, board),
             {"name": b.get("name"), "nodes": nodes, "edges": edges, "summary": "簡報切成 %d 段" % len(segs)})
    got = push.api("GET", "/projects/%s/boards/%s" % (pid, board)); got = got.get("board", got)
    back = {n["id"]: n for n in got.get("nodes", [])}
    for s in segs:
        assert s["id"] in back, "回讀少了 %s" % s["id"]
        assert back[s["id"]]["data"]["pluginValues"]["content"] == s["text"], "%s 內容不符" % s["id"]
    links = {(e["source"], e["target"]) for e in got.get("edges", [])}
    for x, y in zip(chain, chain[1:]):
        assert (x, y) in links, "少了連線 %s → %s" % (x, y)
    print("回讀 OK：nodes %d、edges %d，%d 段內容與接線都對%s" % (len(got["nodes"]), len(got["edges"]), len(segs),
          "（含 %d 張銜接卡）" % len(bridges) if bridges else ""))
    pv = push.api("GET", "/projects/%s/preview?boardId=%s" % (pid, board))
    print("preview:", pv.get("playUrl") or pv.get("url"))

if __name__ == "__main__":
    main()
