"""Ánh xạ giá trị Excel → giá trị danh mục MPLIS (BR-05). Dữ liệu ở config/danh_muc.toml."""
from __future__ import annotations

import tomllib
import unicodedata
from pathlib import Path

from .models import HoSo, VanDe

# trường miền -> (bảng trong TOML, hàm lấy giá trị từ một dòng)
TRUONG = {
    "loai_nha": lambda d: d.nha.loai_nha,
    "cap_nha": lambda d: d.nha.cap_nha,
    "ket_cau": lambda d: d.nha.ket_cau,
    "thoi_han": lambda d: d.thua.thoi_han,
}


def _k(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).lower().split())


class DanhMuc:
    def __init__(self, data: dict[str, dict[str, str]]):
        self._map = {bang: {_k(k): v for k, v in vals.items()} for bang, vals in data.items()}

    @classmethod
    def doc(cls, path: Path) -> "DanhMuc":
        return cls(tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {})

    def anh_xa(self, bang: str, gia_tri: str | None) -> str | None:
        if gia_tri in (None, ""):
            return None
        v = self._map.get(bang, {}).get(_k(gia_tri))
        return None if v in (None, "", "TODO") else v

    def kiem_tra(self, ho_so: list[HoSo]) -> list[VanDe]:
        out: list[VanDe] = []
        thieu: dict[tuple[str, str], list[int]] = {}
        for hs in ho_so:
            for d in hs.dong:
                for bang, lay in TRUONG.items():
                    gv = lay(d)
                    if gv and self.anh_xa(bang, gv) is None:
                        thieu.setdefault((bang, gv), []).append(d.excel_row)
        for (bang, gv), rows in thieu.items():
            out.append(VanDe(excel_row=rows[0], muc="loi", ma="BR-05",
                             noi_dung=f"[{bang}] '{gv}' chưa ánh xạ sang danh mục MPLIS (dòng {', '.join(map(str, rows))})"))
        return out
