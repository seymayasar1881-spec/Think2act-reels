// Render a 1080x1920 cover/thumbnail PNG with Puppeteer.
// usage: node cover.mjs <page.html> <out.png>
// The HTML is produced by think2act_reels/cover.py from templates/cover.html.
import puppeteer from "puppeteer";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , htmlPath, outPath] = process.argv;
if (!htmlPath || !outPath) {
  console.error("usage: node cover.mjs <page.html> <out.png>");
  process.exit(2);
}

const browser = await puppeteer.launch({
  headless: true,
  executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
  args: ["--no-sandbox", "--allow-file-access-from-files"],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  // Shrink the title until it fits in the lower 45% of the frame.
  await page.evaluate(() => {
    const el = document.getElementById("title");
    let size = 104;
    while (el.getBoundingClientRect().height > 1920 * 0.42 && size > 48) {
      size -= 4;
      el.style.fontSize = size + "px";
    }
  });
  await page.screenshot({ path: outPath, type: "png" });
} finally {
  await browser.close();
}
