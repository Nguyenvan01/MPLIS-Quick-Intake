import pytest

from tiep_nhan.domain.chuan_hoa import cccd_khop, ten_xa, to_cccd, to_decimal, to_int
from tiep_nhan.domain.models import Nguoi
from tiep_nhan.domain.rules import kiem_tra_dong, kiem_tra_file
from tiep_nhan.infra.excel_in import RawRow, ReadResult, read_phieu


@pytest.mark.parametrize("raw,expected", [("45,6", 45.6), ("218,5", 218.5), (217, 217.0), ("84", 84.0), ("1.234,5", 1234.5)])
def test_so_thap_phan(raw, expected):
    assert to_decimal(raw) == expected


def test_so_tang():
    assert to_int("5 tầng") == 5


def test_br02_cccd():
    assert cccd_khop("001163000001", 1963, "Bà") == []
    assert cccd_khop("001163000001", 1963, "Ông")      # CCCD nữ ở cột Ông
    assert cccd_khop("001163000001", 1964, "Bà")       # lệch năm sinh


def test_file_mau(mau):
    rows, issues = kiem_tra_file(read_phieu(mau))
    assert len(rows) == 3
    assert [n.vai_tro for n in rows[0].nguoi] == ["Bà"]
    assert rows[0].nha.dt_xay_dung == 45.6 and rows[0].nha.so_tang == 5
    assert rows[2].thua.ma_phat_hanh == "AA 00000001"
    assert not [i for i in issues if i.muc == "loi"]
    assert any(i.ma == "BR-06" and "Mã phát hành" in i.noi_dung for i in issues if i.excel_row == 6)
    assert any(i.ma == "BR-08" for i in issues)


def _raw(row, **v):
    base = dict(stt=1, ma_dau_vao="H31.36-260316-0024", so_to=3, so_thua=100, ba_ho_ten="NGUYỄN THỊ AN",
                ba_nam_sinh=1963, ba_cccd="001163000001")
    base.update(v)
    return RawRow(excel_row=row, values=base)


def test_br01_khong_co_nguoi():
    r = ReadResult(sheet="s", header_row=5, columns={}, rows=[_raw(6, ba_ho_ten=None, ba_nam_sinh=None, ba_cccd=None)])
    rows, issues = kiem_tra_file(r)
    assert rows == [] and issues[0].ma == "BR-01"


def test_br03_trung_to_thua():
    r = ReadResult(sheet="s", header_row=5, columns={}, rows=[_raw(6), _raw(7, stt=2)])
    rows, issues = kiem_tra_file(r)
    assert len(rows) == 1 and any(i.ma == "BR-03" and i.muc == "canh_bao" for i in issues)  # loại dòng trùng, không chặn cả lô


def test_cccd_dang_so_mat_so_0():
    r = ReadResult(sheet="s", header_row=5, columns={}, rows=[_raw(6, ba_cccd=1163000001)])
    rows, issues = kiem_tra_file(r)
    assert rows[0].nguoi[0].cccd == "001163000001"
    assert any("mất số 0" in i.noi_dung for i in issues)


NAM, NU = "001063000001", "001163000002"


def _dong(**nguoi):
    return kiem_tra_dong(RawRow(excel_row=6, values={"stt": 1, "ma_dau_vao": "H31-1", "so_to": 2, "so_thua": 1133, **nguoi}))


@pytest.mark.parametrize("cccd,gioi", [("001063000001", "Nam"), ("001163000001", "Nữ"), ("001203000001", "Nam"), ("001303000001", "Nữ")])
def test_gioi_tinh_theo_chu_so_thu_4(cccd, gioi):
    assert Nguoi(vai_tro="Bà", ho_ten="Thử", cccd=cccd).gioi_tinh == gioi


def test_gioi_tinh_khong_cccd_theo_cot():
    assert Nguoi(vai_tro="Ông", ho_ten="Thử").gioi_tinh == "Nam"


def test_mot_nguoi_la_ca_nhan():
    dong, _ = _dong(ba_ho_ten="Thử", ba_cccd=NU)
    assert not dong.la_vo_chong


def test_vo_chong_theo_cccd_khi_dao_cot():
    dong, _ = _dong(ong_ho_ten="Vợ", ong_cccd=NU, ba_ho_ten="Chồng", ba_cccd=NAM)
    assert dong.la_vo_chong
    assert [n.ho_ten for n in dong.chong_vo] == ["Chồng", "Vợ"]


def test_br09_hai_nguoi_cung_gioi_bi_chan():
    dong, issues = _dong(ong_ho_ten="Người A", ong_cccd=NAM, ba_ho_ten="Người B", ba_cccd="001063000003")
    assert dong is None
    assert [i.muc for i in issues if i.ma == "BR-09"] == ["loi"]


@pytest.mark.parametrize("dia_chi,xa", [
    ("AD18-19, Khu đô thị Đại An, Xã Nghĩa Trụ", "Nghĩa Trụ"),
    ("TĐ18-107, Khu đô thị đại An, xã Nghĩa Trụ, tỉnh Hưng Yên", "Nghĩa Trụ"),
    ("Số 5, phường Lê Lợi, tỉnh Hưng Yên", "Lê Lợi"),
    ("Thị trấn Văn Giang, tỉnh Hưng Yên", "Văn Giang"),
    ("Lô A, Xã Nghĩa Trụ + Xã Như Quỳnh", "Nghĩa Trụ"),
])
def test_ten_xa_tu_dia_chi(dia_chi, xa):
    assert ten_xa(dia_chi) == xa


@pytest.mark.parametrize("dia_chi", [None, "", "Khu đô thị Đại An"])
def test_ten_xa_khong_co(dia_chi):
    assert ten_xa(dia_chi) is None


def test_nguoi_nop_vo_chong_la_chong():
    dong, _ = _dong(ong_ho_ten="Vợ", ong_cccd=NU, ba_ho_ten="Chồng", ba_cccd=NAM)
    assert dong.nguoi_nop.ho_ten == "Chồng"


def test_nguoi_nop_ca_nhan():
    dong, _ = _dong(ba_ho_ten="Thử", ba_cccd=NU)
    assert dong.nguoi_nop.ho_ten == "Thử"


@pytest.mark.parametrize("raw", ["CC:001163000001", "CC: 001163000001", "cc: 001163000001"])
def test_cccd_bo_tien_to_cc(raw):
    assert to_cccd(raw)[0] == "001163000001"


@pytest.mark.parametrize("raw", ["CC:12345", "AB:001163000001"])
def test_cccd_sai_van_bao_loi(raw):
    with pytest.raises(ValueError):
        to_cccd(raw)


def test_cccd_11_so_mat_so_0_dau_tu_bu_khi_khop_nam_sinh():
    # ô Văn bản nhưng đã mất số 0 đầu từ trước (file khách 10/11/2026)
    cccd, notes = to_cccd("01163000001", nam_sinh=1963)
    assert cccd == "001163000001" and notes


@pytest.mark.parametrize("raw, nam", [("01163000001", 1970), ("01163000001", None), ("99163000001", 1963)])
def test_cccd_11_so_khong_khop_van_bao_loi(raw, nam):
    with pytest.raises(ValueError):
        to_cccd(raw, nam_sinh=nam)


def test_nam_hoan_cong_tuong_lai_giu_nhu_excel():
    dong, issues = _dong(ong_ho_ten="Người Nhận", ong_cccd=NAM, nam_hoan_cong=2028)
    assert dong.nha.nam_hoan_cong == 2028
    assert not [i for i in issues if i.muc == "loi"]


def test_br03_trung_so_phat_hanh():
    r = ReadResult(sheet="s", header_row=5, columns={}, rows=[
        _raw(6, so_thua=100, ma_phat_hanh="AA 00000001"),
        _raw(7, so_thua=101, ma_phat_hanh="AA 00000002"),
        _raw(8, so_thua=102, ma_phat_hanh="aa00000001"),
    ])
    rows, issues = kiem_tra_file(r)
    assert [d.excel_row for d in rows] == [6, 7]
    assert [(i.excel_row, i.ma) for i in issues if i.muc == "loi"] == [(8, "BR-03")]


def test_cot_nguoi_nop_chon_dung_nguoi_nhan():
    dong, issues = kiem_tra_dong(_raw(6, ong_ho_ten="Trần Chồng", ong_cccd=NAM, nguoi_nop="nguyễn  thị an"))
    assert dong.nguoi_nop.ho_ten == "NGUYỄN THỊ AN" and dong.nguoi_nop_excel
    assert not [i for i in issues if i.muc == "loi"]


def test_cot_nguoi_nop_khong_khop_nguoi_nhan_thi_chan():
    dong, issues = kiem_tra_dong(_raw(6, nguoi_nop="Người Lạ"))
    assert dong is None and [(i.ma, i.muc) for i in issues if i.muc == "loi"] == [("BR-09", "loi")]
    assert "Người Lạ" not in issues[-1].noi_dung


def test_cot_nguoi_nop_trong_thi_giu_mac_dinh():
    dong, _ = kiem_tra_dong(_raw(6, ong_ho_ten="Trần Chồng", ong_cccd=NAM))
    assert dong.nguoi_nop.ho_ten == "Trần Chồng" and not dong.nguoi_nop_excel


@pytest.mark.parametrize("so, mong", [("AA 12345678", True), ("aa12345678", True), (" ab  12345678 ", True), ("TEST0001", False),
                                      ("AA 12312312323", False), ("9912323", False), ("AA 1234567", False), ("", False), (None, False)])
def test_so_phat_hanh_hop_le_hai_chu_tam_so(so, mong):
    from tiep_nhan.domain.chuan_hoa import so_phat_hanh_hop_le
    assert so_phat_hanh_hop_le(so) is mong


def test_trung_to_thua_trong_file_thi_loai_dong_sau_va_chi_canh_bao():
    def dong(r, stt, ten):
        return RawRow(excel_row=r, values={"stt": stt, "ma_dau_vao": f"M-{stt}", "so_to": 3, "so_thua": 3549, "dien_tich": 56, "ong_ho_ten": ten})
    kq = ReadResult(sheet="S", header_row=5, columns={}, rows=[dong(6, 1, "Người A"), dong(7, 2, "Người B"),
                    RawRow(excel_row=8, values={"stt": 3, "ma_dau_vao": "M-3", "so_to": 3, "so_thua": 3550, "dien_tich": 60, "ong_ho_ten": "Người C"})])
    rows, van_de = kiem_tra_file(kq)
    assert [r.excel_row for r in rows] == [6, 8]
    trung = [v for v in van_de if v.ma == "BR-03"]
    assert len(trung) == 1 and trung[0].muc == "canh_bao" and trung[0].excel_row == 7
    assert "3/3549" in trung[0].noi_dung and "dòng 6" in trung[0].noi_dung and "đã loại" in trung[0].noi_dung


def test_dia_chi_thua_lam_sach_va_tach_xa():
    from tiep_nhan.domain.models import ThuaDat
    t = ThuaDat(so_to=3, so_thua=3222, dia_chi="VTĐ2-39, , Khu đô thị đại An, xã Nghĩa Trụ, tỉnh Hưng Yên ")
    assert t.dia_chi == "VTĐ2-39, Khu đô thị đại An, xã Nghĩa Trụ, tỉnh Hưng Yên"   # địa chỉ tài sản (nhà)
    assert t.dia_chi_thua_dat == "xã Nghĩa Trụ, tỉnh Hưng Yên"                      # địa chỉ thửa trên GCN
    assert ThuaDat(so_to=1, so_thua=1, dia_chi="Số 5, Phường Mẫu, Hà Nội").dia_chi_thua_dat == "Phường Mẫu, Hà Nội"
    assert ThuaDat(so_to=1, so_thua=1, dia_chi="Khu A, Hưng Yên").dia_chi_thua_dat == "Khu A, Hưng Yên"  # không có xã/phường: giữ nguyên


def test_so_tang_doc_tu_chu():
    from tiep_nhan.domain.models import NhaO
    assert NhaO(so_tang="5 tầng").so_tang == 5 and NhaO(so_tang=5).so_tang == 5


@pytest.mark.parametrize("raw,loai", [("CC:001063000001", "Căn cước"), ("cc: 001063000001", "Căn cước"), ("001063000001", "CCCD")])
def test_tien_to_cc_la_can_cuoc(raw, loai):
    dong, _ = _dong(ong_ho_ten="Người Nhận", ong_cccd=raw)
    assert dong.nguoi[0].cccd == "001063000001" and dong.nguoi[0].loai_giay_to == loai
