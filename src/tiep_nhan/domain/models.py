"""Mô hình miền (pydantic v2). Lớp này KHÔNG import gì từ mplis/, app/ hay Playwright."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .chuan_hoa import chuan_ma_phat_hanh, to_decimal, to_int


class _Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True, coerce_numbers_to_str=True)


class Nguoi(_Base):
    vai_tro: Literal["Ông", "Bà"]
    ho_ten: str = Field(min_length=2)
    nam_sinh: int | None = Field(default=None, ge=1900, le=2026)
    cccd: str | None = Field(default=None, pattern=r"^\d{12}$")
    dia_chi: str | None = None

    @field_validator("nam_sinh", mode="before")
    @classmethod
    def _nam(cls, v):
        return to_int(v)


class ThuaDat(_Base):
    so_to: int = Field(gt=0)
    so_thua: int = Field(gt=0)
    dien_tich: float | None = Field(default=None, gt=0)
    ma_phat_hanh: str | None = None
    thoi_han: str | None = None
    dia_chi: str | None = None

    @field_validator("so_to", "so_thua", mode="before")
    @classmethod
    def _nguyen(cls, v):
        return to_int(v)

    @field_validator("dien_tich", mode="before")
    @classmethod
    def _so(cls, v):
        return to_decimal(v)

    @field_validator("ma_phat_hanh", mode="before")
    @classmethod
    def _mph(cls, v):
        return chuan_ma_phat_hanh(v)


class NhaO(_Base):
    loai_nha: str | None = None
    cap_nha: str | None = None
    dt_xay_dung: float | None = Field(default=None, gt=0)
    dt_san: float | None = Field(default=None, gt=0)
    so_tang: int | None = Field(default=None, ge=1, le=100)
    nam_hoan_cong: int | None = Field(default=None, ge=1900, le=2026)
    ket_cau: str | None = None

    @field_validator("dt_xay_dung", "dt_san", mode="before")
    @classmethod
    def _so(cls, v):
        return to_decimal(v)

    @field_validator("so_tang", "nam_hoan_cong", mode="before")
    @classmethod
    def _nguyen(cls, v):
        return to_int(v)


class DongPhieu(_Base):
    """Một dòng của phiếu chuyển, đã kiểm tra kiểu dữ liệu."""
    excel_row: int
    stt: int
    ma_dau_vao: str = Field(min_length=3)
    ben_chuyen: str | None = None
    xac_nhan: str | None = None
    nguoi: tuple[Nguoi, ...] = Field(min_length=1)   # BR-01
    thua: ThuaDat
    nha: NhaO
    mau_nha: str | None = None
    phan_loai_duong: str | None = None
    can_bo: str | None = None

    @field_validator("stt", mode="before")
    @classmethod
    def _stt(cls, v):
        return to_int(v)

    @property
    def khoa_dong(self) -> str:
        return f"{self.ma_dau_vao}|to{self.thua.so_to}|thua{self.thua.so_thua}"

    @property
    def ten_chu(self) -> str:
        return " & ".join(n.ho_ten for n in self.nguoi)


class HoSo(_Base):
    """Đơn vị công việc: một hồ sơ tiếp nhận trên MPLIS (một hoặc nhiều dòng phiếu)."""
    key: str
    dong: tuple[DongPhieu, ...] = Field(min_length=1)

    @property
    def excel_rows(self) -> list[int]:
        return [d.excel_row for d in self.dong]

    @property
    def dau(self) -> DongPhieu:
        return self.dong[0]

    @property
    def mo_ta(self) -> str:
        thua = ", ".join(f"{d.thua.so_to}/{d.thua.so_thua}" for d in self.dong)
        return f"STT {', '.join(str(d.stt) for d in self.dong)} · tờ/thửa {thua} · {self.dau.ten_chu}"


VanDeMuc = Literal["loi", "canh_bao"]


class VanDe(BaseModel):
    excel_row: int          # 0 = cả file
    muc: VanDeMuc
    ma: str                 # BR-xx hoặc FILE
    noi_dung: str
