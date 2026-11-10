"""Lệnh ghi MPLIS gọi thẳng API (Đợt 1): Lưu hồ sơ tiếp nhận, gắn GCN, chuyển Thụ lý.

Cấu trúc lấy từ bản ghi harvest 08/11/2026 (các lệnh chính giao diện MPLIS gửi). Hàm ở đây chỉ dựng/đọc dữ liệu,
không gọi mạng; PlaywrightMplis gửi đi. Chỗ nào thiếu hoặc lạ thì báo lỗi TRƯỚC khi gửi lệnh ghi.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..domain.models import HoSo, Nguoi

API_NGAN_CHAN_THUA = "/dc/DangKyAjax/KiemTraNganChanThua"
API_LUU = "/dc/DangKyAjax/TiepNhanHoSo"
API_NGAY_HEN_TRA = "/dc/DangKyAjax/GetNgayHenTra"
API_QUY_TRINH = "/dc/DangKyAjax/GetQuyTrinh"
API_TIM_CA_NHAN = "/dc/ChuSoHuuAjax/AdvancedSearchCaNhan"
API_NGAN_CHAN_GCN = "/dc/DangKyAjax/KiemTraNganChanThanhPhanHoSoTruocBienDongByGCNIds"
API_THEM_GCN = "/dc/DangKyAjax/AddGiayChungNhanVaoThanhPhanHoSo"
API_DA_XU_LY = "/dc/DangKyAjax/UpdateTacVuDaXuLy"
API_CHUYEN = "/dc/WorkflowAjax/executeCommand"
DUONG_DAN_HO_SO = "/dc/TiepNhanHoSo/CapNhatHoSo?id="

_GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_MSDATE = re.compile(r"^/Date\((-?\d+)\)/$")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$")


def _chuan(s: str) -> str:
    return " ".join(str(s or "").split()).upper()


def _ds(v: Any) -> list:
    return v if isinstance(v, list) else []


def kiem_ngan_chan(kq: dict, buoc: str) -> None:
    """Giao diện MPLIS hiện hộp cảnh báo ở các trường hợp này và tool (chạy giao diện) đã dừng; API cũng dừng như vậy."""
    if kq.get("success") is False:
        raise RuntimeError(f"MPLIS báo lỗi ở bước {buoc}: {kq.get('message') or kq.get('status') or ''}")
    v = kq.get("value") if isinstance(kq.get("value"), dict) else {}
    if v.get("coNganChan"):
        raise RuntimeError(f"MPLIS báo ngăn chặn ở bước {buoc}: {v.get('noiDungNganChan') or ''}")
    if kq.get("coTheChap"):
        raise RuntimeError(f"MPLIS báo đang thế chấp ở bước {buoc}: {kq.get('theChapMessage') or ''}")
    if _ds(kq.get("listThuaDangThuLy")):
        raise RuntimeError(f"MPLIS báo thửa đang có hồ sơ thụ lý ở bước {buoc}")
    if kq.get("coGhiNoNghiaVuTaiChinh"):
        raise RuntimeError(f"MPLIS báo ghi nợ nghĩa vụ tài chính ở bước {buoc}: {kq.get('noiDungGhiNoNghiaVuTaiChinh') or ''}")


def _ma_thua(thua: dict) -> int:
    v = thua.get("thuaDatId")
    if not v:
        raise ValueError("Bản ghi thửa trên MPLIS không có mã thửa (thuaDatId)")
    return int(v)


def than_ngan_chan_thua(thua: dict, xa_id: int) -> dict:
    return {"kiemTraNganChanThuaInputs": [{"thuaDatId": _ma_thua(thua), "soTo": thua["soHieuToBanDo"], "soThua": thua["soThuTuThua"],
                                           "dienTich": thua.get("dienTich"), "xaId": xa_id, "diaChi": thua.get("diaChi") or ""}]}


def than_luu(hs: HoSo, *, xa_id: int, thua: dict, nguoi_nop: dict, quy_trinh: tuple[str, str], ngay_tiep_nhan: str,
             ngay_hen_tra: str) -> dict:
    """Thân lệnh TiepNhanHoSo giống hệt giao diện gửi khi chọn thửa từ bảng tra cứu và bấm "Một cửa"."""
    t = hs.dau.thua
    nguoi = {"hoTen": "", "giayChungMinh": "", "soDienThoai": "", "noidung": "", "email": "", "vaiTroNguoiNopDon": "0",
             "nhanThongTin": "email", "diachi": "", "caNhanId": "", "caNhanChuId": "", "hoTenChu": "", "giayChungMinhChu": "",
             "soDienThoaiChu": "", "emailChu": "", "diachiChu": "", **nguoi_nop}
    ma, ten = quy_trinh
    return {"hoSo": {
        "huyenId": "0", "xaId": str(xa_id), "quytrinh": "", "soBienNhan": "", "ngayTiepNhan": ngay_tiep_nhan, "ngayhenTra": ngay_hen_tra,
        "nguoiNopDon": nguoi, "phuongThucNhanHoSo": "1", "phuongThucTraKetQua": "0", "giayToDinhKem": [],
        "thuaDat": [{"soThua": t.so_thua, "soTo": t.so_to, "dienTich": thua.get("dienTich"), "diaChi": thua.get("diaChi") or "",
                     "thuaDatId": _ma_thua(thua), "xaId": xa_id}],
        "listQuyTrinh": [{"TenQuyTrinh": ten, "MaQuyTrinh": ma, "TrangThai": 0, "IsStartFirst": True}],
        "nhanThongTin": "email", "tinhId": "33", "dangKyHoSoTrucTuyenId": "", "diaChiTaiSan": t.dia_chi or "",
    }, "capNhatSoBienNhanMoi": False, "thoiGianTiepNhanTheoHeThong": True}


@dataclass
class KetQuaLuu:
    so_bien_nhan: str
    id: str             # GUID hồ sơ, dùng cho các lệnh sau và địa chỉ trang hồ sơ
    process_id: str     # GUID tiến trình, dùng khi chuyển phân công
    gcn: list[dict] = field(default_factory=list)  # GCN cũ của thửa (giao diện hiện thành popup "Chọn giấy chứng nhận")


def doc_ket_qua_luu(kq: dict) -> KetQuaLuu:
    if not kq.get("success"):
        raise RuntimeError(f"MPLIS không lưu được: {kq.get('message') or kq.get('status') or ''}")
    v = kq.get("value") or {}
    r = KetQuaLuu(str(v.get("soBienNhan") or ""), str(v.get("Id") or ""), str(v.get("processId") or ""), _ds(kq.get("listGiayChungNhan")))
    if not (r.so_bien_nhan and _GUID.match(r.id) and _GUID.match(r.process_id)):
        # có thể đã lưu trên máy chủ: Runner để DANG_TAO, lần sau tra trùng sẽ tìm lại, không tạo thêm
        raise RuntimeError("MPLIS trả kết quả Lưu thiếu số biên nhận hoặc mã hồ sơ")
    return r


def doc_ngay_hen_tra(kq: dict) -> str:
    """MPLIS trả "/Date(ms)/"; giao diện gửi lại dạng Date.toISOString() của JavaScript."""
    v = str(kq.get("value") or "")
    m = _MSDATE.match(v)
    if kq.get("success") and m:
        ms = int(m.group(1))
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"
    if kq.get("success") and _ISO.match(v):
        return v
    raise RuntimeError(f"Không đọc được ngày hẹn trả từ MPLIS: {v[:40]!r}")


def ten_quy_trinh(kq: dict, ma: str) -> str:
    ten = [x.get("SchemaName") for x in _ds(kq.get("value")) if x.get("SchemaCode") == ma]
    if not (kq.get("success") and len(ten) == 1 and ten[0]):
        raise RuntimeError(f"MPLIS không có quy trình {ma}")
    return str(ten[0])


def chon_ban_ghi_ca_nhan(ds: list[dict], n: Nguoi) -> dict | None:
    """Như giao diện (câu hỏi 18): không có bản ghi thì gõ tay; có thì phải đúng một bản ghi khớp họ tên và năm sinh."""
    if not ds:
        return None
    khop = [r for r in ds if _chuan(r.get("hoTen")) == _chuan(n.ho_ten) and str(r.get("namSinh") or "").endswith(str(n.nam_sinh))]
    if len(khop) != 1:
        raise RuntimeError(f"{len(ds)} cá nhân cùng số giấy tờ, không xác định được bản ghi khớp họ tên và năm sinh")
    return khop[0]


def chon_tai_khoan(ds: dict[str, str], ten: str) -> str:
    """Cán bộ XL trong Excel là tài khoản hoặc đuôi họ tên; phải khớp đúng một người nhận bước Thụ lý."""
    khop = [tk for tk, ho_ten in ds.items() if tk.strip() == ten.strip() or _chuan(ho_ten).endswith(_chuan(ten))]
    if len(khop) != 1:
        raise RuntimeError(f"Cán bộ XL '{ten}' khớp {len(khop)} tài khoản nhận bước Thụ lý")
    return khop[0]


def than_chuyen(quy_trinh: str, id_ho_so: str, process_id: str, tai_khoan: str) -> dict:
    return {"schemaCode": f"QD_1_012787_{quy_trinh}", "processId": process_id, "commandName": "Chuyển phân công",
            "hoSoTiepNhanId": id_ho_so, "userName": tai_khoan, "moveToState": None, "ghiChuChuyenViec": ""}
