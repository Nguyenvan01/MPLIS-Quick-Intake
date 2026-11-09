'use strict';
// Cửa sổ để Claude đọc và thao tác qua cổng 9222; người dùng tự đăng nhập.
// Mọi lệnh ghi lên hye.mplis.gov.vn bị chặn, trừ khi có file cho_ghi (chỉ tạo khi người dùng đồng ý cho từng lần Lưu).
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { gan } = require('./harvest');

const RA = 'harvest/dieu_khien';
const CHO_GHI = path.join(RA, 'cho_ghi');
const CHO_PHEP = path.join(RA, 'cho_phep.txt'); // lệnh đọc đã được người dùng duyệt, mỗi dòng một 'Controller/Action'

function choPhep(url, method, coChoGhi, them = []) {
  const u = new URL(url);
  if (coChoGhi || ['GET', 'HEAD'].includes(method) || u.hostname !== 'hye.mplis.gov.vn') return true; // đăng nhập nằm ở authen.mplis.gov.vn
  return u.pathname.includes('/signalr/') || /^get/i.test(u.pathname.split('/').pop()) || them.some((x) => u.pathname.endsWith('/' + x));
}

async function main() {
  fs.mkdirSync(RA, { recursive: true });
  fs.rmSync(CHO_GHI, { force: true }); // mở lại luôn về trạng thái chặn
  const context = await chromium.launchPersistentContext(path.join(RA, 'profile'), {
    headless: false, args: ['--remote-debugging-port=9222', '--remote-debugging-address=127.0.0.1'],
  });
  await context.route('**/*', (route) => {
    const r = route.request();
    const them = fs.existsSync(CHO_PHEP) ? fs.readFileSync(CHO_PHEP, 'utf8').split('\n').filter(Boolean) : []; // đọc mỗi lần để khỏi mở lại trình duyệt
    if (choPhep(r.url(), r.method(), fs.existsSync(CHO_GHI), them)) return route.continue();
    fs.appendFileSync(path.join(RA, 'bi_chan.jsonl'), JSON.stringify({ t: new Date().toISOString(), method: r.method(), url: r.url().split('?')[0] }) + '\n');
    return route.abort();
  });
  await gan(context, RA);
  const page = context.pages()[0] || await context.newPage();
  await page.goto('https://hye.mplis.gov.vn/dc/TiepNhanHoSo');
  console.log('Sẵn sàng. Đăng nhập trong cửa sổ này.');
  await new Promise((r) => context.on('close', r));
}

if (require.main === module) main();
module.exports = { choPhep };
