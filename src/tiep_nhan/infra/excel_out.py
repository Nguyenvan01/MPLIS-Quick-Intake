"""Ghi file kết quả: bản sao file gốc + 3 cột Mã hồ sơ MPLIS / Trạng thái / Ghi chú."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font


@dataclass
class KetQuaDong:
    excel_row: int
    ma_ho_so: str
    trang_thai: str
    ghi_chu: str


def ghi_ket_qua(goc: Path, header_row: int, ket_qua: list[KetQuaDong], sheet: str | None = None,
                dich: Path | None = None) -> Path:
    dich = dich or goc.with_name(f"{goc.stem}_ket_qua.xlsx")
    wb = load_workbook(goc)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    c0 = ws.max_column + 1
    for i, title in enumerate(("Mã hồ sơ MPLIS", "Trạng thái", "Ghi chú")):
        cell = ws.cell(header_row, c0 + i, title)
        cell.font = Font(bold=True)
    for kq in ket_qua:
        ws.cell(kq.excel_row, c0, kq.ma_ho_so)
        ws.cell(kq.excel_row, c0 + 1, kq.trang_thai)
        ws.cell(kq.excel_row, c0 + 2, kq.ghi_chu)
    wb.save(dich)
    return dich
