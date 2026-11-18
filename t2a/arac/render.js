// HTML animasyonu kare kare çekip ffmpeg ile videoya çevirir.
// Sayfa window.DURATION (sn) ve window.seek(t) sağlamalı.
// Kullanım: node render.js sahne.html cikti.mp4 [ses.wav] [--fps 30] [--onizleme 1.5,5,9]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

(async () => {
  const args = process.argv.slice(2);
  const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
  const fps = Number(opt('--fps', 30));
  const preview = opt('--onizleme', null);
  const [html, out, audio] = args;

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => window.hazir ? window.hazir() : 0);
  const dur = await page.evaluate(() => window.DURATION);

  if (preview) {
    for (const t of preview.split(',').map(Number)) {
      await page.evaluate(t => window.seek(t), t);
      await page.screenshot({ path: `${out}-${t}.png` });
    }
    await browser.close();
    return;
  }

  const ff = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-'];
  if (audio) ff.push('-i', audio);
  ff.push('-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(fps),
    '-movflags', '+faststart');
  if (audio) ff.push('-c:a', 'aac', '-b:a', '192k', '-shortest');
  ff.push(out);
  const proc = spawn('ffmpeg', ff, { stdio: ['pipe', 'inherit', 'inherit'] });

  const total = Math.round(dur * fps);
  for (let f = 0; f < total; f++) {
    await page.evaluate(t => window.seek(t), f / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!proc.stdin.write(buf)) await new Promise(r => proc.stdin.once('drain', r));
    if (f % 60 === 0) process.stdout.write(`\r${f}/${total}`);
  }
  proc.stdin.end();
  await new Promise(r => proc.on('close', r));
  await browser.close();
  console.log(`\nbitti: ${out}`);
})();
