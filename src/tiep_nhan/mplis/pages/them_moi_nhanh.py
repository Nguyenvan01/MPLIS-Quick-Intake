"""Form "Thêm mới nhanh thông tin tiếp nhận hồ sơ".

TODO(locators): thứ tự thao tác dưới đây là phỏng đoán; sửa theo bản ghi codegen thật.
"""
from __future__ import annotations

import re

from playwright.sync_api import expect

from ...domain.danh_muc import DanhMuc
from ...domain.models import HoSo
from ..locators import ChuaCoLocator
from ..mapping import gia_tri_nguoi, gia_tri_thua_nha
from .base import BasePage


class ThemMoiNhanhPage(BasePage):
    def __init__(self, page, L, dm: DanhMuc):
        super().__init__(page, L)
        self.dm = dm

    def form(self):
        return self.el("them_moi_nhanh.vung_form") if self.L.co("them_moi_nhanh.vung_form") else self.page

    def mo(self) -> None:
        self.el("them_moi_nhanh.mo_form").click()
        expect(self.el("them_moi_nhanh.nut_luu")).to_be_visible()

    def dien(self, hs: HoSo) -> None:
        f = self.form()
        truong = self.L.section("them_moi_nhanh.truong")
        for i, d in enumerate(hs.dong):
            if i > 0:
                self.el("them_moi_nhanh.nut_them_thua", f).click()   # chỉ dùng khi gộp nhiều dòng
            for key, value in gia_tri_thua_nha(d, self.dm).items():
                if key in truong:
                    self.dien_o(f"them_moi_nhanh.truong.{key}", value, f, truong[key].get("kind", "text"))
            for n in d.nguoi:
                self.them_nguoi(gia_tri_nguoi(n))

    def them_nguoi(self, vals: dict[str, str]) -> None:
        self.el("them_moi_nhanh.nut_them_nguoi", self.form()).click()
        hop = self.el("them_moi_nhanh.hop_thoai_nguoi")
        expect(hop).to_be_visible()
        o = self.L.section("them_moi_nhanh.nguoi")
        for key, value in vals.items():
            if key in o:
                self.dien_o(f"them_moi_nhanh.nguoi.{key}", value, hop, o[key].get("kind", "text"))
        self.el("them_moi_nhanh.nut_luu_nguoi", hop).click()
        expect(hop).to_be_hidden()

    def luu(self) -> str:
        self.el("them_moi_nhanh.nut_luu", self.form()).click()
        msg = self.el("them_moi_nhanh.thong_bao_ok")
        expect(msg).to_be_visible()
        text = self.el("them_moi_nhanh.ma_ho_so_moi").inner_text()
        mau = self.L.data.get("them_moi_nhanh", {}).get("mau_ma_ho_so", "TODO")
        if mau == "TODO":
            raise ChuaCoLocator("them_moi_nhanh.mau_ma_ho_so chưa khai báo (regex mã hồ sơ)")
        m = re.search(mau, text)
        if not m:
            raise RuntimeError(f"Không đọc được mã hồ sơ mới từ: {text!r}")
        return m.group(0)

    def huy(self) -> None:
        self.el("them_moi_nhanh.nut_huy", self.form()).click()
        if self.L.co("them_moi_nhanh.xac_nhan_huy"):
            xac_nhan = self.el("them_moi_nhanh.xac_nhan_huy")
            if xac_nhan.count():
                xac_nhan.click()
