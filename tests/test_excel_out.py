from openpyxl import load_workbook

from tiep_nhan.infra.excel_out import KetQuaDong, ghi_ket_qua


def test_ghi_ket_qua(mau, tmp_path):
    dich = ghi_ket_qua(mau, 5, [KetQuaDong(6, "HS-0001", "Thành công", "")], dich=tmp_path / "kq.xlsx")
    ws = load_workbook(dich).active
    hdr = [c.value for c in ws[5]]
    c = hdr.index("Mã hồ sơ MPLIS") + 1
    assert ws.cell(6, c).value == "HS-0001" and ws.cell(6, c + 1).value == "Thành công"
