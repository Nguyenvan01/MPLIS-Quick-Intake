'use strict';
// Mở trình duyệt để người dùng tự đăng nhập, giải captcha. Script không thao tác gì trên trang.
const fs = require('fs');
const readline = require('readline');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto('https://hye.mplis.gov.vn');
  console.log('Đăng nhập đến khi vào được trang chính, rồi nhấn Enter ở terminal này để lưu phiên.');

  const rl = readline.createInterface({ input: process.stdin });
  let enter = false;
  rl.once('line', () => { enter = true; });
  while (!enter && browser.isConnected() && context.pages().length) await new Promise((r) => setTimeout(r, 300));
  rl.close();

  if (!browser.isConnected()) throw new Error('Trình duyệt đã thoát trước khi lưu. Chạy lại và nhấn Enter thay vì Cmd+Q.');
  // Chỉ gọi một lần: mỗi lần gọi storageState mở một trang tạm, gọi lặp sẽ làm cửa sổ nháy.
  await context.storageState({ path: 'auth.json' });
  fs.chmodSync('auth.json', 0o600);
  await browser.close();
  console.log('Đã lưu phiên vào auth.json');
})();
