#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 card.src.html 組成單檔 card.html，再包成 Larch 插件 manifest：
    python3 manifest.py            → dist/card.html 與 dist/slide-deck-<版>.json
改了 card.src.html、deck.css 或欄位就重跑。上傳到 Larch（帳號 → 我的素材 → 插件）之後，
每個要用的專案都要「導入」一次；push.py 直接寫 settings.plugins 也可以。"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.1.0"
ID = "slide-deck"

src = open(os.path.join(HERE, "card.src.html"), encoding="utf-8").read()
css = open(os.path.join(HERE, "deck.css"), encoding="utf-8").read()
qr = open(os.path.join(HERE, "qrcode.min.js"), encoding="utf-8").read()
assert "/*@deck.css*/" in src and "/*@qrcode.min.js*/" in src
html = src.replace("/*@deck.css*/", css).replace("/*@qrcode.min.js*/", qr)
os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
open(os.path.join(HERE, "dist", "card.html"), "w", encoding="utf-8").write(html)

SAMPLE = open(os.path.join(HERE, "example", "sample.md"), encoding="utf-8").read()
fields = [
 {"key": "content", "label": "簡報內容", "labelEn": "Deck content", "kind": "longText", "defaultValue": SAMPLE,
  "hint": "一頁一段，用一行 --- 分頁。頁首 [cover] [light] [statement] [cols] [dense] [pace=分鐘]；# 標題（**粗**變強調色）；## 小標；- 條列（_底線_變灰字）；| 表格 |；``` 程式碼；> 講稿備註；@embed 網址 嵌右側（加 full 全寬、lazy 按了才載）；@img 網址。一段以 <section 開頭就當手寫 HTML 原樣用。完整規格：github.com/yazelin/larch-slide-deck"},
 {"key": "brand", "label": "左上角名稱", "labelEn": "Brand", "kind": "text", "defaultValue": "簡報"},
 {"key": "subtitle", "label": "左上角副標", "labelEn": "Subtitle", "kind": "text", "defaultValue": ""},
 {"key": "theme", "label": "配色", "labelEn": "Theme", "kind": "select", "defaultValue": "amber",
  "options": [{"value": "amber", "label": "琥珀墨黑", "labelEn": "Amber on ink"},
              {"value": "peach", "label": "桃粉霧色", "labelEn": "Peach on mist"},
              {"value": "mint", "label": "薄荷深海", "labelEn": "Mint on deep sea"}]},
 {"key": "accent", "label": "強調色（選填，#hex）", "labelEn": "Accent override", "kind": "text", "defaultValue": "", "hint": "留空用配色預設。"},
 {"key": "ink", "label": "深色頁底色（選填）", "labelEn": "Dark background override", "kind": "text", "defaultValue": ""},
 {"key": "cream", "label": "深色頁字色（選填）", "labelEn": "Dark text override", "kind": "text", "defaultValue": ""},
 {"key": "dayBg", "label": "淺色頁底色（選填）", "labelEn": "Light background override", "kind": "text", "defaultValue": ""},
 {"key": "dayAccent", "label": "淺色頁強調色（選填）", "labelEn": "Light accent override", "kind": "text", "defaultValue": ""},
 {"key": "fontScale", "label": "字級倍率", "labelEn": "Font scale", "kind": "number", "min": 0.6, "max": 1.6, "step": 0.05, "defaultValue": 1},
 {"key": "clickNav", "label": "點畫面翻頁", "labelEn": "Click to navigate", "kind": "toggle", "defaultValue": True,
  "hint": "右 2/3 下一頁、左 1/3 上一頁；按鈕、連結、內嵌視窗上不翻。"},
 {"key": "remoteServer", "label": "手機遙控伺服器", "labelEn": "Phone remote server", "kind": "text",
  "defaultValue": "https://deck-sync.yazelinj303.workers.dev", "hint": "主控台的「手機遙控」用它配對。留空就關掉。"},
 {"key": "remoteRoom", "label": "遙控房號（選填）", "labelEn": "Remote room (optional)", "kind": "text", "defaultValue": "",
  "hint": "留空每次隨機。填了網址就固定，可以開播前先把遙控頁開在第二個視窗或第二台螢幕。取一個別人猜不到的。"},
 {"key": "remotePin", "label": "遙控密碼（選填）", "labelEn": "Remote pin (optional)", "kind": "text", "defaultValue": "",
  "hint": "留空每次隨機。房號固定的話這個也要固定，網址才不會變。"},
 {"key": "showEnd", "label": "最後一頁出「結束」鈕", "labelEn": "Show end button on last slide", "kind": "toggle", "defaultValue": True,
  "hint": "按了才接下一張卡。關掉的話玩家要按平台的略過。"},
 {"key": "endLabel", "label": "結束鈕文字", "labelEn": "End button label", "kind": "text", "defaultValue": "簡報結束，繼續"},
 {"key": "flight", "label": "主控台：開播前清單", "labelEn": "Presenter: pre-flight", "kind": "longText", "defaultValue": "", "hint": "只在 P 主控台看得到，一行一項。"},
 {"key": "faq", "label": "主控台：常見問答", "labelEn": "Presenter: FAQ", "kind": "longText", "defaultValue": "", "hint": "一行一題，寫成「問題|答案」。"},
]
manifest = {
 "id": ID, "name": "簡報", "nameEn": "Slide deck", "version": VERSION,
 "author": "林亞澤", "authorHandle": "yaze", "pricing": "free", "icon": "presentation",
 "categories": ["card"], "license": "MIT · 林亞澤",
 "description": "全螢幕 16:9 簡報卡。內容用 Markdown 型標記寫，一行 --- 分頁，有封面、條列、表格、雙欄、程式碼、宣言五種頁型與深淺兩種底；"
                "←→ 翻頁、N 備註抽屜、P 講者主控台（縮圖跳頁、講稿、節奏計時），講稿也能開在第二個視窗或手機上（掃 QR 或複製網址），附雷射筆；頁內可嵌外站。"
                "三組配色可再覆寫主色。最後一頁出「結束」鈕接下一張卡。",
 "descriptionEn": "Fullscreen 16:9 slide deck card. Write slides in a Markdown-like markup separated by ---, with cover, bullet, table, "
                  "two-column, code and statement layouts in dark or light. Arrow keys to navigate, N for notes, P for the presenter console "
                  "(thumbnails, script, pacing timer), phone remote with laser pointer via QR, live site embeds. Three colour presets with overrides. "
                  "An end button on the last slide advances to the next card.",
 "permissions": ["flow:control"],
 "cards": [{
   "id": "deck", "name": "簡報", "nameEn": "Slide deck",
   "description": "一張卡一整份簡報。內容欄一頁一段，講稿寫在 > 開頭的行，按 P 開主控台。",
   "descriptionEn": "One card holds a whole deck. One slide per block, speaker notes on lines starting with >, press P for the presenter console.",
   "icon": "presentation", "color": "#b8862b", "presentation": "fullscreen", "skippable": True,
   "readVariables": [], "writeVariables": [], "fields": fields, "html": html}],
}
out = os.path.join(HERE, "dist", "%s-%s.json" % (ID, VERSION))
json.dump(manifest, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(out, os.path.getsize(out), "bytes;", len(fields), "fields; card.html", len(html), "bytes")
