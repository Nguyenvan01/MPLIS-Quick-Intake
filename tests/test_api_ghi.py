"""Dựng và đọc dữ liệu các lệnh ghi MPLIS (Đợt 1: Lưu, chọn GCN, chuyển Thụ lý). Không mở trình duyệt."""
import pytest

from tiep_nhan.domain.gom_ho_so import gom
from tiep_nhan.domain.rules import kiem_tra_file
from tiep_nhan.infra.excel_in import read_phieu
from tiep_nhan.mplis.pages.tra_cuu import tham_so_tim_ca_nhan, tham_so_tim_gcn
from tiep_nhan.mplis.api_ghi import (chon_ban_ghi_ca_nhan, chon_gcn_hien_hanh, kiem_phap_ly, kiem_so_khac_gcn_cu, chon_tai_khoan, doc_ket_qua_luu, doc_ngay_hen_tra, kiem_ngan_chan,
                                     than_chuyen, than_luu, than_ngan_chan_thua, ten_quy_trinh)

GUID = "d3022e23-3933-4d30-8182-bea1097ed8c9"


@pytest.fixture
def hs(mau):
    rows, _ = kiem_tra_file(read_phieu(mau))
    return gom(rows)[0]


def _thua(hs, **them):
    t = hs.dau.thua
    return {"thuaDatId": 729983, "soThuTuThua": t.so_thua, "soHieuToBanDo": t.so_to, "dienTich": t.dien_tich, "diaChi": "địa chỉ thửa", **them}


def test_than_luu_dung_cau_truc_ban_ghi(hs):
    b = than_luu(hs, xa_id=12031, thua=_thua(hs), nguoi_nop={"hoTen": "A", "giayChungMinh": "", "diachi": "", "caNhanId": ""},
                 quy_trinh=("QD_1_012787_2", "Tên quy trình"), ngay_tiep_nhan="2026-11-10T01:00:00.000Z",
                 ngay_hen_tra="2026-11-25T01:00:00.000Z")
    h = b["hoSo"]
    assert b["capNhatSoBienNhanMoi"] is False and b["thoiGianTiepNhanTheoHeThong"] is True
    assert (h["xaId"], h["tinhId"], h["huyenId"], h["phuongThucNhanHoSo"], h["phuongThucTraKetQua"]) == ("12031", "33", "0", "1", "0")
    assert h["thuaDat"] == [{"soThua": hs.dau.thua.so_thua, "soTo": hs.dau.thua.so_to, "dienTich": hs.dau.thua.dien_tich,
                             "diaChi": "địa chỉ thửa", "thuaDatId": 729983, "xaId": 12031}]
    assert h["listQuyTrinh"] == [{"TenQuyTrinh": "Tên quy trình", "MaQuyTrinh": "QD_1_012787_2", "TrangThai": 0, "IsStartFirst": True}]
    assert h["diaChiTaiSan"] == hs.dau.dia_chi_tai_san
    assert h["nguoiNopDon"]["hoTen"] == "A" and h["nguoiNopDon"]["vaiTroNguoiNopDon"] == "0"
    assert h["ngayhenTra"] == "2026-11-25T01:00:00.000Z"


def test_than_luu_thieu_ma_thua_thi_dung(hs):
    with pytest.raises(ValueError, match="mã thửa"):
        than_luu(hs, xa_id=1, thua=_thua(hs, thuaDatId=None), nguoi_nop={}, quy_trinh=("a", "b"), ngay_tiep_nhan="", ngay_hen_tra="")


def test_than_ngan_chan_thua(hs):
    b = than_ngan_chan_thua(_thua(hs), 12031)
    assert b == {"kiemTraNganChanThuaInputs": [{"thuaDatId": 729983, "soTo": hs.dau.thua.so_to, "soThua": hs.dau.thua.so_thua,
                                                "dienTich": hs.dau.thua.dien_tich, "xaId": 12031, "diaChi": "địa chỉ thửa"}]}


@pytest.mark.parametrize("kq", [
    {"value": {"coNganChan": True}},
    {"value": {"coNganChan": False}, "coTheChap": True, "theChapMessage": "đang thế chấp"},
    {"value": {"coNganChan": False}, "listThuaDangThuLy": [{"x": 1}]},
    {"success": True, "value": {"coNganChan": False}, "coGhiNoNghiaVuTaiChinh": True},
    {"success": False, "message": "lỗi"},
])
def test_ngan_chan_thi_dung(kq):
    with pytest.raises(RuntimeError):
        kiem_ngan_chan(kq, "chọn thửa")


def test_khong_ngan_chan_thi_qua():
    kiem_ngan_chan({"value": {"coNganChan": False}, "coTheChap": False, "listThuaDangThuLy": []}, "chọn thửa")


def test_doc_ket_qua_luu():
    kq = {"success": True, "value": {"soBienNhan": "12031", "Id": GUID, "processId": "711d5baa-1718-46f8-a05f-92dfdc8cdc25"},
          "listGiayChungNhan": [{"giayChungNhanId": 2566210, "Id": "216c8607-f52f-4ec1-a12b-295bf20f711a"}]}
    r = doc_ket_qua_luu(kq)
    assert (r.so_bien_nhan, r.id, r.process_id) == ("12031", GUID, "711d5baa-1718-46f8-a05f-92dfdc8cdc25")
    assert r.gcn == kq["listGiayChungNhan"]


@pytest.mark.parametrize("kq", [
    {"success": False, "message": "trùng"},
    {"success": True, "value": {"soBienNhan": "1", "Id": "0", "processId": GUID}},
    {"success": True, "value": {"soBienNhan": "", "Id": GUID, "processId": GUID}},
])
def test_ket_qua_luu_thieu_thi_bao(kq):
    with pytest.raises(RuntimeError):
        doc_ket_qua_luu(kq)


def test_ngay_hen_tra_chi_nhan_iso():
    assert doc_ngay_hen_tra({"success": True, "value": "2026-11-23T01:00:00.000Z"}) == "2026-11-23T01:00:00.000Z"
    assert doc_ngay_hen_tra({"success": True, "value": "/Date(1795395600123)/"}) == "2026-11-23T01:00:00.123Z"
    with pytest.raises(RuntimeError):
        doc_ngay_hen_tra({"success": True, "value": "23/11/2026"})


def test_ten_quy_trinh():
    ds = [{"SchemaCode": "QD_1_012787_1", "SchemaName": "một"}, {"SchemaCode": "QD_1_012787_2", "SchemaName": "hai"}]
    assert ten_quy_trinh({"success": True, "value": ds}, "QD_1_012787_2") == "hai"
    with pytest.raises(RuntimeError):
        ten_quy_trinh({"success": True, "value": ds}, "QD_9")


def test_chon_ban_ghi_ca_nhan(hs):
    n = hs.dau.nguoi_nop
    dung = {"caNhanId": 5, "hoTen": n.ho_ten.lower(), "namSinh": n.nam_sinh}
    assert chon_ban_ghi_ca_nhan([], n) is None
    assert chon_ban_ghi_ca_nhan([dung, {"caNhanId": 6, "hoTen": "KHÁC", "namSinh": n.nam_sinh}], n) == dung
    assert chon_ban_ghi_ca_nhan([dung, dict(dung, caNhanId=7)], n) == dung  # một người bị nhập trùng: lấy bản đầu
    with pytest.raises(RuntimeError):
        chon_ban_ghi_ca_nhan([dict(dung, diaChi="A"), dict(dung, caNhanId=7, diaChi="B")], n)


def test_chon_tai_khoan():
    ds = {"ltmung.nnmt": "Lê Thị Mừng", "abc": "Nguyễn Văn A"}
    assert chon_tai_khoan(ds, "ltmung.nnmt") == "ltmung.nnmt"
    assert chon_tai_khoan(ds, "Mừng") == "ltmung.nnmt"
    with pytest.raises(RuntimeError):
        chon_tai_khoan(ds, "Không Ai")


def test_than_chuyen():
    assert than_chuyen("2", GUID, "pid", "abc") == {"schemaCode": "QD_1_012787_2", "processId": "pid", "commandName": "Chuyển phân công",
                                                    "hoSoTiepNhanId": GUID, "userName": "abc", "moveToState": None, "ghiChuChuyenViec": ""}


def test_tham_so_tim_ca_nhan():
    ts = dict(tham_so_tim_ca_nhan("001", 0, 50))
    assert ts["model[soGiayTo]"] == "001" and ts["columns[1][data]"] == "caNhanId" and ts["length"] == "50"


def test_tham_so_tim_gcn():
    ts = dict(tham_so_tim_gcn(12031, "1265", "2"))
    assert (ts["model[xaId]"], ts["model[soThuTuThua]"], ts["model[soHieuToBanDo]"]) == ("12031", "1265", "2")
    assert ts["columns[1][data]"] == "soPhatHanh" and ts["model[soPhatHanh]"] == ""


def test_chon_gcn_hien_hanh():
    cu = {"giayChungNhanId": 1, "Id": GUID, "isLastest": False}
    moi = {"giayChungNhanId": 2, "Id": GUID, "isLastest": True}
    assert chon_gcn_hien_hanh([cu, moi]) == moi
    with pytest.raises(RuntimeError, match="0 GCN"):
        chon_gcn_hien_hanh([cu])
    with pytest.raises(RuntimeError, match="2 GCN"):
        chon_gcn_hien_hanh([moi, dict(moi, giayChungNhanId=3)])


def test_kiem_phap_ly():
    kiem_phap_ly({"daCongNhanPhapLy": True})
    with pytest.raises(RuntimeError, match="pháp lý"):
        kiem_phap_ly({"daCongNhanPhapLy": False})


def test_so_phat_hanh_trung_gcn_cu_thi_dung():
    kiem_so_khac_gcn_cu({"soPhatHanh": "AA 00000001"}, "AA 12345678")
    with pytest.raises(RuntimeError, match="GCN cũ"):
        kiem_so_khac_gcn_cu({"soPhatHanh": "AA 00000001"}, "aa00000001")
