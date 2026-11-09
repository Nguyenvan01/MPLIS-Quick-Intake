import openpyxl
from tiep_nhan.core.batch import nap_lo
from tiep_nhan.domain.danh_muc import DanhMuc
from tiep_nhan.domain.rules import kiem_tra_file
from tiep_nhan.infra.excel_in import read_phieu


def test_doc_cot_theo_ten(mau):
    r = read_phieu(mau)
    assert r.header_row == 5
    assert r.columns["ong_ho_ten"] == "F" and r.columns["ba_ho_ten"] == "J"
    assert r.columns["ma_dau_vao"] == "AD"
    assert [x.excel_row for x in r.rows] == [6, 7, 8]


def test_canh_bao_cau_truc(mau):
    text = " ".join(read_phieu(mau).warnings)
    assert "AA5:AA6" in text and "Dòng 9" in text


def _file_khong_nhom(path):
    """Mẫu 'Đợt': hai nhóm người không ghi Ông/Bà, dùng Số hợp đồng thay Mã đầu vào. Dữ liệu giả."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.merge_cells("B2:E2")
    ws.merge_cells("F2:I2")
    for cot, ten in zip("JKLMN", ["Hợp đồng mua bán", None, "Thửa đất", "Số tờ", "Diện tích (m2)"]):
        ws[f"{cot}2"] = ten
    for cot in "LMN":
        ws.merge_cells(f"{cot}2:{cot}3")
    tieu_de = ["STT", "Họ và tên", "Năm sinh", "CCCD", "Địa chỉ", "Họ và tên", "Năm sinh", "CCCD", "Địa chỉ", "Số hợp đồng", "Ngày"]
    for i, ten in enumerate(tieu_de, 1):
        ws.cell(3, i, ten)
    # Cột đầu là nữ để kiểm tra vợ/chồng theo CCCD, không theo vị trí cột.
    ws.append([1, "Người Vợ", "1969", "001169000001", "ĐC A", "Người Chồng", "1962", "001062000002", "ĐC A", "AD6-24/HD", "08/02/2023", 3666, 3, 100])
    wb.save(path)
    return path


def test_doc_mau_khong_nhom_ong_ba(tmp_path):
    kq = read_phieu(_file_khong_nhom(tmp_path / "dot.xlsx"))
    assert kq.columns["ong_ho_ten"] == "B" and kq.columns["ba_ho_ten"] == "F"
    assert kq.rows[0].values["ma_dau_vao"] == "AD6-24/HD"


def test_mau_khong_nhom_xac_dinh_chong_theo_cccd(tmp_path):
    rows, issues = kiem_tra_file(read_phieu(_file_khong_nhom(tmp_path / "dot.xlsx")))
    assert not [i for i in issues if i.muc == "loi"]
    assert [n.ho_ten for n in rows[0].chong_vo] == ["Người Chồng", "Người Vợ"]


def test_mac_dinh_dien_khi_excel_trong(tmp_path):
    lo = nap_lo(_file_khong_nhom(tmp_path / "dot.xlsx"), DanhMuc({}), mac_dinh={"can_bo": "Đức Anh", "thoi_han": "Lâu dài"})
    d = lo.ho_so[0].dau
    assert d.can_bo == "Đức Anh" and d.thua.thoi_han == "Lâu dài"
    assert not [v for v in lo.van_de if v.ma == "BR-06" and ("Cán bộ" in v.noi_dung or "Thời hạn" in v.noi_dung)]


def test_khong_mac_dinh_van_canh_bao(tmp_path):
    lo = nap_lo(_file_khong_nhom(tmp_path / "dot.xlsx"), DanhMuc({}))
    assert lo.ho_so[0].dau.can_bo is None
    assert [v for v in lo.van_de if v.ma == "BR-06" and "Cán bộ" in v.noi_dung]


def test_gia_tri_excel_uu_tien_hon_mac_dinh(mau):
    lo = nap_lo(mau, DanhMuc({}), mac_dinh={"can_bo": "Người Khác"})
    assert {h.dau.can_bo for h in lo.ho_so if h.dau.excel_row == 7} != {"Người Khác"}


def test_doc_cot_nguoi_nop(mau, tmp_path):
    from openpyxl import load_workbook
    wb = load_workbook(mau)
    ws = wb.worksheets[0]
    c = ws.max_column + 1
    ws.cell(5, c, "Người nộp")
    ws.cell(6, c, "NGUYỄN THỊ AN")
    f = tmp_path / "co_nguoi_nop.xlsx"
    wb.save(f)
    assert read_phieu(f).rows[0].values["nguoi_nop"] == "NGUYỄN THỊ AN"
