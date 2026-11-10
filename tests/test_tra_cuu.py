"""Tìm trùng và đọc lại trên dữ liệu MPLIS trả về. Dữ liệu giả, cùng dạng phản hồi AdvancedSearchHoSoTiepNhan."""
import pytest

from tiep_nhan.domain.models import HoSo, Nguoi
from tiep_nhan.domain.rules import kiem_tra_dong
from tiep_nhan.infra.excel_in import RawRow
from tiep_nhan.mplis.pages.tiep_nhan import chon_ca_nhan, khop_can_bo
from tiep_nhan.mplis.pages.tra_cuu import chon_trung, gia_tri_doc
from tiep_nhan.mplis.port import so_sanh

NAM, NU = "001063000001", "001163000002"


def _hs():
    dong, _ = kiem_tra_dong(RawRow(excel_row=6, values={
        "stt": 1, "ma_dau_vao": "H31-1", "so_to": 3, "so_thua": 3549, "dien_tich": 56,
        "ong_ho_ten": "Người Chồng", "ong_cccd": NAM, "ba_ho_ten": "Người Vợ", "ba_cccd": NU}))
    return HoSo(key="k", dong=(dong,))


def _ban_ghi(so_bn, giay, thua=(("3549", "3", 56),)):
    return {"soBienNhan": so_bn, "nguoiNopDon": {"giayChungMinh": giay, "hoTen": "X"},
            "thuaDat": [{"soThua": a, "soTo": b, "dienTich": c} for a, b, c in thua]}


def test_trung_khi_cung_thua_cung_nguoi_nop():
    assert chon_trung([_ban_ghi("A", "999999999999"), _ban_ghi("B", NAM)], _hs()) == "B"


def test_nguoi_nop_la_vo_van_tinh_trung():
    assert chon_trung([_ban_ghi("B", NU)], _hs()) == "B"


def test_cung_thua_nguoi_khac_khong_trung():
    assert chon_trung([_ban_ghi("A", "999999999999")], _hs()) is None


def test_cung_nguoi_thua_khac_khong_trung():
    assert chon_trung([_ban_ghi("A", NAM, thua=(("3576", "3", 64),))], _hs()) is None


def test_ho_so_nhieu_thua_co_thua_can_tim():
    assert chon_trung([_ban_ghi("A", NAM, thua=(("3576", "3", 64), ("3549", "3", 56)))], _hs()) == "A"


def test_doc_lai_khop_excel():
    assert so_sanh(_hs(), gia_tri_doc(_ban_ghi("B", NAM))) == {}


def test_doc_lai_lech_dien_tich():
    assert "dien_tich" in so_sanh(_hs(), gia_tri_doc(_ban_ghi("B", NAM, thua=(("3549", "3", 60),))))


def _nguoi(nam=1962):
    return Nguoi(vai_tro="Ông", ho_ten="Nguyễn Văn A", nam_sinh=nam, cccd=NAM)


def _dong(ten, nam):
    return ["", "123", ten, "Nam", nam, "Địa chỉ"]


def test_chon_ban_ghi_khop_ten_va_nam_sinh():
    assert chon_ca_nhan([_dong("NGUYỄN VĂN B", "1962"), _dong("Nguyễn  Văn A", "1962")], _nguoi()) == 1


def test_nam_sinh_dang_ngay_day_du():
    assert chon_ca_nhan([_dong("Nguyễn Văn A", "05/03/1962"), _dong("Nguyễn Văn A", "1970")], _nguoi()) == 0


def test_nhieu_ban_ghi_cung_khop_thi_khong_chon():
    assert chon_ca_nhan([_dong("Nguyễn Văn A", "1962"), _dong("Nguyễn Văn A", "1962")], _nguoi()) is None


def test_khong_ban_ghi_nao_khop_thi_khong_chon():
    assert chon_ca_nhan([_dong("Nguyễn Văn B", "1962")], _nguoi()) is None


def test_khop_can_bo_theo_tai_khoan_hoac_ten():
    o = ["", "ltmung.nnmt", "Lê Thị Mừng", "Hưng Yên"]
    assert khop_can_bo(o, "ltmung.nnmt")
    assert khop_can_bo(o, "Thị Mừng")
    assert not khop_can_bo(o, "Đức Anh")
    assert not khop_can_bo(["Không có dữ liệu"], "Đức Anh")


def _hs_dia_chi(dia_chi, ma="AD7-46/VHOCP3/HD"):
    dong, _ = kiem_tra_dong(RawRow(excel_row=6, values={
        "stt": 1, "ma_dau_vao": ma, "so_to": 3, "so_thua": 1, "dia_chi_thua": dia_chi, "ong_ho_ten": "Người Chồng", "ong_cccd": NAM}))
    return dong


def test_so_nha_tu_dau_dia_chi():
    assert _hs_dia_chi("TĐ18-107, Khu đô thị Đại An, xã Nghĩa Trụ").so_nha == "TĐ18-107"


def test_so_nha_tu_ma_can_khi_dia_chi_khong_co_so():
    assert _hs_dia_chi("Khu đô thị Đại An, xã Nghĩa Trụ").so_nha == "AD7-46"


def test_nhan_biet_da_dang_nhap():
    from tiep_nhan.mplis.ui_adapter import da_dang_nhap
    base = "https://hye.mplis.gov.vn"
    assert da_dang_nhap("https://hye.mplis.gov.vn/dc/TiepNhanHoSo", base)
    assert not da_dang_nhap("https://authen.mplis.gov.vn/account/login?x=/dc/", base)
    assert not da_dang_nhap("about:blank", base)


def test_dien_tich_mplis_dung_dau_cham_van_khop():
    from tiep_nhan.mplis.pages.tiep_nhan import khop_dien_tich
    assert khop_dien_tich("123.53", 123.53)
    assert khop_dien_tich("70", 70.0)
    assert khop_dien_tich("123,50", 123.5)
    assert not khop_dien_tich("107.5", 112.0)


def _hs_khong_cccd():
    dong, _ = kiem_tra_dong(RawRow(excel_row=6, values={
        "stt": 1, "ma_dau_vao": "H31-1", "so_to": 3, "so_thua": 3549, "dien_tich": 56, "ong_ho_ten": "Người Chồng"}))
    return HoSo(key="k", dong=(dong,))


def test_khong_co_cccd_ma_thua_da_co_ho_so_thi_bao_loi_khong_coi_la_moi():
    with pytest.raises(ValueError, match="CCCD"):
        chon_trung([_ban_ghi("A", None)], _hs_khong_cccd())


def test_khong_co_cccd_va_thua_chua_co_ho_so_thi_tao_moi_duoc():
    assert chon_trung([_ban_ghi("A", None, thua=(("3576", "3", 64),))], _hs_khong_cccd()) is None


def test_tham_so_tra_ho_so_dung_cac_truong_mplis_gui():
    from tiep_nhan.mplis.pages.tra_cuu import tham_so_tra_ho_so
    ts = dict(tham_so_tra_ho_so(12031, so_thua="3549", so_to="3", start=200, length=100))
    assert ts["model[xaId]"] == "12031" and ts["model[tinhId]"] == "33"
    assert ts["model[soThua]"] == "3549" and ts["model[soTo]"] == "3" and ts["model[soBienNhan]"] == ""
    assert ts["start"] == "200" and ts["length"] == "100" and ts["model[daXuLy]"] == "-1" and ts["model[trangThaiKetISO][]"] == "0"


def test_doc_het_moi_trang_ket_qua():
    from tiep_nhan.mplis.pages.tra_cuu import doc_het_trang
    goi = []

    def mot_trang(start, length):
        goi.append(start)
        return {"recordsFiltered": 250, "data": [{"i": i} for i in range(start, min(start + length, 250))]}

    kq = doc_het_trang(mot_trang, length=100)
    assert len(kq) == 250 and goi == [0, 100, 200]


def test_doc_het_trang_khi_khong_co_ket_qua():
    from tiep_nhan.mplis.pages.tra_cuu import doc_het_trang
    assert doc_het_trang(lambda s, n: {"recordsFiltered": 0, "data": []}) == []


@pytest.mark.parametrize("ban_ghi, mong", [
    ([{"soThuTuThua": 3549, "soHieuToBanDo": 3, "dienTich": 56.0}], None),
    ([{"soThuTuThua": "3549", "soHieuToBanDo": "3", "dienTich": "56"}], None),
    ([{"soThuTuThua": 3549, "soHieuToBanDo": 3, "dienTich": 107.5}], "Diện tích trên MPLIS (107,5) khác Excel (56)"),
    ([{"soThuTuThua": 3576, "soHieuToBanDo": 3, "dienTich": 56.0}], "Không thấy thửa 3/3549 trên MPLIS"),
    ([], "Không thấy thửa 3/3549 trên MPLIS"),
])
def test_doi_chieu_thua(ban_ghi, mong):
    from tiep_nhan.mplis.pages.tra_cuu import doi_chieu_thua
    assert doi_chieu_thua(ban_ghi, _hs()) == mong
