"""Gom dòng phiếu thành hồ sơ. Chế độ do Cài đặt quyết định (câu hỏi mở trong plan.md)."""
from __future__ import annotations

from collections import OrderedDict
from enum import StrEnum

from .models import DongPhieu, HoSo


class CheDoGom(StrEnum):
    MOI_DONG = "moi_dong"          # mỗi dòng có STT = một hồ sơ (mặc định)
    THEO_MA_DAU_VAO = "ma_dau_vao"  # các dòng cùng Mã đầu vào = một hồ sơ


def gom(dong: list[DongPhieu], che_do: CheDoGom = CheDoGom.MOI_DONG) -> list[HoSo]:
    if che_do is CheDoGom.MOI_DONG:
        return [HoSo(key=d.khoa_dong, dong=(d,)) for d in dong]
    groups: OrderedDict[str, list[DongPhieu]] = OrderedDict()
    for d in dong:
        groups.setdefault(d.ma_dau_vao, []).append(d)
    return [HoSo(key=f"{ma}|gop", dong=tuple(ds)) for ma, ds in groups.items()]
