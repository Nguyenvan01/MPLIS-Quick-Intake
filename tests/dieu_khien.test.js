'use strict';
const assert = require('node:assert');
const { test } = require('node:test');
const { choPhep } = require('../dieu_khien');

const HYE = 'https://hye.mplis.gov.vn/dc/';

test('chặn lệnh ghi lên MPLIS, cho phép đọc và đăng nhập', () => {
  assert.strictEqual(choPhep(HYE + 'DangKyAjax/LuuHoSo', 'POST', false), false);
  assert.strictEqual(choPhep(HYE + 'DangKyAjax/HoanTat?x=GetA', 'POST', false), false);
  assert.strictEqual(choPhep(HYE + 'DangKyAjax/SaveGetThing', 'POST', false), false);
  assert.strictEqual(choPhep(HYE + 'DangKyAjax/LuuHoSo', 'PUT', false), false);
  assert.strictEqual(choPhep(HYE + 'DangKyAjax/GetQuyTrinh', 'POST', false), true);
  assert.strictEqual(choPhep(HYE + 'signalr/send', 'POST', false), true);
  assert.strictEqual(choPhep(HYE + 'TiepNhanHoSo', 'GET', false), true);
  assert.strictEqual(choPhep('https://authen.mplis.gov.vn/Account/Api/Login', 'POST', false), true);
  assert.strictEqual(choPhep(HYE + 'DangKyAjax/LuuHoSo', 'POST', true), true);
});

test('chỉ lệnh đúng controller trong danh sách bổ sung mới được qua', () => {
  const them = ['TaiSanAjax/AdvancedSearchThuaDat'];
  assert.strictEqual(choPhep(HYE + 'TaiSanAjax/AdvancedSearchThuaDat', 'POST', false, them), true);
  assert.strictEqual(choPhep(HYE + 'KhacAjax/AdvancedSearchThuaDat', 'POST', false, them), false);
  assert.strictEqual(choPhep(HYE + 'DangKyAjax/LuuHoSo', 'POST', false, them), false);
});
