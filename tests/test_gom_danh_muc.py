import pytest

from tiep_nhan.domain.danh_muc import DanhMuc
from tiep_nhan.domain.gom_ho_so import CheDoGom, gom
from tiep_nhan.domain.rules import kiem_tra_file
from tiep_nhan.infra.excel_in import read_phieu
from .conftest import CONFIG


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


def test_danh_muc_da_chot_cho_dot_vinhomes():
    dm = DanhMuc.doc(CONFIG / "danh_muc.toml")
    assert dm.anh_xa("loai_nha", "Liên kế") == "Nhà ở liên kế"
    assert dm.anh_xa("loai_nha", "Biệt thự") == "Nhà biệt thự"
    assert dm.anh_xa("cap_nha", "III") == "Cấp 3"
    assert dm.anh_xa("ket_cau", "Nhà khung bê tông cốt thép") == "Tường gạch, khung sàn bằng bê tông cốt thép"
    assert dm.anh_xa("thoi_han", "Lâu dài") == "Lâu dài"


DU_BANG = {"loai_nha": {"L": "x"}, "cap_nha": {"C": "x"}, "ket_cau": {"K": "x"}, "thoi_han": {"T": "x"}}


def _hs_dia_chi(dia_chi: str, **thieu):
    from types import SimpleNamespace as N
    nha = {"loai_nha": "L", "cap_nha": "C", "ket_cau": "K"}
    thua = {"thoi_han": "T", "dia_chi": dia_chi}
    nha.update({k: v for k, v in thieu.items() if k in nha})
    thua.update({k: v for k, v in thieu.items() if k in thua})
    return N(dong=[N(excel_row=7, nha=N(**nha), thua=N(**thua))])


@pytest.mark.parametrize("trong", [None, ""])
@pytest.mark.parametrize("truong", ["loai_nha", "cap_nha", "ket_cau", "thoi_han"])
def test_br05_truong_wizard_trong_thi_chan_truoc_khi_chay(truong, trong):
    loi = DanhMuc(DU_BANG).kiem_tra([_hs_dia_chi("Lô A", **{truong: trong})])
    assert [(v.excel_row, v.muc, v.ma) for v in loi] == [(7, "loi", "BR-05")]
    assert f"[{truong}]" in loi[0].noi_dung and "trống" in loi[0].noi_dung


def test_br05_du_truong_wizard_thi_khong_bao_gi():
    assert DanhMuc(DU_BANG).kiem_tra([_hs_dia_chi("Lô A")]) == []


def test_br05_xa_phai_co_trong_danh_sach_dvhc():
    dm = DanhMuc({**DU_BANG, "xa": {"Nghĩa Trụ": "12345"}})
    assert dm.kiem_tra([_hs_dia_chi("Lô A, Xã Nghĩa Trụ")]) == []
    assert [v.muc for v in dm.kiem_tra([_hs_dia_chi("Lô A, Xã Như Quỳnh")])] == ["loi"]
    assert [(v.ma, v.muc) for v in dm.kiem_tra([_hs_dia_chi("Lô A, Xã Nghĩa Trụ + Xã Như Quỳnh")])] == [("BR-05", "canh_bao")]


def test_danh_muc_cu_chua_co_bang_xa_thi_khong_chan():
    assert DanhMuc(DU_BANG).kiem_tra([_hs_dia_chi("Lô A, Xã Bất Kỳ")]) == []


def test_them_va_luu_danh_muc_doc_lai_duoc(tmp_path):
    dm = DanhMuc({"cap_nha": {"III": "Cấp 3"}})
    dm.them("loai_nha", 'Liền "kề"', "Nhà ở liền kề")
    dm.luu(tmp_path / "dm.toml")
    moi = DanhMuc.doc(tmp_path / "dm.toml")
    assert moi.anh_xa("loai_nha", 'liền "kề"') == "Nhà ở liền kề" and moi.anh_xa("cap_nha", "III") == "Cấp 3"
    assert moi.bang("cap_nha") == ["Cấp 3"]


def test_chua_anh_xa_dem_so_ho_so():
    from types import SimpleNamespace as N
    d = N(excel_row=7, nha=N(loai_nha="Lạ", cap_nha=None, ket_cau=None), thua=N(thoi_han=None, dia_chi=None))
    assert DanhMuc({"loai_nha": {}}).chua_anh_xa([N(dong=[d]), N(dong=[d])]) == {("loai_nha", "Lạ"): [7, 7]}
