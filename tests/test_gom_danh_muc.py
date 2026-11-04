from tiep_nhan.domain.danh_muc import DanhMuc
from tiep_nhan.domain.gom_ho_so import CheDoGom, gom
from tiep_nhan.domain.rules import kiem_tra_file
from tiep_nhan.infra.excel_in import read_phieu


def test_gom(mau):
    rows, _ = kiem_tra_file(read_phieu(mau))
    assert len(gom(rows, CheDoGom.MOI_DONG)) == 3
    g = gom(rows, CheDoGom.THEO_MA_DAU_VAO)
    assert len(g) == 1 and g[0].excel_rows == [6, 7, 8]


def test_br05_danh_muc(mau):
    rows, _ = kiem_tra_file(read_phieu(mau))
    hs = gom(rows)
    dm = DanhMuc({"loai_nha": {"liền kề": "Nhà liền kề"}, "cap_nha": {"III": "TODO"}})
    assert dm.anh_xa("loai_nha", "Liền  Kề") == "Nhà liền kề"
    assert dm.anh_xa("cap_nha", "III") is None           # TODO coi như chưa ánh xạ
    loi = dm.kiem_tra(hs)
    assert {v.noi_dung.split("]")[0] for v in loi} == {"[cap_nha", "[ket_cau", "[thoi_han"}
