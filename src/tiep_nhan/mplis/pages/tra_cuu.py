"""Tra cứu hồ sơ tiếp nhận: tìm trùng (BR-04) và đọc lại để so khớp (BR-07)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

from ...domain.chuan_hoa import ten_xa
from ...domain.models import HoSo
from ..port import so
from .tiep_nhan import TiepNhanPage, khop_dien_tich

# Lệnh chỉ đọc mà chính trang tra cứu và hộp tìm thửa của MPLIS gọi (lấy từ trace). Phân trang kiểu DataTables.
API_TRA_HO_SO = "/dc/DangKyAjax/AdvancedSearchHoSoTiepNhan"
API_TIM_THUA = "/dc/TaiSanAjax/AdvancedSearchThuaDat"
TINH_ID = 33  # Hưng Yên


def tham_so_tra_ho_so(xa_id: int, so_thua: str = "", so_to: str = "", so_bien_nhan: str = "", start: int = 0,
                      length: int = 100) -> list[tuple[str, str]]:
    m = [("tinhId", TINH_ID), ("huyenId", ""), ("xaId", xa_id), ("quytrinh", ""), ("state", ""), ("soBienNhan", so_bien_nhan),
         ("laHoSoMotCua", "false"), ("tiepNhanTuNgay", ""), ("tiepNhanDenNgay", ""), ("henTraTuNgay", ""), ("henTraDenNgay", ""),
         ("trangThaiHoSo", 0), ("trangThaiKetISO][", 0), ("diaChiTaiSan", ""), ("soThua", so_thua), ("soTo", so_to), ("diaChi", ""),
         ("hoTen", ""), ("soDienThoai", ""), ("giayChungMinh", ""), ("daXuLy", -1)]
    return [("start", str(start)), ("length", str(length))] + [(f"model[{k}]", str(v)) for k, v in m]


def _tham_so_bang(cot: list[str], start: int, length: int) -> list[tuple[str, str]]:
    ts = [("draw", "1")]
    for i, c in enumerate(cot):
        ts += [(f"columns[{i}][data]", c), (f"columns[{i}][name]", ""), (f"columns[{i}][searchable]", "true"),
               (f"columns[{i}][orderable]", "false"), (f"columns[{i}][search][value]", ""), (f"columns[{i}][search][regex]", "false")]
    return ts + [("start", str(start)), ("length", str(length)), ("search[value]", ""), ("search[regex]", "false")]


def tham_so_tim_ca_nhan(so_giay_to: str, start: int = 0, length: int = 100) -> list[tuple[str, str]]:
    ts = _tham_so_bang(["", "caNhanId", "hoTen", "gioiTinh", "namSinh", "diaChi"], start, length)
    m = [("hoTen", ""), ("soGiayTo", so_giay_to), ("namSinh", ""), ("diaChiChiTiet", "")]
    return ts + [(f"model[{k}]", v) for k, v in m]


def tham_so_tim_thua(xa_id: int, so_thua: str, so_to: str, start: int = 0, length: int = 100) -> list[tuple[str, str]]:
    ts = _tham_so_bang(["", "soThuTuThua", "soHieuToBanDo", "dienTich", "diaChi", "ListMucDichSuDung"], start, length)
    m = [("soThuTuThua", so_thua), ("soHieuToBanDo", so_to), ("soThuTuThuaCu", ""), ("soHieuToBanDoCu", ""), ("loaiMucDichSuDungId", ""),
         ("loaiNguonGocSuDungDatId", ""), ("thoiHanSuDung", ""), ("ngaySuDungTu", ""), ("ngaySuDungDen", ""), ("diaChiThua", ""),
         ("xaId", xa_id), ("huyenId", 0)]
    return ts + [(f"model[{k}]", str(v)) for k, v in m]


def doc_het_trang(mot_trang: Callable[[int, int], dict], length: int = 100, toi_da: int = 5000) -> list[dict[str, Any]]:
    """Đọc mọi trang (không dừng ở 10 kết quả đầu như giao diện)."""
    kq: list[dict[str, Any]] = []
    start = 0
    while True:
        trang = mot_trang(start, length)
        ds = trang.get("data") or []
        kq += ds
        start += length
        if not ds or start >= (trang.get("recordsFiltered") or 0) or start >= toi_da:
            return kq


def doi_chieu_thua(ban_ghi: list[dict[str, Any]], hs: HoSo) -> str | None:
    """Thửa có trên MPLIS không, diện tích có khớp Excel không. None là khớp."""
    t = hs.dau.thua
    khop = [r for r in ban_ghi if (str(r.get("soThuTuThua")), str(r.get("soHieuToBanDo"))) == (str(t.so_thua), str(t.so_to))]
    if not khop:
        return f"Không thấy thửa {t.so_to}/{t.so_thua} trên MPLIS"
    if t.dien_tich is None or any(khop_dien_tich(str(r.get("dienTich") or "0"), t.dien_tich) for r in khop):
        return None
    return f"Diện tích trên MPLIS ({so(float(str(khop[0].get('dienTich')).replace(',', '.')))}) khác Excel ({so(t.dien_tich)})"


def chon_trung(ban_ghi: list[dict[str, Any]], hs: HoSo) -> str | None:
    """Số biên nhận của hồ sơ cùng thửa và cùng người nộp. MPLIS bỏ qua lọc giấy tờ nên phải tự so."""
    d = hs.dau
    thua = (str(d.thua.so_thua), str(d.thua.so_to))
    giay = {n.cccd for n in d.nguoi if n.cccd}
    cung_thua = [x for x in ban_ghi if thua in {(str(t.get("soThua")), str(t.get("soTo"))) for t in x.get("thuaDat") or []}]
    if not giay and cung_thua:  # không so được người nộp: coi là chưa có thì có thể tạo trùng
        raise ValueError("Thửa đã có hồ sơ tiếp nhận mà người nhận không có CCCD nên không tra trùng được; kiểm tra tay trên MPLIS")
    return next((str(x["soBienNhan"]) for x in cung_thua if (x.get("nguoiNopDon") or {}).get("giayChungMinh") in giay), None)


def gia_tri_doc(x: dict[str, Any]) -> dict[str, str]:
    t = (x.get("thuaDat") or [{}])[0]
    return {
        "so_to": str(t.get("soTo", "")), "so_thua": str(t.get("soThua", "")),
        "dien_tich": so(t.get("dienTich")), "cccd_nop": str((x.get("nguoiNopDon") or {}).get("giayChungMinh", "")),
    }


class TraCuuPage(TiepNhanPage):
    P = "tra_cuu"

    def _tim(self, xa: str, gia_tri: dict[str, str]) -> list[dict[str, Any]]:
        self.page.goto(urljoin(self.base_url, self.L.data[self.P]["duong_dan"]))
        self._cho()
        self._select2("select2_xa", xa, xa)
        for o, v in gia_tri.items():
            self._dat(self._el(o), v)
        # ponytail: chỉ đọc trang đầu 10 kết quả; thửa có trên 10 hồ sơ thì cần lật trang.
        with self.page.expect_response(lambda r: "AdvancedSearchHoSoTiepNhan" in r.url) as ri:
            self._el("nut_tim").click()
        self._cho()
        return ri.value.json().get("data") or []

    def tim(self, hs: HoSo) -> str | None:
        d = hs.dau
        xa = ten_xa(d.thua.dia_chi)
        if not xa:
            raise ValueError(f"Không tách được tên xã từ địa chỉ: {d.thua.dia_chi!r}")
        return chon_trung(self._tim(xa, {"o_so_thua": str(d.thua.so_thua), "o_so_to": str(d.thua.so_to)}), hs)

    def doc(self, hs: HoSo, ma_ho_so: str) -> dict[str, str]:
        kq = self._tim(ten_xa(hs.dau.thua.dia_chi) or "", {"o_so_bien_nhan": ma_ho_so})
        return gia_tri_doc(kq[0]) if len(kq) == 1 else {}
