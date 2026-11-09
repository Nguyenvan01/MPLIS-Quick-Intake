"""Hàm chuẩn hóa giá trị ô Excel. Thuần Python để test được độc lập."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def to_decimal(value: Any) -> float | None:
    """'45,6' -> 45.6 ; '1.234,5' -> 1234.5 ; 217 -> 217.0 ; '84' -> 84.0"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("không phải số")
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"\d[\d.,]*", str(value))
    if not m:
        raise ValueError(f"không đọc được số từ '{value}'")
    s = m.group().rstrip(".,")
    if "," in s and "." in s:      # kiểu VN: dấu chấm phân nghìn, dấu phẩy thập phân
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def to_int(value: Any) -> int | None:
    """'5 tầng' -> 5 ; 2024 -> 2024 ; 3.0 -> 3"""
    if value is None or value == "":
        return None
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"'{value}' không phải số nguyên")
        return int(value)
    if isinstance(value, int):
        return value
    m = re.search(r"\d+", str(value))
    if not m:
        raise ValueError(f"không đọc được số nguyên từ '{value}'")
    return int(m.group())


def to_cccd(value: Any) -> tuple[str | None, list[str]]:
    """Trả về (số CCCD 12 chữ số, cảnh báo). Ô kiểu số làm mất số 0 đầu -> tự bù và cảnh báo."""
    notes: list[str] = []
    if value is None or value == "":
        return None, notes
    if isinstance(value, (int, float)):
        value = str(int(value)).zfill(12)
        notes.append("CCCD đang lưu dạng số trong Excel (dễ mất số 0 đầu) — đã tự bù cho đủ 12 số")
    s = re.sub(r"^cc:", "", re.sub(r"[\s.\-]", "", str(value)), flags=re.IGNORECASE)  # vài file ghi "CC: 0123…"
    if not re.fullmatch(r"\d{12}", s):
        raise ValueError(f"CCCD '{value}' không đủ 12 chữ số")
    return s, notes


def gioi_tinh_cccd(cccd: str) -> str:
    """Chữ số thứ 4 của CCCD: chẵn là Nam, lẻ là Nữ, ở mọi thế kỷ."""
    return "Nam" if int(cccd[3]) % 2 == 0 else "Nữ"


def cccd_khop(cccd: str, nam_sinh: int | None, vai_tro: str) -> list[str]:
    """Đối chiếu chữ số thứ 4 (giới tính + thế kỷ) và số 5–6 (năm sinh) của CCCD."""
    notes: list[str] = []
    code, yy = int(cccd[3]), int(cccd[4:6])
    gioi = gioi_tinh_cccd(cccd)
    nam = 1900 + 100 * (code // 2) + yy
    if vai_tro == "Ông" and gioi != "Nam":
        notes.append(f"CCCD {cccd[:4]}… là của Nữ nhưng nằm ở cột Ông")
    if vai_tro == "Bà" and gioi != "Nữ":
        notes.append(f"CCCD {cccd[:4]}… là của Nam nhưng nằm ở cột Bà")
    if nam_sinh and nam_sinh != nam:
        notes.append(f"Năm sinh {nam_sinh} khác năm trong CCCD ({nam})")
    return notes


def ten_xa(dia_chi: str | None) -> str | None:
    """'AD18-19, Khu đô thị Đại An, Xã Nghĩa Trụ' -> 'Nghĩa Trụ'. Ghi nhiều xã nối bằng '+' thì lấy xã đầu. Không có thì None."""
    m = re.search(r"(?:^|,)\s*(?:xã|phường|thị trấn)\s+([^,+]+)", dia_chi or "", re.IGNORECASE)
    return m.group(1).strip() if m else None


def chuan_ten(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).lower().split())


def nhieu_xa(dia_chi: str | None) -> bool:
    return bool(re.search(r"\+\s*(?:xã|phường|thị trấn)\s", dia_chi or "", re.IGNORECASE))


def chuan_ma_phat_hanh(value: Any) -> str | None:
    """'AA 11488897' -> 'AA 11488897' (chuẩn khoảng trắng, viết hoa)."""
    if value is None or value == "":
        return None
    s = re.sub(r"\s+", " ", str(value)).strip().upper()
    m = re.fullmatch(r"([A-Z]{2})\s?(\d+)", s)
    return f"{m.group(1)} {m.group(2)}" if m else s
