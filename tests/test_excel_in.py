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
