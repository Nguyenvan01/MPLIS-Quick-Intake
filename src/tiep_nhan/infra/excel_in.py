"""Đọc file Excel "Phiếu chuyển thông tin địa chính" (mẫu Vinhomes) thành các dòng thô.

Không phụ thuộc vị trí cột cố định: tìm dòng tiêu đề có ô "STT", ghép với dòng
tiêu đề phía trên (nhóm Ông / Bà) rồi ánh xạ theo tên cột. Chèn/bớt cột không làm hỏng tool.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


def norm(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value)).lower()
    return re.sub(r"\s+", " ", text).strip()


def clean(value: Any) -> Any:
    """Bỏ xuống dòng / khoảng trắng thừa trong chuỗi; giữ nguyên số."""
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()
        return value or None
    return value


GROUPS = {"ông": "ong", "bà": "ba"}
PERSON_FIELDS = {"họ và tên": "ho_ten", "năm sinh": "nam_sinh", "cccd": "cccd", "địa chỉ": "dia_chi"}

COLUMN_MAP: dict[str, str] = {
    "stt": "stt",
    "f1": "ben_chuyen",
    "f2": "f2",
    "f3": "f3",
    "xác nhận vinhomes": "xac_nhan",
    "thửa đất": "so_thua",
    "số tờ": "so_to",
    "diện tích (m2)": "dien_tich",
    "mã phát hành": "ma_phat_hanh",
    "thời hạn sử dụng đất": "thoi_han",
    "đường": "dia_chi_thua",
    "loại nhà": "loai_nha",
    "cấp nhà": "cap_nha",
    "diện tích xây dựng (m2)": "dt_xay_dung",
    "diện tích sàn (m2)": "dt_san",
    "số tầng": "so_tang",
    "năm hoàn công": "nam_hoan_cong",
    "kết cấu": "ket_cau",
    "mẫu nhà": "mau_nha",
    "phân loại đường": "phan_loai_duong",
    "cán bộ xl": "can_bo",
    "người nộp": "nguoi_nop",
    "mã đầu vào": "ma_dau_vao",
    "số hợp đồng": "ma_dau_vao",  # mẫu theo đợt không có Mã đầu vào
}
REQUIRED = {"stt", "so_thua", "so_to", "ma_dau_vao", "ong_ho_ten", "ba_ho_ten"}


@dataclass
class RawRow:
    excel_row: int
    values: dict[str, Any]


@dataclass
class ReadResult:
    sheet: str
    header_row: int
    columns: dict[str, str]  # tên trường -> cột Excel (vd "AD")
    rows: list[RawRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)


class ExcelFormatError(Exception):
    pass


def _merged_lookup(ws) -> dict[tuple[int, int], tuple[int, int]]:
    out: dict[tuple[int, int], tuple[int, int]] = {}
    for rng in ws.merged_cells.ranges:
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                out[(r, c)] = (rng.min_row, rng.min_col)
    return out


def _find_header_row(ws, limit: int = 20) -> int:
    for row in ws.iter_rows(min_row=1, max_row=limit):
        for cell in row:
            if norm(cell.value) == "stt":
                return cell.row
    raise ExcelFormatError("Không tìm thấy dòng tiêu đề có ô 'STT' trong 20 dòng đầu.")


def read_phieu(path: str | Path, sheet: str | None = None) -> ReadResult:
    wb = load_workbook(path, data_only=True)  # data_only: lấy giá trị đã tính của công thức
    ws = wb[sheet] if sheet else wb.worksheets[0]
    merged = _merged_lookup(ws)
    h = _find_header_row(ws)

    def header_val(r: int, c: int) -> str:
        r0, c0 = merged.get((r, c), (r, c))
        return norm(ws.cell(r0, c0).value)

    columns: dict[str, int] = {}
    unmapped: list[str] = []
    for c in range(1, ws.max_column + 1):
        upper, lower = header_val(h - 1, c), header_val(h, c)
        label = lower or upper
        if not label:
            continue
        group = GROUPS.get(upper) if upper != label else None
        if not upper and label in PERSON_FIELDS:  # mẫu không ghi Ông/Bà: chồng/vợ xác định sau theo CCCD (BR-09)
            group = "ba" if f"ong_{PERSON_FIELDS[label]}" in columns else "ong"
        if group and label in PERSON_FIELDS:
            key = f"{group}_{PERSON_FIELDS[label]}"
        else:
            key = COLUMN_MAP.get(label)
        if key is None:
            unmapped.append(f"{get_column_letter(c)}: {label}")
        elif key not in columns:
            columns[key] = c

    missing = REQUIRED - columns.keys()
    if missing:
        raise ExcelFormatError(f"Thiếu cột bắt buộc: {', '.join(sorted(missing))}")

    result = ReadResult(
        sheet=ws.title,
        header_row=h,
        columns={k: get_column_letter(c) for k, c in columns.items()},
        unmapped=unmapped,
    )

    # Ô gộp ở tiêu đề kéo xuống vùng dữ liệu => giá trị của dòng đó bị Excel che mất.
    spill = sorted(
        (rng for rng in ws.merged_cells.ranges if rng.min_row <= h < rng.max_row),
        key=lambda rng: rng.min_col,
    )
    if spill:
        last = max(rng.max_row for rng in spill)
        rows_txt = f"{h + 1}" if last == h + 1 else f"{h + 1}–{last}"
        result.warnings.append(
            f"Ô tiêu đề gộp {', '.join(rng.coord for rng in spill)} lấn xuống dòng dữ liệu {rows_txt}: "
            "giá trị các cột này ở dòng đó bị mất. Hãy bỏ gộp ô và điền lại."
        )

    for r in range(h + 1, ws.max_row + 1):
        values = {k: clean(ws.cell(r, c).value) for k, c in columns.items()}
        if all(v is None for v in values.values()):
            continue
        if values.get("stt") is None and values.get("so_thua") is None and values.get("so_to") is None:
            filled = ", ".join(f"{k}={v}" for k, v in values.items() if v is not None)
            result.warnings.append(f"Dòng {r} không có STT/tờ/thửa nên bị bỏ qua (đang có: {filled}).")
            continue
        result.rows.append(RawRow(excel_row=r, values=values))

    return result


def ten_sheet(path: str | Path) -> list[str]:
    return load_workbook(path, read_only=True).sheetnames
