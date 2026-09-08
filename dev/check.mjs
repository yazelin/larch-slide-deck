// 本機驗收：把 dist/card.html 放進跟 Larch 一樣的 sandbox iframe（allow-scripts、opaque origin），
// 假扮 host 送 larch:init，然後逐頁檢查：頁數對不對、有沒有溢出、備註數對不對、N/P/方向鍵有沒有反應、
// 最後一頁的結束鈕有沒有送 larch:complete。有 --shots 就每頁截圖到 dist/shots/。
//   node dev/check.mjs example/0909-larch-vn.md [--set key=value ...] [--shots]
// 用 line-sticker-studio 的 playwright（這個 repo 不裝依賴）。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '/home/ct/line-sticker-studio/node_modules/playwright/index.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const deckPath = args.find(a => !a.startsWith('--')) || path.join(HERE, '..', 'example', 'sample.md');
const shots = args.includes('--shots');
const sets = {}; args.forEach((a, i) => { if (a === '--set') { const [k, v] = args[i + 1].split('='); sets[k] = v; } });

const html = fs.readFileSync(path.join(HERE, '..', 'dist', 'card.html'), 'utf8');
let text = fs.readFileSync(deckPath, 'utf8').replace(/\r\n/g, '\n');
const values = { ...sets };
const parts = text.split('\n---\n');
if (parts.length > 1 && parts[0].split('\n').every(l => !l.trim() || (l.includes(':') && !/^[#\-\[|>@`]/.test(l)))) {
  parts[0].split('\n').forEach(l => { if (l.includes(':')) { const [k, ...v] = l.split(':'); values[k.trim()] = v.join(':').trim(); } });
  text = parts.slice(1).join('\n---\n');
}
values.content = text;
const expectSlides = text.split(/\n---\s*\n|^---\s*\n/m).filter(s => s.trim()).length;

// Larch 的插件卡外框實測給卡片 1280×655（不是 720），驗收照這個高度量
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 655 } });
const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|WebSocket/.test(m.text())) errs.push(m.text()); });   // 網路資源（遙控 WS、嵌站）失敗不算卡片壞
let completed = false;
await p.exposeFunction('__hostGot', t => { if (t === 'larch:complete') completed = true; });
await p.setContent(`<body style="margin:0"><iframe id="f" sandbox="allow-scripts" style="width:1280px;height:655px;border:0"></iframe></body>`);
// 不能把卡片 HTML 內嵌在 <script> 字串裡（裡面有 </script>），用 evaluate 直接塞 srcdoc
await p.evaluate(({ h, values }) => { const f = document.getElementById('f');
  addEventListener('message', e => { if (e.source !== f.contentWindow) return; window.__hostGot(e.data && e.data.type);
    if (e.data && e.data.type === 'larch:ready') f.contentWindow.postMessage({ type: 'larch:init', values, variables: {}, plugin: {}, card: {} }, '*'); });
  f.srcdoc = h; }, { h: html, values });
let fr; for (let i = 0; i < 40 && !fr; i++) { fr = p.frames().find(f => f !== p.mainFrame() && /srcdoc|^$/.test(f.url())); if (!fr) await p.waitForTimeout(250); }
if (!fr) { console.log('找不到 srcdoc iframe：', p.frames().map(f => f.url())); process.exit(1); }
await p.waitForTimeout(1500);
const rows = [];
const n = await fr.evaluate(() => document.querySelectorAll('.slide').length);
const notes = await fr.evaluate(() => document.querySelectorAll('#notes > div').length);
const ready = await fr.evaluate(() => document.body.classList.contains('ready'));
if (shots) fs.mkdirSync(path.join(HERE, '..', 'dist', 'shots'), { recursive: true });
await p.mouse.click(200, 620);            // 取得焦點：點左下（左 1/3 是上一頁，第一頁按了不動）
await p.keyboard.press('Home');
for (let i = 0; i < n; i++) {
  await p.waitForTimeout(i === 0 ? 1200 : 350);
  const r = await fr.evaluate(() => { const s = document.querySelector('.slide.active'); const bar = document.querySelector('.bar').getBoundingClientRect();
    let top = 1e9; s.querySelectorAll('*').forEach(k => { const rr = k.getBoundingClientRect(); if (rr.height > 0 && rr.width > 0) top = Math.min(top, rr.top); });
    return { i: document.getElementById('counter').textContent, cls: s.className.replace('slide', '').replace('active', '').trim() || '-', overflow: s.scrollHeight > s.clientHeight + 2, top: Math.round(top), bar: Math.round(bar.bottom), title: (s.querySelector('h1,h2,.big') || {}).textContent || '' }; });
  rows.push(r);
  if (shots) await p.screenshot({ path: path.join(HERE, '..', 'dist', 'shots', `s${String(i + 1).padStart(2, '0')}.png`) });
  await p.keyboard.press('ArrowRight');
}
await p.keyboard.press('n'); const notesOn = await fr.evaluate(() => document.body.classList.contains('show-notes')); await p.keyboard.press('n');
await p.keyboard.press('p'); const presentOn = await fr.evaluate(() => document.body.classList.contains('present') && document.getElementById('pnote').textContent.length > 0); await p.keyboard.press('p');
await p.keyboard.press('End'); await p.waitForTimeout(300);
const endVisible = await fr.evaluate(() => getComputedStyle(document.getElementById('larch-end')).display !== 'none');
if (endVisible) { await fr.click('#larch-end'); await p.waitForTimeout(300); }
console.table(rows.map(r => ({ 頁: r.i, 頁型: r.cls, 溢出: r.overflow ? '✗' : '', 頂: r.top, 標題: r.title.slice(0, 22) })));
const problems = [];
if (!ready) problems.push('卡片沒進入 ready（init 沒收到）');
if (n !== expectSlides) problems.push(`頁數 ${n} ≠ 標記檔的 ${expectSlides} 段`);
if (notes !== n) problems.push(`備註區塊 ${notes} ≠ 頁數 ${n}`);
rows.forEach(r => { if (r.overflow) problems.push(`第 ${r.i} 頁內容超出畫面`); if (r.top < r.bar) problems.push(`第 ${r.i} 頁內容蓋到上方狀態列`); });
if (!notesOn) problems.push('按 N 沒開備註抽屜'); if (!presentOn) problems.push('按 P 沒開主控台');
if (!endVisible) problems.push('最後一頁沒出結束鈕'); else if (!completed) problems.push('按結束鈕沒送 larch:complete');
if (errs.length) problems.push('JS 錯誤：' + errs.slice(0, 3).join(' | '));
console.log(problems.length ? '✗ ' + problems.join('\n✗ ') : `✓ ${n} 頁全過：無溢出、備註 ${notes} 則、N/P 有反應、結束鈕送出 larch:complete`);
await b.close();
process.exit(problems.length ? 1 : 0);
