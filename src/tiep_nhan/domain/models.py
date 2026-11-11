"""Mô hình miền (pydantic v2). Lớp này KHÔNG import gì từ mplis/, app/ hay Playwright."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .chuan_hoa import chuan_ma_phat_hanh, chuan_ten, gioi_tinh_cccd, to_decimal, to_int


class _Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True, coerce_numbers_to_str=True)


class Nguoi(_Base):
    vai_tro: Literal["Ông", "Bà"]
    ho_ten: str = Field(min_length=2)
    nam_sinh: int | None = Field(default=None, ge=1900)
    cccd: str | None = Field(default=None, pattern=r"^\d{12}$")
    loai_giay_to: Literal["CCCD", "Căn cước"] = "CCCD"  # Excel ghi "CC:0123…" là thẻ Căn cước (cấp từ 01/07/2024)
    dia_chi: str | None = None

    @field_validator("nam_sinh", mode="before")
    @classmethod
    def _nam(cls, v):
        return to_int(v)

    @property
    def gioi_tinh(self) -> str:
        """Theo CCCD; không có CCCD mới dùng cột Ông/Bà."""
        if self.cccd:
            return gioi_tinh_cccd(self.cccd)
        return "Nam" if self.vai_tro == "Ông" else "Nữ"


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
        if isinstance(v, str) and len(re.findall(r"\d+", v)) > 1:  # vd "3938 + 2162": đọc số đầu sẽ bỏ sót thửa
            raise ValueError(f"'{v}' ghi nhiều thửa trong một dòng, tool chưa hỗ trợ: tách mỗi thửa một dòng hoặc làm tay")
        return to_int(v)

    @field_validator("dien_tich", mode="before")
    @classmethod
    def _so(cls, v):
        return to_decimal(v)

    @field_validator("ma_phat_hanh", mode="before")
    @classmethod
    def _mph(cls, v):
        return chuan_ma_phat_hanh(v)

    @field_validator("dia_chi", mode="before")
    @classmethod
    def _dia_chi(cls, v):
        """Cột Đường hay có đoạn trống (", ,") và khoảng trắng thừa: bỏ đi để GCN in gọn."""
        if v is None:
            return None
        s = ", ".join(p for p in (" ".join(x.split()) for x in str(v).split(",")) if p)
        if re.match(r"(?i)(xã|phường|thị trấn|thị xã|huyện)\s", s.rsplit(", ", 1)[-1]):
            s += ", tỉnh Hưng Yên"  # dừng ở cấp xã/huyện là thiếu tỉnh; tool chỉ chạy MPLIS Hưng Yên (tinhId 33)
        return s or None

    @property
    def dia_chi_thua_dat(self) -> str:
        """Địa chỉ thửa trên GCN chỉ gồm xã/phường trở đi; trùng địa chỉ tài sản thì MPLIS không in địa chỉ tài sản."""
        m = re.search(r"(?i)\b(xã|phường|thị trấn)\b.*$", self.dia_chi or "")
        return m.group(0) if m else (self.dia_chi or "")


class NhaO(_Base):
    loai_nha: str | None = None
    cap_nha: str | None = None
    dt_xay_dung: float | None = Field(default=None, gt=0)
    dt_san: float | None = Field(default=None, gt=0)
    so_tang: int | None = Field(default=None, ge=1, le=100)
    nam_hoan_cong: int | None = Field(default=None, ge=1900)  # Excel có thể ghi năm dự kiến
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
    nguoi_nop_excel: str | None = None  # họ tên trong cột Người nộp, là một trong các người nhận (BR-09)

    @field_validator("stt", mode="before")
    @classmethod
    def _stt(cls, v):
        return to_int(v)

    @property
    def khoa_dong(self) -> str:
        return f"{self.ma_dau_vao}|to{self.thua.so_to}|thua{self.thua.so_thua}"

    @property
    def la_vo_chong(self) -> bool:
        return len(self.nguoi) == 2

    @property
    def chong_vo(self) -> tuple[Nguoi, Nguoi]:
        """(chồng, vợ) theo giới tính, không theo cột. BR-09 đã bảo đảm có một Nam, một Nữ."""
        a, b = self.nguoi
        return (a, b) if a.gioi_tinh == "Nam" else (b, a)

    @property
    def so_nha(self) -> str:
        """Số nhà ở đầu địa chỉ (TĐ18-107, ...); địa chỉ không có số thì lấy mã căn từ Số hợp đồng."""
        dau = (self.thua.dia_chi or "").split(",")[0].strip()
        return dau if re.search(r"\d", dau) else self.ma_dau_vao.split("/")[0]

    @property
    def nguoi_nop(self) -> Nguoi:
        if self.nguoi_nop_excel:
            return next(n for n in self.nguoi if chuan_ten(n.ho_ten) == chuan_ten(self.nguoi_nop_excel))
        return self.chong_vo[0] if self.la_vo_chong else self.nguoi[0]

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
