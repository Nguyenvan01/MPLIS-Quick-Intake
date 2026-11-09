'use strict';
// Chỉ QUAN SÁT: người dùng tự thao tác, script không click, không điền, chỉ mở trang đầu.
// Kết quả: harvest/events.jsonl (dòng thời gian) và harvest/modals/*.html
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const TRANG_DAU = 'https://hye.mplis.gov.vn/dc/TiepNhanHoSo';

// Chạy trong mọi trang và iframe. Hàm này bị tuần tự hóa nên không dùng được biến của Node.
function tiemVao() {
  if (window.__harvestDaTiem) return;
  window.__harvestDaTiem = true;

  const MODAL = '.modal, .ui-dialog, [role=dialog]';
  const DROPDOWN = 'ul.select2-results, .select2-results__options, .dropdown-menu, .ui-autocomplete, .ui-menu, [role=listbox], [role=menu]';
  const OVERLAY = 'Đang xử lý';
  const VAI_INPUT = { checkbox: 'checkbox', radio: 'radio', button: 'button', submit: 'button', reset: 'button' };

  const gui = (rec) => window.__harvest?.(rec);
  const gon = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const hien = (el) => el.isConnected && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';

  function cssPath(el) {
    const phan = [];
    for (let e = el; e.parentElement && e !== document.body; e = e.parentElement) {
      if (e.id && !/\d{3}/.test(e.id)) { phan.unshift('#' + CSS.escape(e.id)); break; } // id có dãy số thường là id động
      const cung = [...e.parentElement.children].filter((x) => x.tagName === e.tagName);
      phan.unshift(`${e.localName}:nth-of-type(${cung.indexOf(e) + 1})`);
    }
    return phan.join(' > ');
  }

  function nhan(el) {
    const theoId = (el.getAttribute('aria-labelledby') || '').split(/\s+/).map((id) => document.getElementById(id)?.textContent).join(' ');
    return gon(el.getAttribute('aria-label')) || gon(theoId) || gon(el.labels?.[0]?.textContent);
  }

  function vaiTro(el) {
    const r = el.getAttribute('role');
    if (r) return r;
    if (el.localName === 'input') return el.type === 'hidden' ? null : VAI_INPUT[el.type] || 'textbox';
    return { button: 'button', select: 'combobox', textarea: 'textbox', a: el.hasAttribute('href') ? 'link' : null }[el.localName] || null;
  }

  function moTaModal(m) {
    if (!m) return null;
    const tieuDe = gon(m.querySelector('.modal-title, .ui-dialog-title, [role=heading], h1, h2, h3, h4, h5')?.textContent) || gon(m.getAttribute('aria-label'));
    return { id: m.id, lop: m.getAttribute('class'), tieuDe };
  }

  function moTa(el) {
    const nutInput = el.localName === 'input' && VAI_INPUT[el.type] === 'button';
    const chu = gon(el.innerText || el.textContent).slice(0, 80);
    const label = nhan(el);
    const role = vaiTro(el);
    const tenTruyCap = label || (nutInput ? el.value : chu) || el.title || el.placeholder || '';
    return {
      the: el.localName, id: el.id, name: el.getAttribute('name'), lop: el.getAttribute('class'), type: el.getAttribute('type'),
      placeholder: el.getAttribute('placeholder'), chu, label,
      labelGan: gon(el.closest('.form-group, .form-item, tr')?.querySelector('label')?.textContent), // select2 thường tách khỏi nhãn thật
      modal: moTaModal(el.closest(MODAL)),
      selector: {
        css: cssPath(el),
        role: role && tenTruyCap ? `getByRole(${JSON.stringify(role)}, { name: ${JSON.stringify(tenTruyCap)} })` : null,
        label: label ? `getByLabel(${JSON.stringify(label)})` : null,
      },
    };
  }

  // 1. Bấm chuột. Dùng pointerdown vì lúc click thì option của select2 đã bị gỡ khỏi trang.
  let bamCuoi = null;
  function ghiBam(e) {
    const el = e.target.closest?.('a, button, input, select, textarea, label, [role], li') || e.target;
    if (!el.getAttribute) return;
    bamCuoi = moTa(el);
    gui({ loai: 'bam', phanTu: bamCuoi });
    if (el.localName === 'select') { // danh sách của <select> không nằm trong DOM nên quét không thấy
      gui({ loai: 'dropdown', nguon: 'select', moBoi: bamCuoi.selector, luaChon: [...el.options].map((o) => gon(o.text)) });
    }
  }
  addEventListener('pointerdown', ghiBam, true);
  addEventListener('click', (e) => { if (e.detail === 0) ghiBam(e); }, true); // click bằng bàn phím không có pointerdown

  // 2. Nhập liệu. ponytail: select2 đổi <select> ẩn qua jQuery nên không có sự kiện; lựa chọn lấy từ bản ghi 'bam' trên option.
  const hen = new WeakMap();
  const cu = new WeakMap();
  const giaTri = (el) => {
    if (el.type === 'password') return '***';
    if (el.type === 'checkbox' || el.type === 'radio') return el.checked;
    return el.localName === 'select' ? [...el.selectedOptions].map((o) => gon(o.text)).join(', ') : el.value;
  };
  function ghiNhap(el) {
    clearTimeout(hen.get(el));
    const v = giaTri(el);
    if (cu.get(el) === v) return;
    cu.set(el, v);
    gui({ loai: 'nhap', phanTu: moTa(el), giaTri: v });
  }
  const laO = (el) => el.matches?.('input, textarea, select');
  addEventListener('input', (e) => {
    if (!laO(e.target)) return;
    clearTimeout(hen.get(e.target));
    hen.set(e.target, setTimeout(() => ghiNhap(e.target), 400));
  }, true);
  addEventListener('change', (e) => { if (laO(e.target)) ghiNhap(e.target); }, true);

  // 3, 4, 5. Modal, dropdown, overlay: quét lại sau mỗi lần trang đổi.
  const doDai = new WeakMap();
  const daGui = new Set();
  const dangHien = new Map();

  function quet() {
    henQuet = null;
    for (const m of document.querySelectorAll(MODAL)) {
      if (!hien(m)) continue;
      const html = m.outerHTML;
      if (doDai.get(m) === html.length) continue; // nội dung modal thường nạp sau khi mở nên gửi lại khi đổi
      doDai.set(m, html.length);
      gui({ loai: 'modal', ...moTaModal(m), modalCha: moTaModal(m.parentElement?.closest(MODAL)), html });
    }

    for (const d of document.querySelectorAll(DROPDOWN)) {
      if (!hien(d)) continue;
      const luaChon = [...d.children].map((c) => gon(c.textContent)).filter(Boolean);
      const khoa = luaChon.join('|');
      if (!luaChon.length || daGui.has(khoa)) continue;
      daGui.add(khoa);
      gui({ loai: 'dropdown', nguon: d.getAttribute('class') || d.getAttribute('role'), selector: cssPath(d), modal: moTaModal(d.closest(MODAL)), moBoi: bamCuoi?.selector, luaChon });
    }

    const nut = document.evaluate(`//text()[contains(., "${OVERLAY}")]/parent::*`, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    for (let i = 0; i < nut.snapshotLength; i++) {
      const el = nut.snapshotItem(i);
      if (dangHien.has(el) || !hien(el)) continue;
      dangHien.set(el, performance.now());
      gui({ loai: 'overlay_hien', chu: gon(el.textContent), id: el.id, lop: el.getAttribute('class'), selector: cssPath(el), modal: moTaModal(el.closest(MODAL)) });
    }
    for (const [el, t0] of dangHien) {
      if (hien(el) && el.textContent.includes(OVERLAY)) continue;
      dangHien.delete(el);
      gui({ loai: 'overlay_het', id: el.id, lop: el.getAttribute('class'), selector: cssPath(el), ms: Math.round(performance.now() - t0) });
    }
  }

  let henQuet = null;
  new MutationObserver(() => { henQuet ??= setTimeout(quet, 100); }).observe(document, {
    childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class', 'style', 'hidden', 'aria-hidden'],
  });
}

const cheCccd = (s) => s.replace(/(?<!\d)(\d{4})\d{5}(\d{3})(?!\d)/g, '$1•••$2'); // cùng dạng infra/logging.py::che_cccd
const cheBiMat = (s) => s.replace(/([\w.[\]-]*(?:pass|matkhau|mat_khau|token|captcha|secret|fingerprint)[\w.[\]-]*"?\s*[:=]\s*)("[^"]*"|[^&\s,}]*)/gi, '$1***');

function hinhDang(v) {
  if (Array.isArray(v)) return { soPhanTu: v.length, phanTu: v.length ? hinhDang(v[0]) : null };
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, hinhDang(x)]));
  return v === null ? 'null' : typeof v;
}

async function gan(context, thuMuc) {
  const dirModal = path.join(thuMuc, 'modals');
  fs.mkdirSync(dirModal, { recursive: true });
  const fileModal = path.join(thuMuc, 'modals.json');
  const modals = fs.existsSync(fileModal) ? JSON.parse(fs.readFileSync(fileModal, 'utf8')) : {}; // chạy lại vẫn "mỗi modal một lần"
  let seq = 0;

  const ghi = (rec) => fs.appendFileSync(path.join(thuMuc, 'events.jsonl'),
    cheCccd(JSON.stringify({ seq: ++seq, t: new Date().toISOString(), ...rec })) + '\n');

  await context.exposeBinding('__harvest', ({ frame, page }, rec) => {
    const nguon = { url: page?.url(), frame: frame?.url() };
    if (rec.loai !== 'modal') return ghi({ ...nguon, ...rec });

    const { html, ...meta } = rec;
    const khoa = `${meta.id}|${meta.tieuDe}|${meta.id || meta.tieuDe ? '' : meta.lop}`;
    if (!modals[khoa]) {
      const ten = cheCccd(meta.tieuDe || meta.id || 'khong-ten').replace(/[^\p{L}\p{N}]+/gu, '-').slice(0, 60);
      modals[khoa] = { file: `${String(Object.keys(modals).length + 1).padStart(3, '0')}-${ten}.html`, len: 0 };
      ghi({ ...nguon, ...meta, file: modals[khoa].file });
    }
    if (html.length > modals[khoa].len) { // modal mở trước rồi mới nạp dữ liệu: giữ bản đầy đủ nhất
      modals[khoa].len = html.length;
      fs.writeFileSync(path.join(dirModal, modals[khoa].file), cheCccd(html));
      fs.writeFileSync(fileModal, JSON.stringify(modals, null, 2));
    }
  });
  await context.addInitScript(tiemVao);

  context.on('page', (p) => p.on('framenavigated', (f) => {
    if (f === p.mainFrame()) ghi({ loai: 'dieu_huong', url: f.url() });
  }));

  // 6. Mạng: chỉ lưu dạng kết quả, không lưu nội dung và không lưu header/cookie.
  context.on('response', async (res) => {
    const req = res.request();
    const kieu = req.resourceType();
    if (!['xhr', 'fetch'].includes(kieu) && !(kieu === 'document' && req.method() !== 'GET')) return;
    let ketQua = null;
    try {
      const chu = await res.text();
      try { ketQua = hinhDang(JSON.parse(chu)); } catch { ketQua = `không phải JSON, ${chu.length} ký tự`; }
    } catch { ketQua = 'không đọc được nội dung'; }
    ghi({
      loai: 'mang', method: req.method(), kieu, status: res.status(), url: cheBiMat(res.url()),
      thamSo: cheBiMat(req.postData() || '').slice(0, 2000), contentType: res.headers()['content-type'],
      ms: Math.round(req.timing().responseEnd), ketQua,
    });
  });
}

async function main() {
  if (!fs.existsSync('auth.json')) throw new Error('Chưa có auth.json. Chạy: npm run login');
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ storageState: 'auth.json' });
  await gan(context, 'harvest');
  const page = await context.newPage();
  await page.goto(TRANG_DAU);
  console.log('Đang ghi vào harvest/. Thao tác tay, xong thì đóng cửa sổ trình duyệt.');
  while (browser.isConnected() && context.pages().length) await new Promise((r) => setTimeout(r, 500));
  await browser.close().catch(() => {});
}

if (require.main === module) main();
module.exports = { gan };
