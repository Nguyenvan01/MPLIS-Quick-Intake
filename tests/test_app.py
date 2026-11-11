"""Giao diện chạy không màn hình, MPLIS giả: không mở trình duyệt, không cần mạng."""
from __future__ import annotations

import os
from contextlib import nullcontext

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtWidgets import QLabel

from tiep_nhan.app import screens as S
from tiep_nhan.app.main_window import MainWindow
from tiep_nhan.core.state import StateStore, TrangThai
from tiep_nhan.domain.danh_muc import DanhMuc
from tiep_nhan.domain.models import VanDe
from tiep_nhan.infra import config
from tiep_nhan.infra.config import Settings
from tiep_nhan.mplis.fake import FakeMplis


@pytest.fixture
def cua_so(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    fake = FakeMplis()
    p = S.Phien(settings=Settings(username="toi"), store=StateStore(tmp_path / "s.sqlite3"), dm=DanhMuc({}),
                tao_port=lambda: nullcontext(fake), dm_path=tmp_path / "dm.toml")
    w = MainWindow(p)
    qtbot.addWidget(w)
    w.fake = fake
    return w


def _nap(w, f):
    w.man[S.LO_MOI].mo_file(f)
    w.man[S.LO_MOI].can_bo.setCurrentText("ndanh.tnmt")
    w.man[S.LO_MOI]._sang_kiem_tra()
    _du_so(w)


def _du_so(w):
    """Chạy thật bắt buộc có số phát hành; file mẫu cố ý để trống ở vài dòng nên điền bổ sung sau mỗi lần nạp lô."""
    w.phien.lo.ho_so = [h if h.dau.thua.ma_phat_hanh else _voi_so(h, f"AA {i:08d}") for i, h in enumerate(w.phien.lo.ho_so, 1)]


def _voi_so(hs, so):
    d = hs.dong[0]
    return hs.model_copy(update={"dong": (d.model_copy(update={"thua": d.thua.model_copy(update={"ma_phat_hanh": so})}),) + hs.dong[1:]})


def _chay(w, qtbot, that: bool = False):
    m = w.man[S.CHAY]
    w.di_toi(S.CHAY)  # mở màn luôn về Chạy thử nên phải chọn Chạy thật sau khi mở
    m.r_that.setChecked(that)
    m.bat_dau()
    qtbot.waitUntil(lambda: not w.phien.dang_chay, timeout=30_000)  # chờ tín hiệu sau khi đã start có thể lỡ mất


def test_nap_file_sang_kiem_tra_va_nho_nguoi_xu_ly(cua_so, mau):
    _nap(cua_so, mau)
    assert cua_so.stack.currentIndex() == S.KIEM_TRA
    assert cua_so.man[S.KIEM_TRA].bang.rowCount() == 3
    assert "Hợp lệ: 3" in cua_so.man[S.KIEM_TRA].tong.text()
    assert cua_so.phien.lo.ho_so[0].dau.can_bo and cua_so.phien.settings.ds_can_bo[0] == "ndanh.tnmt"


def test_xem_truoc_che_cccd(cua_so, mau):
    _nap(cua_so, mau)
    m = cua_so.man[S.KIEM_TRA]
    m.bang.selectRow(0)
    cccd = cua_so.phien.lo.ho_so[0].dau.nguoi[0].cccd
    assert cccd and cccd not in m.xem.toPlainText() and "•••" in m.xem.toPlainText()


def test_danh_muc_luu_xong_het_loi_ban_05(cua_so, mau):
    _nap(cua_so, mau)
    w = cua_so
    assert w.phien.lo.co_loi
    m = w.man[S.DANH_MUC]
    w.di_toi(S.DANH_MUC)
    assert m.bang.rowCount() > 0
    for r in range(m.bang.rowCount()):
        m.bang.cellWidget(r, 3).setCurrentText("Giá trị A")
    m.luu()
    assert not w.phien.lo.co_loi and w.phien.dm_path.exists()
    assert w.stack.currentIndex() == S.KIEM_TRA


def _het_loi(w):
    m = w.man[S.DANH_MUC]
    w.di_toi(S.DANH_MUC)
    for r in range(m.bang.rowCount()):
        m.bang.cellWidget(r, 3).setCurrentText("Giá trị A")
    m.luu()
    _du_so(w)


def test_chay_thu_khong_luu_roi_co_ket_qua_va_lich_su(cua_so, mau, qtbot):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    _chay(w, qtbot)
    assert w.fake.so_lan_luu == 0
    assert w.stack.currentIndex() == S.KET_QUA
    assert "Chạy thử: 3" in w.man[S.KET_QUA].tong.text()
    w.di_toi(S.LICH_SU)
    assert w.man[S.LICH_SU].bang.rowCount() == 1


def test_chay_that_phai_xac_nhan(cua_so, mau, monkeypatch):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    w.di_toi(S.CHAY)
    w.man[S.CHAY].r_that.setChecked(True)
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: False)
    w.man[S.CHAY].bat_dau()
    assert w.man[S.CHAY].worker is None and w.fake.so_lan_luu == 0


def test_mac_dinh_la_chay_thu(cua_so):
    assert cua_so.man[S.CHAY].r_thu.isChecked()


def test_lo_con_loi_khong_chay(cua_so, mau):
    _nap(cua_so, mau)
    assert cua_so.phien.lo.co_loi
    cua_so.di_toi(S.CHAY)
    assert not cua_so.man[S.CHAY].chay.isEnabled()


def test_cai_dat_tu_luu(cua_so):
    m = cua_so.man[S.CAI_DAT]
    m.chu["username"].setText("ltmung.nnmt")
    m._luu()
    assert Settings.load().username == "ltmung.nnmt"


def test_cai_dat_o_so_giu_gia_tri_cu_khi_de_trong(cua_so):
    m = cua_so.man[S.CAI_DAT]
    m.so["timeout_ms"].setText("45000")
    m._luu()
    m.so["timeout_ms"].setText("")
    m._luu()
    assert Settings.load().timeout_ms == 45000


def _chay_that(w, qtbot, monkeypatch, tra_loi):
    _het_loi(w)
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    monkeypatch.setattr(S, "hop_nhap", lambda *a, **k: tra_loi)
    w.fake.so_phat_hanh_trung = {w.phien.lo.ho_so[0].key}
    w.phien.can_chay = w.phien.lo.ho_so[:1]
    _chay(w, qtbot, that=True)
    return w.phien.store.get(w.man[S.CHAY].ho_so_chay[0].key)


def test_trung_so_thi_hoi_so_moi_va_di_tiep(cua_so, mau, qtbot, monkeypatch):
    _nap(cua_so, mau)
    bg = _chay_that(cua_so, qtbot, monkeypatch, "ab12345678")
    assert bg.trang_thai is TrangThai.THANH_CONG and cua_so.fake.so_moi_nhan == ["AB 12345678"]
    assert cua_so.fake.so_lan_luu == 1


def test_trung_so_ma_huy_thi_can_kiem_tra(cua_so, mau, qtbot, monkeypatch):
    _nap(cua_so, mau)
    bg = _chay_that(cua_so, qtbot, monkeypatch, None)
    assert bg.trang_thai is TrangThai.CAN_KIEM_TRA and "AA 1" in bg.ghi_chu


def test_gioi_han_chi_chay_dung_so_ho_so_con_lai(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    w.phien.store.mark(w.phien.lo.ho_so[0].key, TrangThai.THANH_CONG, "xong", "HS")
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    w.man[S.CHAY].gioi_han.setText("1")
    _chay(w, qtbot, that=True)
    assert w.fake.so_lan_luu == 1 and [h.key for h in w.man[S.CHAY].ho_so_chay] == [w.phien.lo.ho_so[1].key]


def test_chay_lai_khong_xoa_ho_so_da_co_ma(cua_so, mau, qtbot, monkeypatch):
    _nap(cua_so, mau)
    bg = _chay_that(cua_so, qtbot, monkeypatch, None)
    assert bg.ma_ho_so
    m = cua_so.man[S.KET_QUA]
    m.bang.selectRow(0)
    bao: list[str] = []
    monkeypatch.setattr(S, "hop_thong_bao", lambda _w, _t, chu, *a, **k: bao.append(chu))
    m.chay_lai()
    sau = cua_so.phien.store.get(bg.key)
    assert sau.trang_thai is TrangThai.CAN_KIEM_TRA and sau.ma_ho_so == bg.ma_ho_so
    assert "đã có mã" in bao[0] and cua_so.stack.currentIndex() == S.KET_QUA


def test_mo_lai_man_chay_luon_ve_chay_thu(cua_so, mau):
    w = cua_so
    _nap(w, mau)
    w.di_toi(S.CHAY)
    w.man[S.CHAY].r_that.setChecked(True)
    w.di_toi(S.LO_MOI)
    w.di_toi(S.CHAY)
    assert w.man[S.CHAY].r_thu.isChecked() and not w.man[S.CHAY].r_that.isChecked()


def test_xac_nhan_chay_that_neu_dung_so_ho_so(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    goi = []
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: goi.append((a, k)) or False)
    w.di_toi(S.CHAY)
    w.man[S.CHAY].r_that.setChecked(True)
    w.man[S.CHAY].gioi_han.setText("2")
    w.man[S.CHAY].bat_dau()
    a, k = goi[0]
    assert a[1] == "Chạy thật 2 hồ sơ?" and k["kieu"] == "chay_that" and a[4] == "Chạy thật 2 hồ sơ"
    assert w.man[S.CHAY].worker is None


def test_cot_ho_so_khong_hien_khoa_ky_thuat(cua_so, mau, qtbot):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    _chay(w, qtbot)
    o = w.man[S.KET_QUA].bang.item(0, 1)
    assert o.text().startswith("Tờ ") and "|" not in o.text() and "|thua" in o.data(Qt.ItemDataRole.UserRole)


def test_ket_qua_mac_dinh_loc_ho_so_can_xu_ly_tay(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    monkeypatch.setattr(S, "hop_nhap", lambda *a, **k: None)
    w.fake.so_phat_hanh_trung = {w.phien.lo.ho_so[1].key}
    _chay(w, qtbot, that=True)
    m = w.man[S.KET_QUA]
    hien = lambda: [r for r in range(m.bang.rowCount()) if not m.bang.isRowHidden(r)]
    assert m.bang.rowCount() == 3 and len(hien()) == 1
    assert m.bang.item(hien()[0], 1).data(Qt.ItemDataRole.UserRole) == w.phien.lo.ho_so[1].key
    m.chips["Tất cả"].click()
    assert len(hien()) == 3


def test_ket_qua_tich_chon_cung_duoc_tinh_de_chay_lai(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    bg_key = w.phien.lo.ho_so[0].key
    _chay(w, qtbot)
    m = w.man[S.KET_QUA]
    w.phien.ket_qua[bg_key] = ("Lỗi", "x", "")
    m.hien()
    m.chips["Tất cả"].click()
    r = next(r for r in range(m.bang.rowCount()) if m.bang.item(r, 1).data(Qt.ItemDataRole.UserRole) == bg_key)
    m.bang.item(r, 0).setCheckState(Qt.CheckState.Checked)
    assert m.nut_lai.isEnabled() and "1" in m.nut_lai.text()
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    m.chay_lai()
    assert [h.key for h in w.phien.can_chay] == [bg_key] and w.stack.currentIndex() == S.CHAY


def test_kiem_tra_loc_theo_the_loi(cua_so, mau):
    w = cua_so
    _nap(w, mau)
    m = w.man[S.KIEM_TRA]
    w.phien.lo.van_de = [VanDe(excel_row=w.phien.lo.ho_so[1].dau.excel_row, muc="loi", ma="BR-01", noi_dung="Thiếu người nhận")]
    m.hien()
    m.the_loi.click()
    hien = [r for r in range(m.bang.rowCount()) if not m.bang.isRowHidden(r)]
    assert len(hien) == 1 and m.bang.item(hien[0], 0).data(Qt.ItemDataRole.UserRole) == w.phien.lo.ho_so[1].key
    m.the_loi.click()
    assert not any(m.bang.isRowHidden(r) for r in range(m.bang.rowCount()))


def test_cai_dat_gia_tri_sai_bao_chua_luu(cua_so):
    m = cua_so.man[S.CAI_DAT]
    m.so["timeout_ms"].setText("abc")
    m._luu()
    assert "Chưa lưu" in m.trang_thai_luu.text() and "Thời gian chờ" in m.trang_thai_luu.text()


def test_cai_dat_dia_chi_khong_phai_https_khong_luu(cua_so):
    m = cua_so.man[S.CAI_DAT]
    m.chu["mplis_url"].setText("hye.mplis.gov.vn")
    m._luu()
    assert "Chưa lưu" in m.trang_thai_luu.text() and cua_so.phien.settings.mplis_url.startswith("https://")


def test_dai_che_do_chi_hien_o_man_chay_khi_chua_chay(cua_so, mau):
    w = cua_so
    _nap(w, mau)
    w.di_toi(S.CHAY)
    assert not w.dai.isHidden() and "CHẠY THỬ" in w.dai.chu.text()
    w.man[S.CHAY].r_that.setChecked(True)
    assert "CHẠY THẬT" in w.dai.chu.text()
    w.di_toi(S.LICH_SU)
    assert w.dai.isHidden()


def test_doi_man_co_lop_chuyen_canh_roi_tu_don(cua_so, qtbot, monkeypatch):
    monkeypatch.setattr("tiep_nhan.app.main_window.co_hieu_ung", lambda: True)
    w = cua_so
    w.show()
    qtbot.waitExposed(w)
    w.di_toi(S.LICH_SU)
    assert w.stack.currentIndex() == S.LICH_SU and w.stack.findChildren(QLabel, "chuyenMan")
    assert w.dong_nav.state() == QAbstractAnimation.State.Running
    qtbot.waitUntil(lambda: not w.stack.findChildren(QLabel, "chuyenMan") and w.y_truot is None, timeout=3_000)


def test_tat_hieu_ung_he_thong_thi_khong_chuyen_canh(cua_so, qtbot, monkeypatch):
    monkeypatch.setattr("tiep_nhan.app.main_window.co_hieu_ung", lambda: False)
    w = cua_so
    w.show()
    qtbot.waitExposed(w)
    w.di_toi(S.LICH_SU)
    assert not w.stack.findChildren(QLabel, "chuyenMan")


def test_tra_loi_sai_dang_coi_nhu_bo_qua(cua_so, mau, qtbot, monkeypatch):
    _nap(cua_so, mau)
    bg = _chay_that(cua_so, qtbot, monkeypatch, "TEST0001")
    assert bg.trang_thai is TrangThai.CAN_KIEM_TRA and cua_so.fake.so_moi_nhan == []


def _co_lich_su(w, mau, qtbot, so_lan=1):
    _nap(w, mau)
    _het_loi(w)
    for _ in range(so_lan):
        _chay(w, qtbot)


def test_xoa_mot_lo_o_lich_su_phai_xac_nhan_va_cap_nhat_ngay(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _co_lich_su(w, mau, qtbot)
    m = w.man[S.LICH_SU]
    w.di_toi(S.LICH_SU)
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: False)
    m.xoa_dong(0)
    assert m.bang.rowCount() == 1
    goi = []
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: goi.append(k) or True)
    m.xoa_dong(0)
    assert goi[0]["kieu"] == "nguy_hiem" and goi[0]["nut_huy"] == "Huỷ"
    assert m.bang.rowCount() == 0 and w.phien.store.ds_lo() == []
    assert w.phien.file is None and w.phien.lo is None  # xoá đúng lô đang mở thì về Chưa chọn file
    w.di_toi(S.LO_MOI)
    assert w.man[S.LO_MOI].trang.currentIndex() == 0 and not w.man[S.LO_MOI].tiep.isEnabled()


def test_xoa_toan_bo_lich_su(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _co_lich_su(w, mau, qtbot, so_lan=2)
    m = w.man[S.LICH_SU]
    w.di_toi(S.LICH_SU)
    assert m.bang.rowCount() == 2
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    m.xoa_het()
    assert m.bang.rowCount() == 0 and w.phien.store.ds_lo() == []


def test_xoa_trong_lo_gan_day(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _co_lich_su(w, mau, qtbot)
    m = w.man[S.LO_MOI]
    w.di_toi(S.LO_MOI)
    assert m.gan_day.count() == 1
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    m.xoa_gan_day(w.phien.store.ds_lo()[0]["id"])
    assert m.gan_day.count() == 0 and w.phien.store.ds_lo() == []


def test_dang_chay_thi_khong_xoa_duoc_lich_su(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _co_lich_su(w, mau, qtbot)
    w.phien.dang_chay = True
    try:
        m = w.man[S.LICH_SU]
        w.di_toi(S.LICH_SU)
        tat, goi_y = m.nut_xoa_het.isEnabled(), m.nut_xoa_het.toolTip()
        monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
        m.xoa_het()
        con = len(w.phien.store.ds_lo())
    finally:
        w.phien.dang_chay = False  # cửa sổ đang chạy thì không cho đóng: phải trả cờ để dọn test
    assert not tat and "đang chạy" in goi_y.lower() and con == 1


def test_danh_sach_nguoi_xu_ly_lay_tu_mplis_khi_chay_va_chon_theo_tai_khoan(cua_so, mau, qtbot):
    w = cua_so
    w.fake.danh_ba = {"a.nguyen": "Nguyễn Văn A", "b.tran": "Trần Thị B"}
    _nap(w, mau)
    _het_loi(w)
    _chay(w, qtbot)
    assert w.phien.settings.danh_ba_can_bo == {"a.nguyen": "Nguyễn Văn A", "b.tran": "Trần Thị B"}
    m = w.man[S.LO_MOI]
    w.di_toi(S.LO_MOI)
    chu = [m.can_bo.itemText(i) for i in range(m.can_bo.count())]
    assert chu[0] == "ndanh.tnmt" and "a.nguyen — Nguyễn Văn A" in chu and "b.tran — Trần Thị B" in chu
    m.can_bo.setCurrentText("b.tran — Trần Thị B")
    m._sang_kiem_tra()
    assert w.phien.can_bo == "b.tran"  # chỉ dùng tài khoản để chọn người trên MPLIS


def test_khung_chon_file_gon_mot_hang(cua_so, mau):
    m = cua_so.man[S.LO_MOI]
    cao_trong = m.vung.sizeHint().height()
    m.mo_file(mau)
    assert cao_trong <= 100 and m.vung.sizeHint().height() <= 100


def test_xoa_the_lo_gan_day_xoa_moi_lan_chay_cua_file_do(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _co_lich_su(w, mau, qtbot, so_lan=3)
    m = w.man[S.LO_MOI]
    w.di_toi(S.LO_MOI)
    assert m.gan_day.count() == 1 and len(w.phien.store.ds_lo()) == 3  # một thẻ cho cả 3 lần chạy cùng file
    goi = []
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: goi.append(a) or True)
    m.xoa_gan_day(w.phien.store.ds_lo()[0]["id"])
    assert m.gan_day.count() == 0 and w.phien.store.ds_lo() == []
    assert goi[0][2] == "" and goi[0][3] == []  # hộp xác nhận chỉ có câu hỏi ngắn



def test_chay_lai_ho_so_dang_tao_giu_trang_thai_de_bat_buoc_tra_trung(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _co_lich_su(w, mau, qtbot)
    k = w.phien.lo.ho_so[0].key
    w.phien.store.mark(k, TrangThai.DANG_TAO, "Đã bấm Lưu, chưa xác nhận")
    w.phien.ket_qua[k] = ("Lỗi", "mất mạng", "")
    m = w.man[S.KET_QUA]
    w.di_toi(S.KET_QUA)
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    m.chay_lai([k])
    assert w.phien.store.get(k).trang_thai is TrangThai.DANG_TAO and [h.key for h in w.phien.can_chay] == [k]


def test_chay_lai_mot_ho_so_chi_lay_dung_ho_so_do(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _co_lich_su(w, mau, qtbot)
    a, b = w.phien.lo.ho_so[0].key, w.phien.lo.ho_so[1].key
    w.phien.ket_qua[a] = ("Lỗi", "x", "")
    w.phien.ket_qua[b] = ("Lỗi", "y", "")
    m = w.man[S.KET_QUA]
    w.di_toi(S.KET_QUA)
    m.chips["Tất cả"].click()
    for r in range(m.bang.rowCount()):
        m.bang.item(r, 0).setCheckState(Qt.CheckState.Checked)
    monkeypatch.setattr(S, "hop_xac_nhan", lambda *a, **k: True)
    m.chay_lai([a])
    assert [h.key for h in w.phien.can_chay] == [a]


def test_dang_chay_khong_doi_duoc_file_hay_lo(cua_so, mau, qtbot, tmp_path):
    w = cua_so
    _co_lich_su(w, mau, qtbot)
    cu = w.phien.file
    w.phien.dang_chay = True
    try:
        w.man[S.LO_MOI].mo_file(tmp_path / "khac.xlsx")
        w.man[S.LO_MOI]._sang_kiem_tra()
        file_sau, kq_sau = w.phien.file, dict(w.phien.ket_qua)
    finally:
        w.phien.dang_chay = False
    assert file_sau == cu and kq_sau


def test_mo_lo_tu_lich_su_bo_danh_sach_chay_lai_cu(cua_so, mau, qtbot):
    w = cua_so
    _co_lich_su(w, mau, qtbot)
    w.phien.can_chay, w.phien.da_reset = w.phien.lo.ho_so[:1], True
    m = w.man[S.LICH_SU]
    w.di_toi(S.LICH_SU)
    m.bang.selectRow(0)
    m.mo(S.KET_QUA)
    assert w.phien.can_chay is None and w.phien.da_reset is False


def test_mo_lai_lo_tu_lich_su_dung_che_do_gom_va_sheet_da_chay(cua_so, mau, qtbot):
    from tiep_nhan.domain.gom_ho_so import CheDoGom
    w = cua_so
    m = w.man[S.LO_MOI]
    m.mo_file(mau)
    m.che_do.setCurrentIndex(m.che_do.findData(CheDoGom.THEO_MA_DAU_VAO))
    m._sang_kiem_tra()
    _du_so(w)
    _het_loi(w)
    _chay(w, qtbot)
    sheet = w.phien.sheet
    w.phien.che_do, w.phien.sheet = CheDoGom.MOI_DONG, None  # như lúc mở app lại
    ls = w.man[S.LICH_SU]
    w.di_toi(S.LICH_SU)
    ls.bang.selectRow(0)
    ls.mo(S.KET_QUA)
    assert w.phien.che_do is CheDoGom.THEO_MA_DAU_VAO and w.phien.sheet == sheet  # chạy thử không ghi trạng thái nên không có kết quả để hiện lại


def test_chon_quy_trinh_o_lo_moi_luu_vao_cai_dat(cua_so, mau):
    w = cua_so
    m = w.man[S.LO_MOI]
    assert m.quy_trinh.currentData() == "2"  # mặc định như đã chốt: từ 30 hồ sơ trở lên
    m.mo_file(mau)
    m.quy_trinh.setCurrentIndex(m.quy_trinh.findData("1"))
    m._sang_kiem_tra()
    assert w.phien.settings.quy_trinh == "1"


def test_tu_kiem_sau_khi_cai_ghi_ket_qua(cua_so, tmp_path, monkeypatch):
    import json
    from tiep_nhan.app import main_window as M
    monkeypatch.setattr(M, "_mo_chromium_an", lambda: "ok")
    ra = tmp_path / "kiem_cai.json"
    kq = M.tu_kiem(cua_so, ra)
    du_lieu = json.loads(ra.read_text(encoding="utf-8"))
    assert kq is True and du_lieu["chromium"] == "ok" and du_lieu["phien_ban"] and du_lieu["font"] == "Be Vietnam Pro"


def test_tu_kiem_bao_loi_khi_chromium_khong_chay(cua_so, tmp_path, monkeypatch):
    import json
    from tiep_nhan.app import main_window as M

    def hong():
        raise RuntimeError("không tìm thấy Chromium")

    monkeypatch.setattr(M, "_mo_chromium_an", hong)
    ra = tmp_path / "kiem_cai.json"
    assert M.tu_kiem(cua_so, ra) is False
    assert "không tìm thấy Chromium" in json.loads(ra.read_text(encoding="utf-8"))["chromium"]


def test_cai_dat_tuy_chon_chay_tren_giao_dien(cua_so):
    m = cua_so.man[S.CAI_DAT]
    assert not m.tich["chay_giao_dien"].isChecked()  # mặc định dùng API để tra cứu
    m.tich["chay_giao_dien"].setChecked(True)
    assert Settings.load().chay_giao_dien is True


def test_nap_file_trung_to_thua_thi_bao_va_loai_dong_trung(cua_so, mau, tmp_path, monkeypatch):
    import openpyxl
    wb = openpyxl.load_workbook(mau)
    ws = wb.active
    ws.cell(8, 14).value, ws.cell(8, 15).value = ws.cell(7, 14).value, ws.cell(7, 15).value  # dòng 8 trùng tờ/thửa dòng 7
    f = tmp_path / "trung.xlsx"
    wb.save(f)
    bao = []
    monkeypatch.setattr(S, "hop_thong_bao", lambda _w, tieu_de, chu, *a, **k: bao.append((tieu_de, chu)))
    cua_so.man[S.LO_MOI].mo_file(f)
    lo = cua_so.phien.lo
    assert [h.dau.excel_row for h in lo.ho_so] == [6, 7]
    assert len(bao) == 1 and "dòng 8" in bao[0][1] and "dòng 7" in bao[0][1]
    assert not [v for v in lo.van_de if v.ma == "BR-03" and v.muc == "loi"]


def test_tai_file_mau(cua_so, tmp_path, monkeypatch):
    from tiep_nhan.domain.rules import kiem_tra_file
    from tiep_nhan.infra.excel_in import read_phieu
    ra = tmp_path / "phieu_chuyen_mau.xlsx"
    monkeypatch.setattr(S.QFileDialog, "getSaveFileName", lambda *a, **k: (str(ra), ""))
    monkeypatch.setattr(S, "hop_thong_bao", lambda *a, **k: None)
    cua_so.man[S.LO_MOI].nut_mau.click()
    rows, van_de = kiem_tra_file(read_phieu(ra))
    assert len(rows) == 1 and not [v for v in van_de if v.muc == "loi"]
    assert all(r.thua.so_to == 999 for r in rows)  # tờ giả: không thể tạo hồ sơ thật từ file mẫu
