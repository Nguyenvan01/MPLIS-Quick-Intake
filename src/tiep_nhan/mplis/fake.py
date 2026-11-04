"""MPLIS giả lập trong bộ nhớ — cho test Runner mà không cần web."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import HoSo
from .port import gia_tri_so_khop


class GiaLapNgat(RuntimeError):
    """Giả lập mất mạng/tắt máy ngay sau khi bấm Lưu."""


@dataclass
class FakeMplis:
    da_co: dict[str, dict[str, str]] = field(default_factory=dict)  # mã hồ sơ -> dữ liệu
    ngat_sau_luu: set[str] = field(default_factory=set)              # key hồ sơ sẽ "ngắt" sau Lưu (1 lần)
    lech_khi_doc: set[str] = field(default_factory=set)              # key hồ sơ sẽ đọc lại bị lệch
    so_lan_luu: int = 0
    _form: HoSo | None = None
    _dem: int = 0

    def dang_nhap(self, username: str, password: str) -> None: ...

    def tim_trung(self, hs: HoSo) -> str | None:
        can = gia_tri_so_khop(hs)
        for ma, data in self.da_co.items():
            if all(data.get(k) == can.get(k) for k in ("so_to", "so_thua")) and data.get("_key") == hs.key:
                return ma
        return None

    def mo_form(self) -> None:
        self._form = None

    def dien(self, hs: HoSo) -> None:
        self._form = hs

    def chup(self, key: str) -> str:
        return f"fake/{key}.png"

    def huy(self) -> None:
        self._form = None

    def luu(self) -> str:
        assert self._form is not None, "chưa điền form"
        hs, self._form = self._form, None
        self._dem += 1
        self.so_lan_luu += 1
        ma = f"HS-{self._dem:04d}"
        data = dict(gia_tri_so_khop(hs), _key=hs.key)
        if hs.key in self.lech_khi_doc:
            data["dien_tich"] = "0"
        self.da_co[ma] = data
        if hs.key in self.ngat_sau_luu:
            self.ngat_sau_luu.discard(hs.key)
            raise GiaLapNgat("mất kết nối sau khi bấm Lưu")
        return ma

    def doc(self, ma_ho_so: str) -> dict[str, str]:
        return {k: v for k, v in self.da_co[ma_ho_so].items() if not k.startswith("_")}

    def ve_trang_dau(self) -> None: ...
    def trace_start(self, key: str) -> None: ...
    def trace_stop(self, key: str, keep: bool) -> str | None:
        return f"fake/{key}.zip" if keep else None
