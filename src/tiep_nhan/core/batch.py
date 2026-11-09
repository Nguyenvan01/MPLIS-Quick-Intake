"""Một lô = một lần nạp file. Ghép đọc Excel → kiểm tra → gom → danh mục. Không đụng tới web."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..domain.danh_muc import DanhMuc
from ..infra.excel_out import KetQuaDong, ghi_ket_qua
from ..domain.gom_ho_so import CheDoGom, gom
from ..domain.models import HoSo, VanDe
from ..domain.rules import kiem_tra_file
from ..infra.excel_in import ExcelFormatError, ReadResult, read_phieu


@dataclass
class Lo:
    file: Path
    doc: ReadResult | None = None
    ho_so: list[HoSo] = field(default_factory=list)
    van_de: list[VanDe] = field(default_factory=list)

    @property
    def co_loi(self) -> bool:
        return any(v.muc == "loi" for v in self.van_de)


def nap_lo(file: Path, danh_muc: DanhMuc, che_do: CheDoGom = CheDoGom.MOI_DONG,
           mac_dinh: dict[str, str] | None = None, sheet: str | None = None) -> Lo:
    """mac_dinh: giá trị cho cả lô, chỉ dùng khi ô Excel trống (vd can_bo, thoi_han)."""
    lo = Lo(file=file)
    try:
        lo.doc = read_phieu(file, sheet)
    except (ExcelFormatError, OSError) as e:
        lo.van_de.append(VanDe(excel_row=0, muc="loi", ma="FILE", noi_dung=str(e)))
        return lo
    for raw in lo.doc.rows:
        raw.values.update({k: v for k, v in (mac_dinh or {}).items() if v and not raw.values.get(k)})
    dong, lo.van_de = kiem_tra_file(lo.doc)
    lo.ho_so = gom(dong, che_do)
    lo.van_de += danh_muc.kiem_tra(lo.ho_so)
    return lo


def xuat_ket_qua(lo: Lo, ket_qua: dict[str, tuple[str, str, str]], dich: Path | None = None) -> Path:
    """Ghi `<file>_ket_qua.xlsx` từ kết quả cuối của từng hồ sơ: key -> (trạng thái, ghi chú, mã hồ sơ)."""
    dong = [KetQuaDong(d.excel_row, ket_qua[hs.key][2], ket_qua[hs.key][0], ket_qua[hs.key][1])
            for hs in lo.ho_so if hs.key in ket_qua for d in hs.dong]
    return ghi_ket_qua(lo.file, lo.doc.header_row, dong, sheet=lo.doc.sheet, dich=dich)
