'use strict';
// Chạy trên trang giả lập qua context.route, không có request nào ra mạng thật.
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { test } = require('node:test');
const { chromium } = require('playwright');
const { gan } = require('../harvest');

const THU_MUC = 'harvest-test';
const CCCD = '012345678901';

test('harvest ghi đủ 6 loại và không lộ dữ liệu nhạy cảm', async (t) => {
  fs.rmSync(THU_MUC, { recursive: true, force: true });
  const browser = await chromium.launch();
  t.after(() => browser.close()); // assert hỏng mà không đóng thì test treo
  const context = await browser.newContext();
  await context.route('**/*', (route) => {
    const url = route.request().url();
    if (url.includes('/api/tim')) return route.fulfill({ json: { data: [{ hoTen: 'A', cccd: CCCD }], tong: 1 } });
    if (url === 'http://mplis.test/') return route.fulfill({ path: path.join(__dirname, 'harvest_fixture.html'), contentType: 'text/html; charset=utf-8' });
    return route.abort();
  });
  await gan(context, THU_MUC);
  const page = await context.newPage();
  await page.goto('http://mplis.test/');

  const events = () => fs.readFileSync(path.join(THU_MUC, 'events.jsonl'), 'utf8').trim().split('\n').map((l) => JSON.parse(l));
  const cho = async (dk) => {
    for (let i = 0; i < 100; i++) {
      const e = fs.existsSync(path.join(THU_MUC, 'events.jsonl')) ? events().find(dk) : null;
      if (e) return e;
      await new Promise((r) => setTimeout(r, 50));
    }
    assert.fail('Không thấy bản ghi mong đợi: ' + dk);
  };

  await page.click('#them');
  const dd = await cho((e) => e.loai === 'dropdown');
  assert.deepStrictEqual(dd.luaChon, ['Cá nhân', 'Vợ chồng', 'Hộ gia đình', 'Tổ chức', 'Cộng đồng']);
  assert.match(dd.moBoi.role, /"Thêm"/);

  await page.click('#mo');
  await cho((e) => e.loai === 'modal');
  await page.fill('#soGiayTo', CCCD);
  await page.fill('#mk', 'hunter2');
  const nhap = await cho((e) => e.loai === 'nhap' && e.phanTu.id === 'soGiayTo');
  assert.strictEqual(nhap.giaTri, '0123•••901');
  assert.strictEqual(nhap.phanTu.selector.label, 'getByLabel("Số giấy tờ")');
  assert.strictEqual((await cho((e) => e.loai === 'nhap' && e.phanTu.id === 'mk')).giaTri, '***');

  await page.click('#luu');
  const bam = await cho((e) => e.loai === 'bam' && e.phanTu.id === 'luu');
  assert.strictEqual(bam.phanTu.modal.id, 'modalCaNhan');
  assert.strictEqual(bam.phanTu.selector.css, '#luu');
  assert.strictEqual(bam.phanTu.selector.role, 'getByRole("button", { name: "Lưu hồ sơ" })');

  const mang = await cho((e) => e.loai === 'mang');
  assert.deepStrictEqual(mang.ketQua, { data: { soPhanTu: 1, phanTu: { hoTen: 'string', cccd: 'string' } }, tong: 'number' });
  assert.match(mang.url, /token=\*\*\*/);
  assert.match(mang.thamSo, /password=\*\*\*/);

  assert.strictEqual((await cho((e) => e.loai === 'overlay_hien')).selector, '#dangTai');
  assert.ok((await cho((e) => e.loai === 'overlay_het')).ms >= 200);

  await page.click('#dong');
  await page.click('#mo'); // mở lại: vẫn chỉ một file
  await page.frameLocator('#khung').locator('#trongKhung').click();
  await cho((e) => e.loai === 'bam' && e.phanTu.id === 'trongKhung');

  assert.deepStrictEqual(fs.readdirSync(path.join(THU_MUC, 'modals')), ['001-Thêm-cá-nhân.html']);
  const tatCa = fs.readFileSync(path.join(THU_MUC, 'events.jsonl'), 'utf8') + fs.readFileSync(path.join(THU_MUC, 'modals', '001-Thêm-cá-nhân.html'), 'utf8');
  for (const bi of [CCCD, 'hunter2', 'bimat1']) assert.ok(!tatCa.includes(bi), 'Lộ: ' + bi);
});
