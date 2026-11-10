"""Thành phần dùng chung của giao diện: định dạng dữ liệu, che CCCD, hộp thoại an toàn."""
from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton

from tiep_nhan.app import giao_dien as G


@pytest.mark.parametrize("khoa, mong", [
    ("AD7-64/VHOCP3/HĐMBNO|to3|thua3364", "Tờ 3, thửa 3364"),
    ("H31.36-260316-0024|to59|thua3904", "Tờ 59, thửa 3904"),
    ("to3|thua3547", "Tờ 3, thửa 3547"),
    ("khong-co-to-thua", "khong-co-to-thua"),
])
def test_ten_ho_so(khoa, mong):
    assert G.ten_ho_so(khoa) == mong


def test_rut_gon_thay_duong_dan_anh():
    ngan, day = G.rut_gon_ghi_chu("Điền xong, không lưu. Ảnh: C:/Users/a b/shots/H31|to3|thua1.png")
    assert ngan == "Điền xong, không lưu. Có ảnh form"
    assert "C:/Users/a b/shots" in day


def test_rut_gon_thay_duong_dan_trace():
    assert G.rut_gon_ghi_chu("RuntimeError: x · trace: /Users/a/traces/t 1.zip")[0] == "RuntimeError: x · Có trace"


def test_rut_gon_che_cccd_ca_ban_ngan_va_tooltip():
    ngan, day = G.rut_gon_ghi_chu("Không thấy 001234567890 trên trang")
    assert ngan == day == "Không thấy 0012•••890 trên trang"


def test_rut_gon_giu_ma_ho_so_16_so():
    assert "9999112026000001" in G.rut_gon_ghi_chu("Đã có mã 9999112026000001")[0]


def test_tep_trong_ghi_chu_lay_duong_dan_goc():
    assert G.tep_trong_ghi_chu("Xong. Ảnh: /a/b c.png · trace: /a/t.zip") == ("/a/b c.png", "/a/t.zip")
    assert G.tep_trong_ghi_chu("Không có tệp") == (None, None)


def test_ngay_gio():
    assert G.ngay_gio("2026-11-08T15:44:08", hom_nay=date(2026, 11, 9)) == "08/11/2026 15:44"
    assert G.ngay_gio("2026-11-09T15:44:08", hom_nay=date(2026, 11, 9)) == "Hôm nay 15:44"


@pytest.mark.parametrize("tu_khoa, mong", [("3549", True), ("thua3549", True), ("thửa 3549", True), ("3550", False), ("", True)])
def test_khop_tim(tu_khoa, mong):
    assert G.khop_tim(tu_khoa, "Tờ 3, thửa 3549", "NGUYỄN THỊ AN") is mong


def test_khop_tim_khong_phan_biet_dau():
    assert G.khop_tim("nguyen thi", "Tờ 3, thửa 3549", "NGUYỄN THỊ AN")


@pytest.mark.parametrize("chu, mau", [("Lỗi chặn · 5 cảnh báo", "Lỗi"), ("1 cảnh báo", "Cần kiểm tra"), ("Tốt", "Thành công"), ("Thành công", "Thành công")])
def test_mau_nhan_theo_noi_dung(chu, mau):
    assert G.mau_nhan(chu) == G.TRANG_THAI[mau]


def _sau(ham):
    QTimer.singleShot(30, ham)


def test_hop_xac_nhan_enter_la_quay_lai(qtbot):
    kq = {}

    def bam():
        d = QApplication.activeModalWidget()
        kq["mac_dinh"] = [b.text() for b in d.findChildren(QPushButton) if b.isDefault()]
        QTest.keyClick(d, Qt.Key.Key_Return)

    _sau(bam)
    assert G.hop_xac_nhan(None, "Chạy thật 3 hồ sơ?", "Mô tả", [("File", "a.xlsx")], "Chạy thật 3 hồ sơ", kieu="chay_that") is False
    assert kq["mac_dinh"] == ["Quay lại"]


def test_hop_xac_nhan_bam_dong_y(qtbot):
    def bam():
        d = QApplication.activeModalWidget()
        next(b for b in d.findChildren(QPushButton) if b.text() == "Xóa phiên").click()

    _sau(bam)
    assert G.hop_xac_nhan(None, "Xóa?", "", [], "Xóa phiên", kieu="nguy_hiem") is True


def test_hop_nhap_chua_go_thi_khong_dong_y_duoc_va_tra_so_da_cat_khoang_trang(qtbot):
    kq = {}

    def bam():
        d = QApplication.activeModalWidget()
        nut = next(b for b in d.findChildren(QPushButton) if b.text() == "Dùng số mới")
        kq["luc_trong"] = nut.isEnabled()
        d.findChild(QLineEdit).setText("  AB 123 ")
        nut.click()

    _sau(bam)
    assert G.hop_nhap(None, "Trùng", "Mô tả", "Số mới", nut_dong_y="Dùng số mới") == "AB 123"
    assert kq["luc_trong"] is False


def test_hop_nhap_bo_qua_tra_none(qtbot):
    def bam():
        d = QApplication.activeModalWidget()
        next(b for b in d.findChildren(QPushButton) if b.text() == "Bỏ qua").click()

    _sau(bam)
    assert G.hop_nhap(None, "Trùng", "", "Số mới") is None


def test_hop_nhap_luon_noi_tren_cung(qtbot):
    kq = {}

    def bam():
        d = QApplication.activeModalWidget()
        kq["co"] = bool(d.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        d.reject()

    _sau(bam)
    G.hop_nhap(None, "Trùng", "", "Số mới")
    assert kq["co"] is True


@pytest.mark.parametrize("che_do", ["thu", "that"])
def test_dai_che_do_hien_dung_che_do_va_an_khi_khong_chay(qtbot, che_do):
    d = G.DaiCheDo()
    qtbot.addWidget(d)
    d.dat(che_do)
    assert not d.isHidden() and ("CHẠY THẬT" if che_do == "that" else "CHẠY THỬ") in d.chu.text()
    d.dat(None)
    assert d.isHidden()


TEN_ICON = {"xong", "canh_bao", "loi", "dong_ho", "cai_dat", "thu_muc", "anh", "trace", "tai_xuong", "chay", "tam_dung", "tim", "doc_lai",
            "excel", "thong_tin", "co_le", "xuong", "xoa"}


def test_bo_icon_lay_dung_hinh_lucide():
    from tiep_nhan.app.icon_lucide import ICON
    assert set(ICON) == TEN_ICON
    assert "M20 6 9 17l-5-5" in ICON["xong"]


@pytest.mark.parametrize("ten", sorted(TEN_ICON))
def test_icon_ve_ra_net_dung_mau(qtbot, ten):
    anh = G.ve_anh(ten, "#FF0000", 24).toImage()
    mau = [anh.pixelColor(x, y) for x in range(anh.width()) for y in range(anh.height())]
    assert any(c.alpha() > 200 and c.red() > 200 and c.green() < 60 for c in mau)


def test_icon_khong_co_trong_bo_thi_bao_loi():
    with pytest.raises(ValueError):
        G.ve_anh("khong_co", "#000000")


def test_hop_xac_nhan_mo_dan_den_day_du(qtbot, monkeypatch):
    monkeypatch.setattr(G, "co_hieu_ung", lambda: True)
    kq = {}

    def bam():
        d = QApplication.activeModalWidget()
        kq["do_mo"] = d.windowOpacity()
        d.reject()

    QTimer.singleShot(400, bam)
    G.hop_xac_nhan(None, "T", "", [], "Đồng ý")
    assert kq["do_mo"] == 1.0


def test_hop_nhap_khong_mo_dan_de_nguoi_dung_thay_ngay(qtbot, monkeypatch):
    monkeypatch.setattr(G, "co_hieu_ung", lambda: True)
    kq = {}

    def bam():
        d = QApplication.activeModalWidget()
        kq["do_mo"] = d.windowOpacity()
        d.reject()

    _sau(bam)
    G.hop_nhap(None, "Trùng", "", "Số mới")
    assert kq["do_mo"] == 1.0


def test_dat_tien_do_co_hieu_ung_den_dung_gia_tri(qtbot, monkeypatch):
    from PySide6.QtWidgets import QProgressBar
    monkeypatch.setattr(G, "co_hieu_ung", lambda: True)
    t = QProgressBar()
    qtbot.addWidget(t)
    t.setRange(0, 3)
    t.setValue(0)
    G.dat_tien_do(t, 2)
    qtbot.waitUntil(lambda: t.value() == 2, timeout=2_000)


def test_hop_nhap_so_sai_dang_thi_khong_dong_y_duoc_va_bao_do(qtbot):
    kq = {}

    def bam():
        d = QApplication.activeModalWidget()
        o = d.findChild(QLineEdit)
        nut = next(b for b in d.findChildren(QPushButton) if b.text() == "Dùng số mới")
        o.setText("TEST0001")
        kq["sai"] = (nut.isEnabled(), any(x.text() == "Sai dạng" and x.isVisible() for x in d.findChildren(QLabel)))
        o.setText("aa12345678")
        kq["dung"] = (nut.isEnabled(), any(x.text() == "Sai dạng" and x.isVisible() for x in d.findChildren(QLabel)))
        nut.click()

    _sau(bam)
    tra = G.hop_nhap(None, "Trùng", "", "Số mới", nut_dong_y="Dùng số mới", hop_le=lambda s: s.lower() == "aa12345678", bao_sai="Sai dạng")
    assert kq == {"sai": (False, True), "dung": (True, False)} and tra == "aa12345678"


def test_hop_xac_nhan_doi_ten_nut_huy_va_van_la_mac_dinh(qtbot):
    kq = {}

    def bam():
        d = QApplication.activeModalWidget()
        kq["mac_dinh"] = [b.text() for b in d.findChildren(QPushButton) if b.isDefault()]
        QTest.keyClick(d, Qt.Key.Key_Return)

    _sau(bam)
    assert G.hop_xac_nhan(None, "Xoá?", "", [], "Xoá", kieu="nguy_hiem", nut_huy="Huỷ") is False
    assert kq["mac_dinh"] == ["Huỷ"]


def _do_sang(mau: str) -> float:
    def kenh(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(mau[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * kenh(r) + 0.7152 * kenh(g) + 0.0722 * kenh(b)


def tuong_phan(chu: str, nen: str) -> float:
    a, b = sorted((_do_sang(chu), _do_sang(nen)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def cap_chu_nen() -> list[tuple[str, str, str]]:
    cap = [("Chữ chính / nền trang", G.CHU, G.NEN_APP), ("Chữ chính / card", G.CHU, G.NEN_THE),
           ("Chữ phụ / nền trang", G.CHU_PHU, G.NEN_APP), ("Chữ phụ / card", G.CHU_PHU, G.NEN_THE),
           ("Chữ mờ / nền trang", G.CHU_NHAN, G.NEN_APP), ("Chữ mờ / card", G.CHU_NHAN, G.NEN_THE),
           ("Nút chính", G.TRANG, G.NUT_CHINH), ("Nút chính khi rê", G.TRANG, G.NUT_CHINH_RE),
           ("Nút chính bị tắt", G.NUT_TAT_CHU, G.NUT_TAT_NEN), ("Nút phụ bị tắt / nền trang", G.CHU_NHAN, G.NEN_APP),
           ("Nút phụ bị tắt / card", G.CHU_NHAN, G.NEN_THE), ("Link / nền trang", G.LIEN_KET, G.NEN_APP),
           ("Link / card", G.LIEN_KET, G.NEN_THE), ("Dòng chọn trong card", G.CHU, G.CHON_THE),
           ("Mục chọn dropdown", G.CHU, G.NEN_CHON), ("Chip đang chọn", G.TRANG, G.NUT_CHINH), ("Nút chính khi bấm", G.TRANG, G.NUT_CHINH_BAM),
           ("Mục đang chọn (chữ xanh)", G.NHAN, G.NEN_CHON), ("Chữ xanh / nền trang", G.NHAN, G.NEN_APP),
           ("Phân đoạn chưa chọn", G.CHU_PHU, G.NEN_PHAN_DOAN), ("Tooltip", G.TRANG, G.CHU)]
    cap += [(f"Badge {ten}", chu, nen) for ten, (chu, nen, _) in G.TRANG_THAI.items()]
    cap += [(f"Badge/dải {cd['ten']}", cd["chu_nhan"], cd["nen_nhan"]) for cd in G.CHE_DO.values()]
    cap += [(f"Thẻ {cd['ten']} đang chọn", cd["chu"], cd["nen_nhat"]) for cd in G.CHE_DO.values()]
    return cap


@pytest.mark.parametrize("ten, chu, nen", cap_chu_nen())
def test_tuong_phan_chu_tren_nen_dat_wcag_aa(ten, chu, nen):
    assert tuong_phan(chu, nen) >= 4.5, f"{ten}: {tuong_phan(chu, nen):.2f}"


def test_nap_duoc_font_trong_assets(qtbot):
    assert {"Host Grotesk", "Instrument Sans"} <= set(G.nap_font())
