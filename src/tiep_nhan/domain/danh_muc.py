"""Ánh xạ giá trị Excel → giá trị danh mục MPLIS (BR-05). Dữ liệu ở config/danh_muc.toml."""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

from .chuan_hoa import chuan_ten as _k, nhieu_xa, ten_xa
from .models import HoSo, VanDe

# trường miền -> (bảng trong TOML, hàm lấy giá trị từ một dòng)
TRUONG = {
    "loai_nha": lambda d: d.nha.loai_nha,
    "cap_nha": lambda d: d.nha.cap_nha,
    "ket_cau": lambda d: d.nha.ket_cau,
    "thoi_han": lambda d: d.thua.thoi_han,
    "xa": lambda d: ten_xa(d.thua.dia_chi),
}
BAT_BUOC = ("loai_nha", "cap_nha", "ket_cau", "thoi_han")  # trống thì wizard dừng giữa chừng, sau khi hồ sơ đã Lưu


class DanhMuc:
    def __init__(self, data: dict[str, dict[str, str]]):
        self._goc = {bang: dict(vals) for bang, vals in data.items()}
        self._map = {bang: {_k(k): v for k, v in vals.items()} for bang, vals in data.items()}

    @classmethod
    def doc(cls, path: Path) -> "DanhMuc":
        return cls(tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {})

    def anh_xa(self, bang: str, gia_tri: str | None) -> str | None:
        if gia_tri in (None, ""):
            return None
        v = self._map.get(bang, {}).get(_k(gia_tri))
        return None if v in (None, "", "TODO") else v

    def bang(self, ten: str) -> list[str]:
        """Các giá trị MPLIS đã biết của một bảng, để gợi ý trên màn Ánh xạ."""
        return sorted({v for v in self._goc.get(ten, {}).values() if v not in ("", "TODO")})

    def them(self, bang: str, gia_tri: str, muc_tieu: str) -> None:
        self._goc.setdefault(bang, {})[gia_tri] = muc_tieu
        self._map.setdefault(bang, {})[_k(gia_tri)] = muc_tieu

    def luu(self, path: Path) -> None:
        dong = [f"[{b}]\n" + "".join(f"{json.dumps(k, ensure_ascii=False)} = {json.dumps(v, ensure_ascii=False)}\n"
                                     for k, v in vals.items()) for b, vals in self._goc.items()]
        path.write_text("\n".join(dong), encoding="utf-8")

    def chua_anh_xa(self, ho_so: list[HoSo]) -> dict[tuple[str, str], list[int]]:
        """(bảng, giá trị Excel) -> các dòng Excel đang dùng giá trị chưa có đích."""
        thieu: dict[tuple[str, str], list[int]] = {}
        for hs in ho_so:
            for d in hs.dong:
                for bang, lay in TRUONG.items():
                    if bang == "xa" and bang not in self._map:  # bản toml cũ trong %APPDATA% chưa có danh sách xã
                        continue
                    gv = lay(d)
                    if gv and self.anh_xa(bang, gv) is None:
                        thieu.setdefault((bang, gv), []).append(d.excel_row)
        return thieu

    def kiem_tra(self, ho_so: list[HoSo]) -> list[VanDe]:
        out: list[VanDe] = []
        for hs in ho_so:
            for d in hs.dong:
                if nhieu_xa(d.thua.dia_chi):
                    out.append(VanDe(excel_row=d.excel_row, muc="canh_bao", ma="BR-05",
                                     noi_dung=f"Địa chỉ ghi nhiều xã, tool dùng xã đầu tiên: {ten_xa(d.thua.dia_chi)}"))
                out += [VanDe(excel_row=d.excel_row, muc="loi", ma="BR-05",
                              noi_dung=f"[{bang}] đang trống, wizard chuyển quyền bắt buộc phải có")
                        for bang in BAT_BUOC if not TRUONG[bang](d)]
        for (bang, gv), rows in self.chua_anh_xa(ho_so).items():
            out.append(VanDe(excel_row=rows[0], muc="loi", ma="BR-05",
                             noi_dung=f"[{bang}] '{gv}' chưa ánh xạ sang danh mục MPLIS (dòng {', '.join(map(str, rows))})"))
        return out
