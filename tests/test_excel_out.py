from openpyxl import load_workbook

from tiep_nhan.infra.excel_out import KetQuaDong, ghi_ket_qua


def test_ghi_ket_qua(mau, tmp_path):
    dich = ghi_ket_qua(mau, 5, [KetQuaDong(6, "HS-0001", "Thành công", "")], dich=tmp_path / "kq.xlsx")
    ws = load_workbook(dich).active
    hdr = [c.value for c in ws[5]]
    c = hdr.index("Mã hồ sơ MPLIS") + 1
    assert ws.cell(6, c).value == "HS-0001" and ws.cell(6, c + 1).value == "Thành công"


def test_xuat_ket_qua_ghi_dung_dong_cua_ho_so(mau, tmp_path):
    from openpyxl import load_workbook

    from tiep_nhan.core.batch import nap_lo, xuat_ket_qua
    from tiep_nhan.domain.danh_muc import DanhMuc

    lo = nap_lo(mau, DanhMuc({}))
    hs = lo.ho_so[0]
    dich = xuat_ket_qua(lo, {hs.key: ("Lỗi", "lệch diện tích", "")}, dich=tmp_path / "kq.xlsx")
    assert [c.value for c in load_workbook(dich)[lo.doc.sheet][hs.dong[0].excel_row]][-2:] == ["Lỗi", "lệch diện tích"]
