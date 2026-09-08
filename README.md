# larch-slide-deck

Larch 視覺小說平台的簡報插件卡。一張卡就是一整份 16:9 簡報，內容用 Markdown 型標記寫在卡片的「簡報內容」欄位，播放器裡全螢幕播。做這個是為了把每週直播的簡報直接放在 Larch 專案裡講，講完接著就在同一個播放器裡示範。

- 頁型：封面、條列、表格、雙欄／三欄、程式碼、宣言；深色與淺色兩種底。
- 操作：`←` `→` `空白鍵` `PageDown` 翻頁、`Home` `End` 首尾頁、`N` 講稿抽屜、`P` 講者主控台（縮圖跳頁、講稿、下一頁、節奏計時、開播前清單、常見問答）、`R` 計時歸零、點畫面右 2/3 下一頁、手機左右滑。
- 第二畫面看講稿：主控台按「手機遙控」，掃 QR 或複製網址，開在第二個視窗、第二台螢幕或手機上。那一頁有頁碼、標題、講稿全文、跳頁清單、雷射筆與螢光筆，也能翻頁，兩邊即時同步。走 `deck-sync` worker 的 WebSocket。
- 頁內嵌外站：一行 `@embed 網址`。
- 配色：三組預設（琥珀墨黑、桃粉霧色、薄荷深海），主色、底色、字色可各自覆寫；字級倍率可調。
- 最後一頁出「結束」鈕，按了送 `larch:complete`，插件卡會自己接下一張卡。

樣式是 [slide-deck skill](https://github.com/yazelin/slide-deck-skill) 的 `deck.css`，同一套規則、同一組變數。

## 標記規格

一頁一段，段與段之間放一行 `---`。每段的第一行可以是方括號標籤，後面是內容。

| 寫法 | 意思 |
|---|---|
| `[cover]` | 封面：標題用最大字級，段落當副標 |
| `[light]` | 淺色底 |
| `[statement]` | 宣言頁：一句大字加一段小字 |
| `[cols]` | 雙欄或三欄，欄與欄之間放一行 `\|\|\|` |
| `[dense]` | 表格用緊湊字級（列多的時候） |
| `[pace=45]` | 講到這頁應該不超過的累積分鐘數，超過主控台的計時器轉紅 |
| `## 小標` | 標題上方那行小字（kicker） |
| `# 標題` | 頁標題。`**粗體**` 的部分變強調色 |
| `### 小節` | 欄內小標（雙欄用） |
| `- 條列` | 重點條列。`**粗體**` 變強調色，`_底線_` 變灰字補充 |
| `\| a \| b \|` | 表格列。第二列寫 `\| --- \| --- \|` 的話第一列變表頭；`\|! ` 開頭的列是分組列 |
| ```` ``` ```` | 程式碼區塊，到下一個 ```` ``` ```` 為止 |
| 其他文字 | 封面與宣言頁當副標，其他頁當頁尾小字，欄內當一般段落 |
| `> 備註` | 講稿備註，只在 N 抽屜、P 主控台、手機遙控看得到。可以多行 |
| `@embed 網址` | 右側嵌一個視窗（寬 32%，左欄字自動縮一級） |
| `@embed 網址 full` | 標題下方全寬視窗 |
| `@embed 網址 lazy` | 右側視窗，按「載入」才載 |
| `@img 網址 說明` | 圖片，點了放大 |
| `[文字](網址)` | 連結（開新分頁） |
| `` `code` `` | 行內程式碼 |

標籤可以疊：`[light dense pace=8]`。

嵌站的條件：對方沒設 `X-Frame-Options`（GitHub Pages 沒有，Larch 市集頁有），而且對方站要禁得起「沒有儲存空間」的環境。這張卡是 sandbox iframe，裡面再嵌的站 origin 會是 `null`，`localStorage`、IndexedDB、Service Worker 全部一碰就丟 SecurityError，音訊要標 `crossorigin="anonymous"` 才進得了 Web Audio。這三件在格莉奇OS 與格莉奇音樂上都踩過。

### 標記檔的檔頭

用 `push.py` 推的檔案，第一段可以放設定（每行 `鍵: 值`，到第一個 `---` 為止），鍵就是卡片欄位：`brand`、`subtitle`、`theme`（amber／peach／mint）、`accent`、`ink`、`cream`、`dayBg`、`dayAccent`、`fontScale`、`clickNav`、`remoteServer`、`remoteRoom`、`remotePin`、`showEnd`、`endLabel`、`flight`（主控台開播前清單，一行一項）、`faq`（一行一題，寫成 `問題|答案`）。

範例：`example/sample.md`（六種頁型各一）、`example/0909-larch-vn.md`（2026-09-09 直播的整份簡報，17 頁）。

## 檔案

| 檔案 | 用途 |
|---|---|
| `card.src.html` | 卡片原始碼：標記解析、畫面、主控台、遙控、Larch 協定 |
| `deck.css` | slide-deck skill 的樣式，原樣 |
| `qrcode.min.js` | 手機遙控的 QR（離線） |
| `manifest.py` | 組成 `dist/card.html` 與上傳用的 `dist/slide-deck-<版>.json` |
| `push.py` | 把一份標記檔推成某個專案裡的一張簡報卡 |
| `split.py` | 把一份標記檔切成好幾張卡、依序接線推上同一個版子 |
| `dev/check.mjs` | 本機驗收：同款 sandbox iframe 裡逐頁量溢出、測 N/P、結束鈕 |

## 使用

### 給 Agent（推薦）

```bash
python3 manifest.py                                   # 改過卡片或欄位才需要
python3 push.py --project project-xxxx --deck 我的簡報.md --card deck-0909 --title 開場簡報 --start
node dev/check.mjs 我的簡報.md --shots                  # 推之前先在本機驗：溢出、頁數、備註、按鍵
```

`push.py` 會：讀 `~/.config/larch/key`；寫入帶 `If-Match`（讀回來的 ETag），編輯器改過就被擋而不是蓋掉；專案沒導入插件就寫 `settings.plugins`（先抓版子、PUT 專案、再原樣推回）；同 id 的卡就地更新、沿用座標，其他卡不動；推完回讀比對內容與卡數，印預覽網址。

### 邊講邊帶的場次：切成好幾張卡

一場講述與動手交錯的直播，簡報停在原地十分鐘很浪費。把它切段，講完一段按「結束」就交還給白板，下一段從下一張卡開始：

```bash
python3 split.py --project project-xxxx --deck 我的簡報.md \
    --breaks 6,7,8,9,10,13 --prefix deck-0909 --after deck-0909-after --dry
```

`--breaks` 給的是「新的一段從第幾頁開始」。`--dry` 先看切法與每段幾分鐘，確認了再拿掉。它會自動：

- **把節奏歸零**。原檔的 `[pace=N]` 是從開場算起的累積分鐘，切段後每張卡的計時器都從 0 開始，所以改寫成這一段自己的分鐘數，超時才會正確轉紅。
- **寫結束鈕**：「下一段：<下一段的標題>」，最後一段用檔頭的 `endLabel`。
- **寫副標**：左上角顯示「第 N/M 段 · 這一段的標題」。
- **接線**：一段接一段，最後接到 `--after` 指定的既有卡片。原本那張沒切的大卡（id 等於 `--prefix`）會被換掉。

推之前每一段都可以單獨驗：`node dev/check.mjs dist/segments/deck-0909-2.md`。

### 在 Larch 網頁上

1. 帳號 → 我的素材 → 插件，上傳 `dist/slide-deck-<版>.json`。
2. 進專案，從「我的素材」導入這個插件。
3. 白板上加「簡報」卡，把標記貼進「簡報內容」，其他欄位照喜好。

上架到插件市集只能在網頁上做（agent API 發不了插件）。

## 已知限制

- 第二畫面走 WebSocket，不是原 slide-deck 的 `localStorage` 跨視窗（sandbox iframe 是 opaque origin，兩邊不共用儲存空間）。效果一樣，但**房號預設每次隨機**：卡片重新載入就換一間房，第二畫面要重開。開播前就想架好第二台螢幕的話，把「遙控房號」與「遙控密碼」填死，網址就固定。房號等於進場券，取一個別人猜不到的；作品發佈到市集之後這兩個值在公開 JSON 裡看得到。
- 沒有縮圖：主控台跳頁列表只有頁碼與標題。
- 圖片要是網址（放素材庫拿網址，或外部圖床）。

## 授權

MIT © 林亞澤
