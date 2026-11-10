"""Cửa sổ chính: thanh điều hướng, dải chế độ và các màn hình trong app/screens.py."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPointF, QRect, QRectF, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QCloseEvent, QColor, QFont, QFontInfo, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QStyle,
                               QStyledItemDelegate, QVBoxLayout, QWidget)

from .. import __version__
from . import screens as S
from .giao_dien import (NEN_CHON, NEN_RE, TRANG, CHE_DO, CHU, CHU_NHAN, CHU_PHU, NHAN, TRANG_THAI, VIEN, VIEN_O, VONG_FOCUS, DaiCheDo, The, _font, _font_tieu_de,
                        ap_giao_dien, chuyen_canh, co_hieu_ung, hop_thong_bao, nap_font, ve_anh, ve_logo)
from .screens import MAN_HINH, Phien, phien_mac_dinh

SO_BUOC = 5
TIEU_DE = f"Thêm mới nhanh hồ sơ tiếp nhận MPLIS — v{__version__}"
DAU_CHAY_THAT = "● CHẠY THẬT – "


class _DelegateNav(QStyledItemDelegate):
    """Vẽ mốc tròn, chữ và huy hiệu của từng mục."""
    CAO, KE = 44, 18  # chiều cao mục; khoảng chừa cho đường kẻ trước mục Lịch sử

    def __init__(self, cua_so: "MainWindow"):
        super().__init__(cua_so)
        self.w = cua_so

    def sizeHint(self, o, i) -> QSize:
        return QSize(0, self.CAO + (self.KE if i.row() == SO_BUOC else 0))

    def _ve_moc(self, p: QPainter, tam: QPointF, so: int, trang_thai: str) -> None:
        if trang_thai == "xong":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(NHAN))
            p.drawEllipse(tam, 11, 11)
            p.drawPixmap(QRectF(tam.x() - 7, tam.y() - 7, 14, 14), ve_anh("xong", TRANG, 14), QRectF(0, 0, 28, 28))
            return
        mo = trang_thai == "mo"
        p.setPen(QPen(QColor(NHAN if mo else VIEN_O), 2 if mo else 1.5))
        p.setBrush(QColor(TRANG))
        p.drawEllipse(tam, 10, 10)
        p.setPen(QColor(NHAN if mo else CHU_NHAN))
        p.setFont(_font(12, QFont.Weight.DemiBold))
        p.drawText(QRectF(tam.x() - 11, tam.y() - 11, 22, 22), Qt.AlignmentFlag.AlignCenter, str(so))

    def paint(self, p: QPainter, o, i) -> None:
        r = i.row()
        khung = QRect(o.rect)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if r == SO_BUOC:
            y = khung.y() + self.KE // 2
            p.setPen(QPen(QColor(VIEN), 1))
            p.drawLine(khung.x() + 8, y, khung.right() - 8, y)
            khung.setTop(khung.y() + self.KE)
        khung = khung.adjusted(0, 2, 0, -2)
        chon = bool(o.state & QStyle.StateFlag.State_Selected)
        p.setPen(Qt.PenStyle.NoPen)
        if self.w.y_truot is not None:  # đang trượt: mỗi dòng vẽ phần ô chọn đi qua mình, viewport cắt theo dòng
            p.setClipRect(o.rect)
            p.setBrush(QColor(NEN_CHON))
            p.drawRoundedRect(QRectF(khung.x(), self.w.y_truot + 2, khung.width(), self.CAO - 4), 10, 10)
            p.setClipping(False)
        elif chon:
            p.setBrush(QColor(NEN_CHON))
            p.drawRoundedRect(QRectF(khung), 10, 10)
        elif o.state & QStyle.StateFlag.State_MouseOver:
            p.setBrush(QColor(NEN_RE))
            p.drawRoundedRect(QRectF(khung), 10, 10)
        if o.state & QStyle.StateFlag.State_HasFocus and o.state & QStyle.StateFlag.State_KeyboardFocusChange:
            p.setPen(QPen(QColor(VONG_FOCUS), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(khung).adjusted(1, 1, -1, -1), 10, 10)
        tam = QPointF(khung.x() + 21, khung.center().y() + 0.5)
        if r < SO_BUOC:
            self._ve_moc(p, tam, r + 1, "mo" if chon else self.w.trang_thai_buoc[r])
        else:
            mau = NHAN if chon else CHU_PHU
            p.drawPixmap(QRectF(tam.x() - 9, tam.y() - 9, 18, 18), ve_anh(("dong_ho", "cai_dat")[r - SO_BUOC], mau, 18), QRectF(0, 0, 36, 36))
        huy_hieu = self.w.huy_hieu.get(r)
        phai = khung.right() - 8
        if huy_hieu:
            chu, nen, mau = huy_hieu
            p.setFont(_font(12, QFont.Weight.DemiBold))
            rong = p.fontMetrics().horizontalAdvance(chu) + 14
            o_hh = QRectF(phai - rong, khung.center().y() - 9, rong, 18)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(nen))
            p.drawRoundedRect(o_hh, 9, 9)
            p.setPen(QColor(mau))
            p.drawText(o_hh, Qt.AlignmentFlag.AlignCenter, chu)
            phai -= int(rong) + 6
        p.setFont(_font(14, QFont.Weight.DemiBold if chon else QFont.Weight.Normal))
        p.setPen(QColor(NHAN if chon else CHU))
        chu_r = QRect(khung.x() + 42, khung.y(), phai - khung.x() - 42, khung.height())
        p.drawText(chu_r, Qt.AlignmentFlag.AlignVCenter, p.fontMetrics().elidedText(i.data(), Qt.TextElideMode.ElideRight, chu_r.width()))
        p.restore()


class MainWindow(QMainWindow):
    def __init__(self, phien: Phien | None = None) -> None:
        super().__init__()
        self.setWindowTitle(TIEU_DE)
        self.setMinimumSize(1100, 700)
        self.resize(1280, 820)
        self.phien = phien or phien_mac_dinh()
        self.trang_thai_buoc = ["chua"] * SO_BUOC
        self.huy_hieu: dict[int, tuple[str, str, str]] = {}
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setItemDelegate(_DelegateNav(self))
        self.nav.setMouseTracking(True)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stack = QStackedWidget()
        self.man = [lop(self.phien, self.di_toi) for _, lop in MAN_HINH]
        for (ten, _), m in zip(MAN_HINH, self.man):
            self.nav.addItem(QListWidgetItem(ten))
            self.stack.addWidget(m)
            m.doi.connect(self._lam_moi)
        self.nav.currentRowChanged.connect(self._doi_man)
        self.y_truot: float | None = None  # vị trí ô chọn trên thanh trái trong lúc trượt; None khi đứng yên
        self.dong_nav = QVariantAnimation(self, duration=180, easingCurve=QEasingCurve.Type.OutCubic)
        self.dong_nav.valueChanged.connect(self._truot)
        self.dong_nav.finished.connect(lambda: self._truot(None))
        self.dai = DaiCheDo()
        phai = QVBoxLayout()
        phai.setContentsMargins(0, 0, 0, 0)
        phai.setSpacing(0)
        phai.addWidget(self.dai)
        phai.addWidget(self.stack, 1)
        root = QWidget()
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._thanh_trai())
        lay.addLayout(phai, 1)
        self.setCentralWidget(root)
        self.nav.setCurrentRow(0)
        for i in range(len(self.man)):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self).activated.connect(lambda i=i: self.di_toi(i))
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(lambda: self.di_toi(S.CAI_DAT))
        self._lam_moi()

    def _thanh_trai(self) -> QWidget:
        khung = QWidget()
        khung.setObjectName("khungNav")
        khung.setFixedWidth(232)
        lay = QVBoxLayout(khung)
        lay.setContentsMargins(8, 20, 8, 2)
        lay.setSpacing(0)
        logo = QLabel()
        logo.setPixmap(ve_logo(34))
        ten = QLabel("Tiếp nhận hồ sơ")
        ten.setFont(_font_tieu_de(14))
        cot = QVBoxLayout()
        cot.setSpacing(0)
        cot.addWidget(ten)
        hieu = QHBoxLayout()
        hieu.setContentsMargins(4, 0, 0, 16)
        hieu.setSpacing(10)
        hieu.addWidget(logo)
        hieu.addLayout(cot, 1)
        nhom = QLabel("CÁC BƯỚC CỦA LÔ")
        nhom.setObjectName("nhanNhom")
        f = _font(12, QFont.Weight.DemiBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        nhom.setFont(f)
        nhom.setContentsMargins(8, 0, 0, 6)
        self.lo_tieu_de, self.lo_chi_tiet = QLabel(), QLabel()
        self.lo_tieu_de.setObjectName("nhanNhom")
        self.lo_tieu_de.setFont(_font(12, QFont.Weight.DemiBold))
        self.lo_chi_tiet.setObjectName("phu")
        self.lo_chi_tiet.setFont(_font(12))
        self.lo_chi_tiet.setWordWrap(True)
        self.the_lo = The(self.lo_tieu_de, self.lo_chi_tiet, dem=10, bong=False)
        self.the_lo.layout().setSpacing(2)
        lay.addLayout(hieu)
        lay.addWidget(nhom)
        lay.addWidget(self.nav, 1)
        lay.addWidget(self.the_lo)
        return khung

    def _lam_moi(self) -> None:
        """Vẽ lại mọi phần của cửa sổ phụ thuộc trạng thái lô: mốc, huy hiệu, dải chế độ, thẻ đáy."""
        p = self.phien
        lo = p.lo
        thieu = p.dm.chua_anh_xa(lo.ho_so) if lo else {}
        self.trang_thai_buoc = ["xong" if lo else "chua", "xong" if lo and not lo.co_loi else "chua", "xong" if lo and not thieu else "chua",
                                "xong" if p.ket_qua and not p.dang_chay else "chua", "chua"]
        hh: dict[int, tuple[str, str, str]] = {}
        so_loi = sum(v.muc == "loi" for v in lo.van_de) if lo else 0
        do, cam = TRANG_THAI["Lỗi"], TRANG_THAI["Cần kiểm tra"]
        if so_loi:
            hh[1] = (f"{so_loi} lỗi", do[1], do[0])
        if thieu:
            hh[2] = (f"còn {len(thieu)}", cam[1], cam[0])
        if p.dang_chay and p.tien_do and p.che_do_chay:
            cd = CHE_DO[p.che_do_chay]
            hh[3] = (f"{p.tien_do[0]}/{p.tien_do[1]}", cd["nen_nhan"], cd["chu_nhan"])
        tay = sum(1 for v in p.ket_qua.values() if v[0] in S.CAN_XU_LY)
        if tay:
            hh[4] = (f"{tay} cần xử lý", cam[1], cam[0])
        self.huy_hieu = hh
        self.nav.viewport().update()
        dang_o_chay = self.stack.currentIndex() == S.CHAY
        self.dai.dat(p.che_do_chay or (self.man[S.CHAY].che_do_chon() if dang_o_chay else None))
        self.setWindowTitle((DAU_CHAY_THAT if p.che_do_chay == "that" else "") + TIEU_DE)
        if p.dang_chay and p.che_do_chay:
            cd = CHE_DO[p.che_do_chay]
            self.lo_tieu_de.setText("Đang ở chế độ")
            self.lo_chi_tiet.setText(f'<b style="color:{cd["chu"]}">{cd["ten"]}</b>')
            self.the_lo.dat(vien=cd["chu"], day=2)
        else:
            self.lo_tieu_de.setText("Lô đang mở")
            che_do = "gộp theo mã đầu vào" if p.che_do.value != "moi_dong" else "mỗi dòng một hồ sơ"
            self.lo_chi_tiet.setText(f"{p.file.name}<br>{len(lo.ho_so)} hồ sơ · {che_do}" if p.file and lo else "Chưa chọn file")
            self.the_lo.dat(vien=VIEN, day=1)

    def di_toi(self, i: int) -> None:
        self.nav.setCurrentRow(i)
        self.man[i].hien()  # gọi lại cả khi đang ở sẵn màn đó, vì dữ liệu lô đã đổi
        self._lam_moi()

    def _y_muc(self, i: int) -> float:
        return self.nav.visualItemRect(self.nav.item(i)).y() + (_DelegateNav.KE if i == SO_BUOC else 0)

    def _truot(self, y: float | None) -> None:
        self.y_truot = y
        self.nav.viewport().update()

    def _doi_man(self, i: int) -> None:
        cu = self.stack.currentIndex()
        hieu_ung = self.isVisible() and cu != i and co_hieu_ung()
        anh_cu = self.stack.currentWidget().grab() if hieu_ung else None
        self.stack.setCurrentIndex(i)
        self.man[i].hien()
        self._lam_moi()
        if hieu_ung:
            chuyen_canh(self.stack, anh_cu)
            self.dong_nav.stop()
            self.dong_nav.setStartValue(float(self._y_muc(cu)))
            self.dong_nav.setEndValue(float(self._y_muc(i)))
            self.dong_nav.start()

    def closeEvent(self, e: QCloseEvent) -> None:
        if self.phien.dang_chay:  # đóng QThread đang chạy làm hỏng ứng dụng và có thể ngắt giữa lúc ghi
            x, y = self.phien.tien_do or (0, 0)
            hop_thong_bao(self, "Đang chạy", f"Tool đang chạy hồ sơ {x}/{y}. Bấm Dừng sau hồ sơ này và chờ xong rồi đóng.", "canh_bao")
            e.ignore()
        else:
            e.accept()


def _mo_chromium_an() -> str:
    """Mở Chromium đi kèm bản cài ở chế độ ẩn rồi đóng: xác nhận không phải cài thêm trình duyệt."""
    if getattr(sys, "frozen", False):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        trang = b.new_page()
        trang.set_content("<p>ok</p>")
        chu = trang.inner_text("p")
        b.close()
    return chu


def tu_kiem(w: MainWindow, ra: Path) -> bool:
    """Chế độ tự kiểm sau khi cài (biến môi trường NHAP_PHIEU_KIEM_CAI): ghi kết quả ra file để máy kiểm tra đọc."""
    try:
        chromium = _mo_chromium_an()
    except Exception as e:  # noqa: BLE001 — ghi lỗi ra file thay vì làm app sập
        chromium = f"{type(e).__name__}: {e}"[:300]
    nap_font()
    kq = {"phien_ban": __version__, "cua_so": w.isVisible(), "font": QFontInfo(_font(14)).family(), "chromium": chromium}
    ra.write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
    return chromium == "ok"


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    ap_giao_dien(app)
    w = MainWindow()
    w.show()
    if duong := os.environ.get("NHAP_PHIEU_KIEM_CAI"):
        QTimer.singleShot(1500, lambda: app.exit(0 if tu_kiem(w, Path(duong)) else 1))
    return app.exec()
