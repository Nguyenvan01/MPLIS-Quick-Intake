"""Tra cứu hồ sơ: tìm trùng (BR-04) và đọc lại để so khớp (BR-07).

TODO(locators): luồng dưới đây là phỏng đoán theo kiến trúc; sửa cho khớp màn hình thật.
"""
from __future__ import annotations

from playwright.sync_api import expect

from ...domain.models import HoSo
from .base import BasePage


class TraCuuPage(BasePage):
    def mo(self) -> None:
        self.el("tra_cuu.mo_man_hinh").click()
        expect(self.el("tra_cuu.nut_tim")).to_be_visible()

    def tim(self, hs: HoSo) -> str | None:
        """Trả mã hồ sơ đầu tiên khớp tờ + thửa + CCCD người nhận, không có thì None."""
        self.mo()
        d = hs.dau
        self.el("tra_cuu.o_so_to").fill(str(d.thua.so_to))
        self.el("tra_cuu.o_so_thua").fill(str(d.thua.so_thua))
        cccd = next((n.cccd for n in d.nguoi if n.cccd), None)
        if cccd and self.L.co("tra_cuu.o_cccd"):
            self.el("tra_cuu.o_cccd").fill(cccd)
        self.el("tra_cuu.nut_tim").click()
        self.page.wait_for_load_state("networkidle")
        rows = self.el("tra_cuu.dong_ket_qua")
        if rows.count() == 0:
            return None
        return self.el("tra_cuu.o_ma_ho_so", rows.first).inner_text().strip()

    def doc(self, ma_ho_so: str) -> dict[str, str]:
        """Mở chi tiết hồ sơ và đọc các ô trong [tra_cuu.chi_tiet] của locators.toml."""
        self.mo()
        self.el("tra_cuu.o_ma_ho_so_tim").fill(ma_ho_so)
        self.el("tra_cuu.nut_tim").click()
        self.el("tra_cuu.dong_ket_qua").first.click()
        out: dict[str, str] = {}
        for key, spec in self.L.section("tra_cuu.chi_tiet").items():
            loc = self.el(f"tra_cuu.chi_tiet.{key}")
            out[key] = (loc.input_value() if spec.get("read") == "value" else loc.inner_text()).strip()
        return out
