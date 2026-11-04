"""Một lô = một lần nạp file. Ghép đọc Excel → kiểm tra → gom → danh mục. Không đụng tới web."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..domain.danh_muc import DanhMuc
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


def nap_lo(file: Path, danh_muc: DanhMuc, che_do: CheDoGom = CheDoGom.MOI_DONG) -> Lo:
    lo = Lo(file=file)
    try:
        lo.doc = read_phieu(file)
    except (ExcelFormatError, OSError) as e:
        lo.van_de.append(VanDe(excel_row=0, muc="loi", ma="FILE", noi_dung=str(e)))
        return lo
    dong, lo.van_de = kiem_tra_file(lo.doc)
    lo.ho_so = gom(dong, che_do)
    lo.van_de += danh_muc.kiem_tra(lo.ho_so)
    return lo
