"""Dữ liệu miền → giá trị điền vào từng ô trên form Thêm mới nhanh.

Khóa ở đây PHẢI trùng tên khóa trong [them_moi_nhanh.truong] của locators.toml.
"""
from __future__ import annotations

from ..domain.danh_muc import DanhMuc
from ..domain.models import DongPhieu, Nguoi
from .port import so


def gia_tri_thua_nha(d: DongPhieu, dm: DanhMuc) -> dict[str, str]:
    t, n = d.thua, d.nha
    vals = {
        "so_to": str(t.so_to),
        "so_thua": str(t.so_thua),
        "dien_tich": so(t.dien_tich),
        "ma_phat_hanh": t.ma_phat_hanh or "",
        "thoi_han": dm.anh_xa("thoi_han", t.thoi_han) or "",
        "dia_chi_thua": t.dia_chi or "",
        "loai_nha": dm.anh_xa("loai_nha", n.loai_nha) or "",
        "cap_nha": dm.anh_xa("cap_nha", n.cap_nha) or "",
        "dt_xay_dung": so(n.dt_xay_dung),
        "dt_san": so(n.dt_san),
        "so_tang": so(n.so_tang),
        "nam_hoan_cong": so(n.nam_hoan_cong),
        "ket_cau": dm.anh_xa("ket_cau", n.ket_cau) or "",
        "ma_dau_vao": d.ma_dau_vao,
    }
    return {k: v for k, v in vals.items() if v}


def gia_tri_nguoi(n: Nguoi) -> dict[str, str]:
    vals = {
        "gioi_tinh": "Nam" if n.vai_tro == "Ông" else "Nữ",   # TODO: xác nhận chữ trên MPLIS
        "ho_ten": n.ho_ten,
        "nam_sinh": str(n.nam_sinh or ""),
        "cccd": n.cccd or "",
        "dia_chi": n.dia_chi or "",
    }
    return {k: v for k, v in vals.items() if v}
