"""Hợp đồng giữa Lõi và MPLIS. Runner chỉ gọi các hàm này.

Có 2 bản cài:
  - ui_adapter.PlaywrightMplis : điền giao diện thật bằng Playwright + Chromium
  - fake.FakeMplis             : giả lập trong bộ nhớ, dùng cho test
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from ..domain.chuan_hoa import to_decimal
from ..domain.models import HoSo


class SoPhatHanhTrung(Exception):
    """MPLIS báo số phát hành đã được cấp cho giấy chứng nhận khác. str(e) là số đó."""


class MplisPort(Protocol):
    hoi_so_moi: Callable[[str, str], str | None] | None  # (mô tả thửa, số bị trùng) -> số mới, None nếu không nhập

    def cho_dang_nhap(self) -> None: ...                       # người dùng tự đăng nhập (captcha, Authenticator)
    def tim_trung(self, hs: HoSo) -> str | None: ...          # mã hồ sơ nếu MPLIS đã có (BR-04)
    def so_da_cap(self, ds: list[str]) -> set[str]: ...        # các số phát hành MPLIS báo đã cấp (chỉ đọc)
    def ds_nguoi_xu_ly(self) -> dict[str, str]: ...            # tài khoản -> họ tên người nhận bước Thụ lý (chỉ đọc)
    def kiem_thua(self, hs: HoSo) -> str | None: ...           # thửa không có hoặc lệch diện tích trên MPLIS; None là khớp (chỉ đọc)
    def mo_form(self) -> None: ...                             # mở form tiếp nhận trống
    def dien(self, hs: HoSo) -> None: ...                      # điền, KHÔNG lưu
    def chup(self, key: str) -> str: ...                       # ảnh chụp form, trả đường dẫn
    def huy(self) -> None: ...                                 # đóng form không lưu
    def luu(self) -> str: ...                                  # bấm Lưu, trả mã hồ sơ mới
    def dia_chi_ho_so(self) -> str: ...                        # địa chỉ trang hồ sơ vừa lưu
    def mo_ho_so(self, duong_dan: str) -> None: ...            # đặt lại hồ sơ đang làm khi chạy lại
    def chon_gcn(self, hs: HoSo, ma_ho_so: str) -> None: ...   # chọn GCN cũ trong popup sau khi lưu
    def chuyen_xu_ly(self, hs: HoSo, ma_ho_so: str) -> str: ...  # trả tài khoản đã nhận; đánh dấu đã xử lý, chuyển Cán bộ XL
    def dien_chuyen_quyen(self, hs: HoSo, ma_ho_so: str) -> None: ...  # wizard đến Bước 4, chưa Hoàn tất
    def hoan_tat(self, hs: HoSo, ma_ho_so: str) -> None: ...
    def mo_du_thao(self, hs: HoSo, ma_ho_so: str) -> None: ...  # mở màn "Dự thảo giấy chứng nhận"
    def luu_du_thao(self, hs: HoSo, ma_ho_so: str) -> None: ...  # trên màn dự thảo đang mở: Tạo QR mới rồi Lưu dự thảo
    def doc(self, hs: HoSo, ma_ho_so: str) -> dict[str, str]: ...        # đọc lại hồ sơ để so khớp
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
            "cccd_nop": d.nguoi_nop.cccd or "",
        }
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
