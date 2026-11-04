import pytest

from tiep_nhan.domain.chuan_hoa import cccd_khop, to_decimal, to_int
from tiep_nhan.domain.rules import kiem_tra_file
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
    assert len(rows) == 1 and any(i.ma == "BR-03" and i.muc == "loi" for i in issues)


def test_cccd_dang_so_mat_so_0():
    r = ReadResult(sheet="s", header_row=5, columns={}, rows=[_raw(6, ba_cccd=1163000001)])
    rows, issues = kiem_tra_file(r)
    assert rows[0].nguoi[0].cccd == "001163000001"
    assert any("mất số 0" in i.noi_dung for i in issues)
