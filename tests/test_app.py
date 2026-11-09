"""Giao diện chạy không màn hình, MPLIS giả: không mở trình duyệt, không cần mạng."""
from __future__ import annotations

import os
from contextlib import nullcontext

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from tiep_nhan.app import screens as S
from tiep_nhan.app.main_window import MainWindow
from tiep_nhan.core.state import StateStore, TrangThai
from tiep_nhan.domain.danh_muc import DanhMuc
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


def _chay(w, qtbot):
    m = w.man[S.CHAY]
    w.di_toi(S.CHAY)
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
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
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
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: tra_loi)
    w.fake.so_phat_hanh_trung = {w.phien.lo.ho_so[0].key}
    w.phien.can_chay = w.phien.lo.ho_so[:1]
    w.man[S.CHAY].r_that.setChecked(True)
    _chay(w, qtbot)
    return w.phien.store.get(w.man[S.CHAY].ho_so_chay[0].key)


def test_trung_so_thi_hoi_so_moi_va_di_tiep(cua_so, mau, qtbot, monkeypatch):
    _nap(cua_so, mau)
    bg = _chay_that(cua_so, qtbot, monkeypatch, ("AB 9", True))
    assert bg.trang_thai is TrangThai.THANH_CONG and cua_so.fake.so_moi_nhan == ["AB 9"]
    assert cua_so.fake.so_lan_luu == 1


def test_trung_so_ma_huy_thi_can_kiem_tra(cua_so, mau, qtbot, monkeypatch):
    _nap(cua_so, mau)
    bg = _chay_that(cua_so, qtbot, monkeypatch, ("", False))
    assert bg.trang_thai is TrangThai.CAN_KIEM_TRA and "AA 1" in bg.ghi_chu


def test_gioi_han_chi_chay_dung_so_ho_so_con_lai(cua_so, mau, qtbot, monkeypatch):
    w = cua_so
    _nap(w, mau)
    _het_loi(w)
    w.phien.store.mark(w.phien.lo.ho_so[0].key, TrangThai.THANH_CONG, "xong", "HS")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w.man[S.CHAY].r_that.setChecked(True)
    w.man[S.CHAY].gioi_han.setText("1")
    _chay(w, qtbot)
    assert w.fake.so_lan_luu == 1 and [h.key for h in w.man[S.CHAY].ho_so_chay] == [w.phien.lo.ho_so[1].key]


def test_chay_lai_khong_xoa_ho_so_da_co_ma(cua_so, mau, qtbot, monkeypatch):
    _nap(cua_so, mau)
    bg = _chay_that(cua_so, qtbot, monkeypatch, ("", False))
    assert bg.ma_ho_so
    m = cua_so.man[S.KET_QUA]
    m.bang.selectRow(0)
    bao: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda _w, _t, chu: bao.append(chu))
    m.chay_lai()
    sau = cua_so.phien.store.get(bg.key)
    assert sau.trang_thai is TrangThai.CAN_KIEM_TRA and sau.ma_ho_so == bg.ma_ho_so
    assert "đã có mã" in bao[0] and cua_so.stack.currentIndex() == S.KET_QUA
