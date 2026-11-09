"""MPLIS giả lập trong bộ nhớ — cho test Runner mà không cần web."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..domain.models import HoSo
from .port import SoPhatHanhTrung, gia_tri_so_khop


class GiaLapNgat(RuntimeError):
    """Giả lập mất mạng/tắt máy ngay sau khi bấm Lưu."""


@dataclass
class FakeMplis:
    da_co: dict[str, dict[str, str]] = field(default_factory=dict)  # mã hồ sơ -> dữ liệu
    ngat_sau_luu: set[str] = field(default_factory=set)              # key hồ sơ sẽ "ngắt" sau Lưu (1 lần)
    lech_khi_doc: set[str] = field(default_factory=set)              # key hồ sơ sẽ đọc lại bị lệch
    so_lan_luu: int = 0
    tai_khoan_chuyen: str = "toi"                                    # tài khoản nhận ở bước chuyển
    loi_chon_gcn: set[str] = field(default_factory=set)              # key hồ sơ lỗi một lần khi chọn GCN
    loi_chuyen: set[str] = field(default_factory=set)                # key hồ sơ lỗi một lần khi chuyển xử lý
    loi_chuyen_quyen: set[str] = field(default_factory=set)          # key hồ sơ lỗi trong wizard
    so_phat_hanh_trung: set[str] = field(default_factory=set)        # key hồ sơ bị MPLIS báo trùng số phát hành
    hoi_so_moi: Callable[[str, str], str | None] | None = None
    so_moi_nhan: list[str] = field(default_factory=list)
    loi_hoan_tat: set[str] = field(default_factory=set)              # key hồ sơ lỗi khi Hoàn tất
    mo_lai: list[str] = field(default_factory=list)                  # các hồ sơ được mở lại khi chạy lại
    goi: list[str] = field(default_factory=list)                     # thứ tự các thao tác ghi
    _form: HoSo | None = None
    _dem: int = 0

    def cho_dang_nhap(self) -> None: ...

    def dia_chi_ho_so(self) -> str:
        return f"fake://HS-{self._dem:04d}"

    def mo_ho_so(self, duong_dan: str) -> None:
        self.mo_lai.append(duong_dan)

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
        self.goi.append("luu")
        ma = f"HS-{self._dem:04d}"
        data = dict(gia_tri_so_khop(hs), _key=hs.key)
        if hs.key in self.lech_khi_doc:
            data["dien_tich"] = "0"
        self.da_co[ma] = data
        if hs.key in self.ngat_sau_luu:
            self.ngat_sau_luu.discard(hs.key)
            raise GiaLapNgat("mất kết nối sau khi bấm Lưu")
        return ma

    def chon_gcn(self, hs: HoSo, ma_ho_so: str) -> None:
        self.goi.append("chon_gcn")
        if hs.key in self.loi_chon_gcn:
            self.loi_chon_gcn.discard(hs.key)
            raise RuntimeError("lỗi giả lập khi chọn GCN")

    def chuyen_xu_ly(self, hs: HoSo, ma_ho_so: str) -> str:
        self.goi.append("chuyen_xu_ly")
        if hs.key in self.loi_chuyen:
            self.loi_chuyen.discard(hs.key)
            raise RuntimeError("lỗi giả lập khi chuyển xử lý")
        return self.tai_khoan_chuyen

    def dien_chuyen_quyen(self, hs: HoSo, ma_ho_so: str) -> None:
        self.goi.append("dien_chuyen_quyen")
        if hs.key in self.so_phat_hanh_trung:
            moi = self.hoi_so_moi("tờ/thửa", "AA 1") if self.hoi_so_moi else None
            if not moi:
                raise SoPhatHanhTrung("AA 1")
            self.so_phat_hanh_trung.discard(hs.key)
            self.so_moi_nhan.append(moi)
        if hs.key in self.loi_chuyen_quyen:
            raise RuntimeError("lỗi giả lập trong wizard")

    def hoan_tat(self, hs: HoSo, ma_ho_so: str) -> None:
        self.goi.append("hoan_tat")
        if hs.key in self.loi_hoan_tat:
            raise RuntimeError("lỗi giả lập khi Hoàn tất")

    def doc(self, hs: HoSo, ma_ho_so: str) -> dict[str, str]:
        return {k: v for k, v in self.da_co[ma_ho_so].items() if not k.startswith("_")}

    def ve_trang_dau(self) -> None: ...
    def trace_start(self, key: str) -> None: ...
    def trace_stop(self, key: str, keep: bool) -> str | None:
        return f"fake/{key}.zip" if keep else None
