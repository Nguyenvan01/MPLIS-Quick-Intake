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
    bg = _chay_that(cua_so, qtbot, monkeypatch, "AB 9")
    assert bg.trang_thai is TrangThai.THANH_CONG and cua_so.fake.so_moi_nhan == ["AB 9"]
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
