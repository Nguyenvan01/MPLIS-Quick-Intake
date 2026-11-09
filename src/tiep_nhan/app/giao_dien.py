"""Hệ giao diện: nền trắng, thẻ có bóng nhiều lớp, ô nhập bo 12px, nút chính có độ nâng."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLayout,
                               QPushButton, QVBoxLayout, QWidget)

from ..infra.config import sub_dir

TRANG, VIEN, CHU, CHU_PHU, NHAN = "#FFFFFF", "#E5E7EB", "#101828", "#475467", "#0B5D56"
NHAT = "#E7F2F0"  # nền dòng đang chọn và mục đang mở
BONG = 14         # khoảng chừa quanh thẻ để vẽ bóng, đồng thời là khoảng trắng giữa các thẻ


def _font(co: int, dam: QFont.Weight = QFont.Weight.Normal, gian: float = 0.1) -> QFont:
    f = QFont()
    f.setFamilies(["Segoe UI", ".AppleSystemUIFont", "Helvetica Neue", "Arial"])
    f.setPixelSize(co)
    f.setWeight(dam)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, gian)
    return f


QSS = f"""
QWidget {{ background: {TRANG}; color: {CHU}; }}
QLabel#moTa, QLabel#phu {{ color: {CHU_PHU}; }}
QListWidget#nav {{ border: none; border-right: 1px solid {VIEN}; padding: 28px 14px; outline: 0; }}
QListWidget#nav::item {{ padding-left: 14px; border-radius: 12px; color: {CHU_PHU}; }}
QListWidget#nav::item:hover {{ color: {CHU}; background: #F7F8FA; }}
QListWidget#nav::item:selected {{ color: {NHAN}; background: {NHAT}; font-weight: 600; }}
QLineEdit, QComboBox {{
    border: 1px solid {VIEN}; border-radius: 12px; padding: 9px 12px; selection-background-color: {NHAN}; }}
QLineEdit:hover, QComboBox:hover {{ border-color: #98A2B3; }}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {NHAN}; padding: 8px 11px; }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{ image: url("MUI_TEN"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ border: 1px solid {VIEN}; selection-background-color: {NHAT}; selection-color: {CHU}; outline: 0; }}
QPushButton {{ border: 1px solid {VIEN}; border-radius: 12px; padding: 10px 18px; font-weight: 500; }}
QPushButton:hover {{ border-color: #98A2B3; background: #F7F8FA; }}
QPushButton:pressed {{ background: {NHAT}; }}
QPushButton:focus {{ border: 2px solid {NHAN}; padding: 9px 17px; }}
QPushButton:disabled {{ color: #98A2B3; }}
QPushButton#chinh {{ background: {NHAN}; color: {TRANG}; border: none; padding: 11px 26px; font-weight: 600; }}
QPushButton#chinh:hover {{ background: #0A6E65; }}
QPushButton#chinh:pressed {{ background: #084A44; }}
QPushButton#chinh:focus {{ border: 2px solid {CHU}; padding: 9px 24px; }}
QPushButton#chinh:disabled {{ background: #D0D5DD; color: {TRANG}; }}
QTableWidget, QTreeWidget, QListWidget, QTextBrowser, QPlainTextEdit {{ border: none; outline: 0; }}
QTableWidget::item, QTreeWidget::item {{ border-bottom: 1px solid #F2F4F7; padding: 2px 10px; }}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{ background: {NHAT}; color: {CHU}; }}
QHeaderView::section {{ background: {TRANG}; border: none; border-bottom: 1px solid {VIEN}; padding: 10px;
    font-weight: 700; color: {CHU_PHU}; }}
QProgressBar {{ border: none; background: #F2F4F7; border-radius: 5px; max-height: 10px; color: transparent; }}
QProgressBar::chunk {{ background: {NHAN}; border-radius: 5px; }}
QScrollBar:vertical {{ width: 10px; background: {TRANG}; }}
QScrollBar:horizontal {{ height: 10px; background: {TRANG}; }}
QScrollBar::handle {{ background: #D0D5DD; border-radius: 5px; min-height: 28px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}
"""


def _mui_ten() -> str:
    """QSS chỉ nhận ảnh từ file: vẽ một lần vào thư mục dữ liệu, khỏi phải đóng gói thêm tài nguyên."""
    path = sub_dir("giao_dien") / "mui_ten.png"
    pm = QPixmap(24, 24)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(CHU_PHU), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPolyline([QPoint(5, 9), QPoint(12, 16), QPoint(19, 9)])
    p.end()
    pm.save(str(path))
    return path.as_posix()


def ap_giao_dien(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(_font(14))
    pal = QPalette()
    for vai, mau in ((QPalette.ColorRole.Window, TRANG), (QPalette.ColorRole.Base, TRANG), (QPalette.ColorRole.Button, TRANG),
                     (QPalette.ColorRole.AlternateBase, TRANG), (QPalette.ColorRole.Text, CHU), (QPalette.ColorRole.WindowText, CHU),
                     (QPalette.ColorRole.ButtonText, CHU), (QPalette.ColorRole.Highlight, NHAN),
                     (QPalette.ColorRole.HighlightedText, TRANG)):
        pal.setColor(vai, QColor(mau))
    app.setPalette(pal)
    app.setStyleSheet(QSS.replace("MUI_TEN", _mui_ten()))


class The(QFrame):
    """Thẻ nội dung. Tự vẽ bóng vì QGraphicsDropShadowEffect chỉ có một lớp và làm bảng dài bị giật."""
    LOP = ((1, 1, 9), (2, 4, 2), (6, 10, 1))  # (lệch xuống, độ loang, độ đậm của mỗi vòng)

    def __init__(self, *noi_dung: QWidget | QLayout, dem: int = 18):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(BONG + dem, BONG + dem, BONG + dem, BONG + dem)
        lay.setSpacing(10)
        for x in noi_dung:
            lay.addLayout(x) if isinstance(x, QLayout) else lay.addWidget(x)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(BONG, BONG, -BONG, -BONG)
        p.setPen(Qt.PenStyle.NoPen)
        for lech, loang, dam in self.LOP:
            p.setBrush(QColor(16, 24, 40, dam))
            for i in range(loang, 0, -1):
                p.drawRoundedRect(r.translated(0, lech).adjusted(-i, -i, i, i), 16 + i, 16 + i)
        p.setPen(QPen(QColor(VIEN), 1))
        p.setBrush(QColor(TRANG))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)


class NutChinh(QPushButton):
    """Nút hành động chính của màn hình: có độ nâng, nâng thêm khi rê chuột."""

    def __init__(self, chu: str):
        super().__init__(chu)
        self.setObjectName("chinh")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        mau = QColor(NHAN)
        mau.setAlpha(110)
        self._bong = QGraphicsDropShadowEffect(self, blurRadius=12, xOffset=0, yOffset=3, color=mau)
        self.setGraphicsEffect(self._bong)
        self._dong = QPropertyAnimation(self._bong, b"blurRadius", self, duration=150, easingCurve=QEasingCurve.Type.OutCubic)

    def _nang(self, muc: float) -> None:
        self._dong.stop()
        self._dong.setEndValue(muc)
        self._dong.start()

    def enterEvent(self, e) -> None:
        self._nang(24)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._nang(12)
        super().leaveEvent(e)

    def changeEvent(self, e) -> None:
        if e.type() == QEvent.Type.EnabledChange:
            self._bong.setEnabled(self.isEnabled())
        super().changeEvent(e)


class HangSo(QWidget):
    """Hàng ô số tổng kết: số lớn ở trên, nhãn nhỏ ở dưới."""

    def __init__(self) -> None:
        super().__init__()
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        self._muc: list[tuple[str, int]] = []

    def dat(self, muc: list[tuple[str, int, str]], rong: str = "") -> None:
        """muc: (nhãn, số, màu chữ); màu rỗng khi số đó không đáng chú ý."""
        while (x := self._lay.takeAt(0)) is not None:
            if x.widget():
                x.widget().deleteLater()
        self._muc = [(n, s) for n, s, _ in muc]
        if not muc:
            self._lay.addWidget(QLabel(rong))
            return
        for nhan, so, mau in muc:
            o = QLabel(str(so))
            o.setFont(_font(30, QFont.Weight.Bold, -0.5))
            o.setStyleSheet(f"color: {mau or CHU};")
            ten = QLabel(nhan)
            ten.setObjectName("phu")
            self._lay.addWidget(The(o, ten, dem=14), 1)

    def text(self) -> str:
        return "   ".join(f"{n}: {s}" for n, s in self._muc)


def khung_man(w: QWidget, tieu_de: str, mo_ta: str) -> QVBoxLayout:
    lay = QVBoxLayout(w)
    lay.setContentsMargins(26, 30, 26, 22)
    lay.setSpacing(2)
    t = QLabel(tieu_de)
    t.setFont(_font(26, QFont.Weight.Bold, -0.4))
    m = QLabel(mo_ta)
    m.setObjectName("moTa")
    m.setContentsMargins(0, 2, 0, 14)
    for x in (t, m):
        x.setIndent(BONG)
        lay.addWidget(x)
    return lay


def hang_nut(lay: QVBoxLayout, *nut: QWidget) -> None:
    """Hàng nút cuối màn hình, căn phải, nút chính đứng cuối."""
    h = QHBoxLayout()
    h.setContentsMargins(BONG, 8, BONG, 4)
    h.setSpacing(12)
    h.addStretch(1)
    for b in nut:
        h.addWidget(b)
    lay.addLayout(h)
