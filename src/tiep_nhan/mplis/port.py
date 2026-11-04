"""Hợp đồng giữa Lõi và MPLIS. Runner chỉ gọi các hàm này.

Có 2 bản cài:
  - ui_adapter.PlaywrightMplis : điền giao diện thật bằng Playwright + Edge
  - fake.FakeMplis             : giả lập trong bộ nhớ, dùng cho test
"""
from __future__ import annotations

from typing import Protocol

from ..domain.chuan_hoa import to_decimal
from ..domain.models import HoSo


class MplisPort(Protocol):
    def dang_nhap(self, username: str, password: str) -> None: ...
    def tim_trung(self, hs: HoSo) -> str | None: ...          # mã hồ sơ nếu MPLIS đã có (BR-04)
    def mo_form(self) -> None: ...                             # mở form Thêm mới nhanh trống
    def dien(self, hs: HoSo) -> None: ...                      # điền, KHÔNG lưu
    def chup(self, key: str) -> str: ...                       # ảnh chụp form, trả đường dẫn
    def huy(self) -> None: ...                                 # đóng form không lưu
    def luu(self) -> str: ...                                  # bấm Lưu, trả mã hồ sơ mới
    def doc(self, ma_ho_so: str) -> dict[str, str]: ...        # đọc lại hồ sơ để so khớp
    def ve_trang_dau(self) -> None: ...
    def trace_start(self, key: str) -> None: ...
    def trace_stop(self, key: str, keep: bool) -> str | None: ...


def so(v: float | int | None) -> str:
    """Số kiểu VN: 45.6 -> '45,6', 217.0 -> '217'."""
    return "" if v is None else f"{v:g}".replace(".", ",")


def gia_tri_so_khop(hs: HoSo) -> dict[str, str]:
    """Các giá trị PHẢI thấy được khi tra cứu lại hồ sơ (BR-07). Khóa có tiền tố [i] khi gộp nhiều dòng."""
    out: dict[str, str] = {}
    for i, d in enumerate(hs.dong, 1):
        p = "" if len(hs.dong) == 1 else f"[{i}]"
        vals = {
            "so_to": str(d.thua.so_to), "so_thua": str(d.thua.so_thua), "dien_tich": so(d.thua.dien_tich),
            "ma_phat_hanh": d.thua.ma_phat_hanh or "",
        }
        for n in d.nguoi:
            vals[f"cccd_{'ong' if n.vai_tro == 'Ông' else 'ba'}"] = n.cccd or ""
        out.update({p + k: v for k, v in vals.items() if v})
    return out


def _chuan(s: str) -> str:
    s = " ".join(str(s).split()).lower()
    try:
        n = to_decimal(s)
        digits = s.replace(",", "").replace(".", "").replace(" ", "")
        if n is not None and digits.isdigit() and len(digits) <= 9:  # không áp cho CCCD (giữ số 0 đầu)
            return f"{n:g}"
    except ValueError:
        pass
    return s


def so_sanh(hs: HoSo, web: dict[str, str]) -> dict[str, tuple[str, str]]:
    """{trường: (trên web, trong Excel)}. Trường web không trả về cũng tính là lệch (an toàn hơn bỏ qua)."""
    return {
        k: (web.get(k, ""), v)
        for k, v in gia_tri_so_khop(hs).items()
        if _chuan(web.get(k, "")) != _chuan(v)
    }
