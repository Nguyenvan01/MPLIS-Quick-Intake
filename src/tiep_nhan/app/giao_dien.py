"""Hệ giao diện: bảng màu, QSS, thành phần và hộp thoại dùng chung. Mọi màn hình chỉ lấy màu từ đây."""
from __future__ import annotations

import re
import sys
import unicodedata
from collections.abc import Sequence
from datetime import date, datetime

from PySide6.QtCore import QByteArray, QEasingCurve, QElapsedTimer, QEvent, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
                               QLabel, QLayout, QLineEdit, QProgressBar, QPushButton, QSizePolicy, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                               QVBoxLayout, QWidget)

from ..infra.config import sub_dir
from ..infra.logging import che_cccd
from .icon_lucide import ICON

NEN_APP, NEN_THE, VIEN, VIEN_O = "#F6F7F9", "#FFFFFF", "#E4E7EC", "#D0D5DD"
CHU, CHU_PHU, CHU_NHAN, CHU_NUT = "#101828", "#475467", "#667085", "#344054"
NHAN, NHAN_DAM, NEN_CHON, VONG_FOCUS = "#0B5D56", "#08453F", "#E7F2F0", "#5FB8A9"
KE_BANG, NEN_DANG_CHAY = "#EEF0F3", "#F3FAF8"
VIEN_KEO, NEN_KEO = "#9CCFC5", "#F3FAF8"          # khung kéo thả file
NEN_BAO_LOI, VIEN_BAO_LOI, CHU_LOI = "#FEF0EE", "#F7C1BA", "#B42318"
NEN_XU_LY_TAY, VIEN_XU_LY_TAY = "#FFF8EC", "#F9D9A8"
CAM, CHU_MO, TRANG = "#DC6803", "#98A2B3", "#FFFFFF"
NEN_PHAN_DOAN = "#EAECF0"

# trạng thái -> (chữ, nền, chấm)
TRANG_THAI = {
    "Thành công": ("#146C2E", "#E3F4E8", "#17803D"),
    "Đã có sẵn": ("#344054", "#EEF2F6", "#667085"),
    "Cần kiểm tra": ("#93370D", "#FEF4E6", "#DC6803"),
    "Lỗi": ("#B42318", "#FEF0EE", "#D92D20"),
    "Chạy thử": ("#1849A9", "#EAF2FF", "#2E6BD6"),
    "Đã chuyển": ("#5925DC", "#F1ECFE", "#7A5AF8"),
    "Đang chạy": ("#0B5D56", "#FFFFFF", "#0B5D56"),
    "Chờ": ("#475467", "#F2F4F7", "#98A2B3"),
}
CHE_DO = {
    "thu": {"ten": "Chạy thử", "chu": "#1849A9", "nen": "#EAF2FF", "nen_nhat": "#F3F8FF", "chu_nhan": "#1849A9", "nen_nhan": "#EAF2FF",
            "dai": "<b>CHẠY THỬ</b> · Chỉ điền form, không Lưu. Không tạo hồ sơ trên MPLIS."},
    "that": {"ten": "Chạy thật", "chu": "#B54708", "nen": "#B54708", "nen_nhat": "#FFF6ED", "chu_nhan": "#FFFFFF", "nen_nhan": "#B54708",
             "dai": "<b>CHẠY THẬT</b> · Hồ sơ được Lưu lên MPLIS. Không đóng cửa sổ khi đang chạy."},
}
BONG = 10         # khoảng chừa quanh thẻ để vẽ bóng; hai thẻ kề nhau cách nhau 20px
VAI_PHU = Qt.ItemDataRole.UserRole + 1  # dòng chữ thứ hai trong ô bảng


def _font(co: int, dam: QFont.Weight = QFont.Weight.Normal, gian: float = 0.0) -> QFont:
    f = QFont()
    f.setFamilies(["Segoe UI", ".AppleSystemUIFont", "Helvetica Neue", "Arial"])
    f.setPixelSize(co)
    f.setWeight(dam)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, gian)
    return f


def font_so(co: int = 13, dam: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Font đơn cách cho mã hồ sơ, số phát hành, giờ trong nhật ký."""
    f = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    f.setFamilies(["Consolas", "Menlo", f.family()])
    f.setPixelSize(co)
    f.setWeight(dam)
    return f


QSS = f"""
QWidget {{ color: {CHU}; }}
QLabel, QCheckBox, QRadioButton {{ background: transparent; }}
QDialog {{ background: {NEN_THE}; }}
QToolTip {{ background: {CHU}; color: #FFFFFF; border: none; padding: 6px 10px; }}
QLabel#moTa, QLabel#phu {{ color: {CHU_PHU}; }}
QLabel#nhanNhom {{ color: {CHU_NHAN}; }}
QLabel#nhanO {{ font-size: 13px; font-weight: 600; color: {CHU_NUT}; }}
QLabel#tieuDeThe {{ font-size: 15px; font-weight: 600; }}
QWidget#khungNav {{ background: {NEN_THE}; border-right: 1px solid {VIEN}; }}
QListWidget#nav {{ background: transparent; border: none; outline: 0; }}
QListWidget#ganDay {{ background: transparent; border: none; outline: 0; }}
QListWidget#ganDay::item {{ border: none; padding: 0; }}
QListWidget#ganDay::item:selected {{ background: transparent; }}
QLineEdit, QComboBox {{
    background: {NEN_THE}; border: 1px solid {VIEN_O}; border-radius: 10px; padding: 0 12px; min-height: 40px;
    selection-background-color: {NHAN}; selection-color: #FFFFFF; }}
QLineEdit:hover, QComboBox:hover {{ border-color: #98A2B3; }}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {NHAN}; padding: 0 11px; }}
QLineEdit[loi="true"], QComboBox[chuaChon="true"] {{ border: 2px solid {CAM}; padding: 0 11px; }}
QLineEdit[loi="true"] {{ border-color: #D92D20; }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{ image: url("MUI_TEN"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {NEN_THE}; border: 1px solid {VIEN}; selection-background-color: {NEN_CHON};
    selection-color: {CHU}; outline: 0; }}
QPushButton {{ background: {NEN_THE}; color: {CHU_NUT}; border: 1px solid {VIEN_O}; border-radius: 10px; padding: 0 16px;
    min-height: 40px; font-weight: 600; }}
QPushButton:hover {{ border-color: #98A2B3; background: #F9FAFB; }}
QPushButton:pressed {{ background: {NEN_CHON}; }}
QPushButton:focus {{ border: 2px solid {VONG_FOCUS}; padding: 0 15px; }}
QPushButton:disabled {{ color: #98A2B3; background: #F9FAFB; border-color: {VIEN}; }}
QPushButton#chinh {{ background: {NHAN}; color: #FFFFFF; border: none; padding: 0 22px; }}
QPushButton#chinh:hover, QPushButton#chinh:pressed {{ background: {NHAN_DAM}; }}
QPushButton#chinh[that="true"] {{ background: #B54708; }}
QPushButton#chinh[that="true"]:hover, QPushButton#chinh[that="true"]:pressed {{ background: #93370D; }}
QPushButton#chinh:focus {{ border: 2px solid {VONG_FOCUS}; padding: 0 20px; }}
QPushButton#chinh:disabled {{ background: {VIEN_O}; color: #FFFFFF; }}
QPushButton#nguyHiem {{ color: {CHU_LOI}; border-color: {VIEN_BAO_LOI}; }}
QPushButton#nguyHiem:hover {{ background: {NEN_BAO_LOI}; border-color: {CHU_LOI}; }}
QPushButton#nguyHiem:disabled {{ color: #98A2B3; border-color: {VIEN}; }}
QPushButton#chu {{ background: transparent; border: none; color: {NHAN}; padding: 0 6px; min-height: 28px; }}
QPushButton#chu:hover {{ color: {NHAN_DAM}; text-decoration: underline; }}
QPushButton#chu:focus {{ border: 2px solid {VONG_FOCUS}; padding: 0 4px; }}
QPushButton#chip {{ border-radius: 16px; min-height: 32px; padding: 0 14px; font-weight: 500; }}
QPushButton#chip:focus {{ padding: 0 13px; }}
QPushButton#chip:checked {{ background: {NHAN}; color: #FFFFFF; border: 1px solid {NHAN}; }}
QPushButton#phan {{ background: transparent; border: 2px solid transparent; border-radius: 8px; min-height: 30px; padding: 0 12px; }}
QPushButton#phan:focus {{ border-color: {VONG_FOCUS}; padding: 0 12px; }}
QPushButton#phan:checked {{ background: {NEN_THE}; color: {CHU}; }}
QFrame#nhomPhan {{ background: {NEN_PHAN_DOAN}; border-radius: 10px; }}
QToolButton#tep {{ background: {NEN_THE}; border: 1px solid {VIEN_O}; border-radius: 8px; }}
QToolButton#tep:hover {{ background: {NEN_CHON}; }}
QToolButton#tep:focus {{ border: 2px solid {VONG_FOCUS}; }}
QCheckBox, QRadioButton {{ spacing: 8px; border: 1px solid transparent; border-radius: 6px; padding: 2px; }}
QCheckBox:focus, QRadioButton:focus {{ border-color: {VONG_FOCUS}; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 20px; height: 20px; }}
QCheckBox::indicator:unchecked {{ image: url("O_TICH_TAT"); }}
QCheckBox::indicator:checked {{ image: url("O_TICH_BAT"); }}
QRadioButton::indicator:unchecked {{ image: url("O_TRON_TAT"); }}
QRadioButton::indicator:checked {{ image: url("O_TRON_BAT"); }}
QTableWidget, QTreeWidget {{ background: {NEN_THE}; border: 1px solid transparent; border-radius: 8px; outline: 0; }}
QTableWidget:focus, QTreeWidget:focus {{ border-color: {VONG_FOCUS}; }}
QListWidget, QTextBrowser, QPlainTextEdit {{ background: {NEN_THE}; border: none; outline: 0; }}
QTableWidget::item, QTreeWidget::item {{ border-bottom: 1px solid {KE_BANG}; padding: 2px 10px; }}
QTableWidget::item:selected, QTreeWidget::item:selected {{ background: {NEN_CHON}; color: {CHU}; }}
QHeaderView {{ background: {NEN_THE}; }}
QHeaderView::section {{ background: {NEN_THE}; border: none; border-bottom: 1px solid {VIEN}; padding: 10px;
    font-size: 12px; font-weight: 600; color: {CHU_PHU}; }}
QProgressBar {{ border: none; background: {NEN_PHAN_DOAN}; border-radius: 5px; max-height: 10px; color: transparent; }}
QProgressBar::chunk {{ background: {NHAN}; border-radius: 5px; }}
QProgressBar[cheDo="thu"]::chunk {{ background: #2E6BD6; }}
QProgressBar[cheDo="that"]::chunk {{ background: #B54708; }}
QProgressBar#manh {{ max-height: 8px; border-radius: 4px; }}
QProgressBar#manh::chunk {{ border-radius: 4px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: transparent; width: 6px; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle {{ background: {VIEN_O}; border-radius: 4px; min-height: 28px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}
"""


def _mui_ten() -> str:
    """QSS chỉ nhận ảnh từ file: vẽ một lần vào thư mục dữ liệu, khỏi phải đóng gói thêm tài nguyên."""
    path = sub_dir("giao_dien") / "mui_ten.png"
    ve_anh("xuong", CHU_PHU, 24).save(str(path))
    return path.as_posix()


def _o_chon(tron: bool, bat: bool) -> str:
    """Ảnh ô tích và nút tròn: QSS đặt kích thước ::indicator thì Qt không còn tự vẽ ô."""
    ten = f"{'tron' if tron else 'tich'}_{'bat' if bat else 'tat'}.png"
    path = sub_dir("giao_dien") / ten
    co, ti_le = 20, 2
    pm = QPixmap(co * ti_le, co * ti_le)
    pm.setDevicePixelRatio(ti_le)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = QRectF(1, 1, 18, 18)
    if bat and not tron:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(NHAN))
        p.drawRoundedRect(r, 5, 5)
        p.drawPixmap(QRectF(3, 3, 14, 14), ve_anh("xong", TRANG, 14), QRectF(0, 0, 28, 28))
    else:
        p.setPen(QPen(QColor(NHAN if bat else VIEN_O), 1.5))
        p.setBrush(QColor(NEN_THE))
        p.drawEllipse(r) if tron else p.drawRoundedRect(r, 5, 5)
        if bat:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(NHAN))
            p.drawEllipse(QPointF(10, 10), 5, 5)
    p.end()
    pm.save(str(path))
    return path.as_posix()


def ap_giao_dien(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(_font(14))
    pal = QPalette()
    for vai, mau in ((QPalette.ColorRole.Window, NEN_APP), (QPalette.ColorRole.Base, NEN_THE), (QPalette.ColorRole.Button, NEN_THE),
                     (QPalette.ColorRole.AlternateBase, NEN_THE), (QPalette.ColorRole.Text, CHU), (QPalette.ColorRole.WindowText, CHU),
                     (QPalette.ColorRole.ButtonText, CHU), (QPalette.ColorRole.Highlight, NHAN),
                     (QPalette.ColorRole.HighlightedText, "#FFFFFF"), (QPalette.ColorRole.PlaceholderText, CHU_NHAN),
                     (QPalette.ColorRole.ToolTipBase, CHU), (QPalette.ColorRole.ToolTipText, "#FFFFFF")):
        pal.setColor(vai, QColor(mau))
    app.setPalette(pal)
    qss = QSS.replace("MUI_TEN", _mui_ten())
    for ten, tron, bat in (("O_TICH_TAT", False, False), ("O_TICH_BAT", False, True), ("O_TRON_TAT", True, False), ("O_TRON_BAT", True, True)):
        qss = qss.replace(ten, _o_chon(tron, bat))
    app.setStyleSheet(qss)


# ----- Định dạng dữ liệu -----
_KHOA = re.compile(r"to\s*(\S+?)\|thua\s*(\S+)")
_SO_CCCD = re.compile(r"(?<!\d)\d{12}(?!\d)")
_ANH = re.compile(r"Ảnh:\s*(.+?\.(?:png|jpe?g))(?=\s*(?:·|$))", re.I)
_TRACE = re.compile(r"trace:\s*(.+?\.zip)(?=\s*(?:·|$))", re.I)
_DUONG_DAN = re.compile(r"(?<![\w/\\])(?:[A-Za-z]:[\\/]|/)[^\s·]+")


def ten_ho_so(khoa: str) -> str:
    m = _KHOA.search(khoa)
    return f"Tờ {m[1]}, thửa {m[2]}" if m else khoa


def che_so_giay_to(chu: str) -> str:
    """Nội dung lỗi có thể chứa nguyên số CCCD, nên phải che trước khi hiện ở bảng và tooltip."""
    return _SO_CCCD.sub(lambda m: che_cccd(m[0]), chu)


def rut_gon_ghi_chu(text: str) -> tuple[str, str]:
    """(bản ngắn để hiện trong bảng, bản đầy đủ để làm tooltip)."""
    day = che_so_giay_to(text or "")
    ngan = _TRACE.sub("Có trace", _ANH.sub("Có ảnh form", day))
    return _DUONG_DAN.sub("", ngan).strip(), day


def tep_trong_ghi_chu(text: str) -> tuple[str | None, str | None]:
    """(đường dẫn ảnh form, đường dẫn trace) trong ghi chú gốc."""
    anh, trace = _ANH.search(text or ""), _TRACE.search(text or "")
    return anh[1] if anh else None, trace[1] if trace else None


def ngay_gio(iso: str, hom_nay: date | None = None) -> str:
    t = datetime.fromisoformat(iso)
    return f"Hôm nay {t:%H:%M}" if t.date() == (hom_nay or date.today()) else f"{t:%d/%m/%Y %H:%M}"


def bo_dau(chu: str) -> str:
    bo = "".join(c for c in unicodedata.normalize("NFD", chu) if not unicodedata.combining(c))
    return bo.replace("đ", "d").replace("Đ", "D").casefold()


def khop_tim(tu_khoa: str, *truong: str) -> bool:
    """Gõ "3549", "thua3549" hay "thửa 3549" đều tìm ra."""
    q = re.sub(r"\s+", "", bo_dau(tu_khoa))
    return not q or any(q in re.sub(r"\s+", "", bo_dau(t)) for t in truong if t)


def mau_nhan(chu: str) -> tuple[str, str, str]:
    """Màu (chữ, nền, chấm) cho nội dung ô trạng thái; chữ luôn hiện, màu chỉ để nhìn nhanh."""
    if chu in TRANG_THAI:
        return TRANG_THAI[chu]
    if chu.startswith("Lỗi"):
        return TRANG_THAI["Lỗi"]
    if "cảnh báo" in chu.lower():
        return TRANG_THAI["Cần kiểm tra"]
    if chu == "Tốt":
        return TRANG_THAI["Thành công"]
    for cd in CHE_DO.values():
        if chu == cd["ten"]:
            return cd["chu_nhan"], cd["nen_nhan"], cd["chu_nhan"]
    return TRANG_THAI["Chờ"]


def dat_thuoc_tinh(w: QWidget, ten: str, gia_tri: object) -> None:
    """Đổi thuộc tính động mà QSS đang chọn theo, rồi cho QSS áp lại."""
    w.setProperty(ten, gia_tri)
    w.style().unpolish(w)
    w.style().polish(w)


# ----- Icon -----
def ve_anh(ten: str, mau: str, co: int = 16) -> QPixmap:
    if ten not in ICON:
        raise ValueError(ten)
    ti_le = 2  # vẽ gấp đôi để không răng cưa trên màn hình độ phân giải cao
    pm = QPixmap(co * ti_le, co * ti_le)
    pm.setDevicePixelRatio(ti_le)
    pm.fill(Qt.GlobalColor.transparent)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{mau}" stroke-width="{1.8 * 24 / co:.3f}" '
           f'stroke-linecap="round" stroke-linejoin="round">{ICON[ten]}</svg>')  # nét 1.8px ở mọi cỡ
    p = QPainter(pm)
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, co, co))
    p.end()
    return pm


def ve_icon(ten: str, mau: str, co: int = 16) -> QIcon:
    return QIcon(ve_anh(ten, mau, co))


def nhan_icon(ten: str, mau: str, co: int = 16) -> QLabel:
    o = QLabel()
    o.setPixmap(ve_anh(ten, mau, co))
    o.setFixedSize(co, co)
    return o


def _anh_cham(mau: str, co: int = 8) -> QPixmap:
    ti_le = 2
    pm = QPixmap(co * ti_le, co * ti_le)
    pm.setDevicePixelRatio(ti_le)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(mau))
    p.drawEllipse(0, 0, co, co)
    p.end()
    return pm


# ----- Chuyển động -----
def co_hieu_ung() -> bool:
    """Windows: theo thiết lập tắt hiệu ứng của hệ thống. Nền khác Qt luôn báo tắt nên coi như bật."""
    return sys.platform != "win32" or QApplication.isEffectEnabled(Qt.UIEffect.UI_General)


def chuyen_canh(khung: QWidget, anh_cu: QPixmap, ms: int = 180) -> None:
    """Ảnh màn cũ mờ dần phủ trên màn mới. Hiệu ứng nằm trên lớp ảnh nên không ảnh hưởng widget thật của màn."""
    o = QLabel(khung)
    o.setObjectName("chuyenMan")
    o.setPixmap(anh_cu)
    o.setGeometry(khung.rect())
    o.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    mo = QGraphicsOpacityEffect(o)
    o.setGraphicsEffect(mo)
    dong = QPropertyAnimation(mo, b"opacity", o, duration=ms, startValue=1.0, endValue=0.0, easingCurve=QEasingCurve.Type.OutCubic)
    dong.finished.connect(o.deleteLater)
    o.show()
    o.raise_()
    dong.start()


def dat_tien_do(thanh: QProgressBar, gia_tri: int) -> None:
    if not co_hieu_ung():
        thanh.setValue(gia_tri)
        return
    QPropertyAnimation(thanh, b"value", thanh, duration=320, endValue=gia_tri,
                       easingCurve=QEasingCurve.Type.OutCubic).start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


# ----- Thẻ và nút -----
def _ve_the(p: QPainter, r: QRectF, nen: str, vien: str, day: float, bong: bool, dut: bool = False, bo: float = 16) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if bong:  # các vòng chồng lên nhau tạo một lớp bóng mờ 16px, độ đậm khoảng 5%
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(16, 24, 40, 2))
        for i in range(BONG - 2, 0, -1):
            p.drawRoundedRect(r.translated(0, 2).adjusted(-i, -i, i, i), bo + i, bo + i)
    but = QPen(QColor(vien), day)
    if dut:
        but.setStyle(Qt.PenStyle.DashLine)
    p.setPen(but)
    p.setBrush(QColor(nen))
    nua = day / 2
    p.drawRoundedRect(r.adjusted(nua, nua, -nua, -nua), bo, bo)


class The(QFrame):
    """Thẻ nội dung. Tự vẽ bóng vì QGraphicsDropShadowEffect làm bảng dài bị giật."""

    def __init__(self, *noi_dung: QWidget | QLayout, dem: int = 20, bong: bool = True, nen: str = NEN_THE, vien: str = VIEN,
                 day: float = 1, dut: bool = False):
        super().__init__()
        self._kieu = (nen, vien, day, dut)
        self._bong = bong
        lay = QVBoxLayout(self)
        lay.setContentsMargins(BONG + dem, BONG + dem, BONG + dem, BONG + dem)
        lay.setSpacing(10)
        for x in noi_dung:
            lay.addLayout(x) if isinstance(x, QLayout) else lay.addWidget(x)

    def dat(self, nen: str | None = None, vien: str | None = None, day: float | None = None) -> None:
        n, v, d, dut = self._kieu
        self._kieu = (nen or n, vien or v, day or d, dut)
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(BONG, BONG, -BONG, -BONG)
        n, v, d, dut = self._kieu
        _ve_the(p, r, n, v, d, self._bong, dut)


class _NutCoIcon(QPushButton):
    def __init__(self, chu: str, icon: QIcon | None = None):
        super().__init__(chu)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon is not None:
            self.setIcon(icon)


class NutChinh(_NutCoIcon):
    """Nút hành động chính của màn hình: có độ nâng, nâng thêm khi rê chuột."""

    def __init__(self, chu: str, icon: QIcon | None = None):
        super().__init__(chu, icon)
        self.setObjectName("chinh")
        self._bong = QGraphicsDropShadowEffect(self, blurRadius=10, xOffset=0, yOffset=2, color=self._mau_bong(NHAN))
        self.setGraphicsEffect(self._bong)
        self._dong = QPropertyAnimation(self._bong, b"blurRadius", self, duration=150, easingCurve=QEasingCurve.Type.OutCubic)

    @staticmethod
    def _mau_bong(mau: str) -> QColor:
        c = QColor(mau)
        c.setAlpha(90)
        return c

    def dat_chay_that(self, that: bool) -> None:
        dat_thuoc_tinh(self, "that", "true" if that else "false")
        self._bong.setColor(self._mau_bong("#B54708" if that else NHAN))

    def _nang(self, muc: float) -> None:
        self._dong.stop()
        self._dong.setEndValue(muc)
        self._dong.start()

    def enterEvent(self, e) -> None:
        self._nang(20)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._nang(10)
        super().leaveEvent(e)

    def changeEvent(self, e) -> None:
        if e.type() == QEvent.Type.EnabledChange:
            self._bong.setEnabled(self.isEnabled())
        super().changeEvent(e)


class NutChayThat(NutChinh):
    def __init__(self, chu: str, icon: QIcon | None = None):
        super().__init__(chu, icon)
        self.dat_chay_that(True)


class NutPhu(_NutCoIcon):
    pass


class NutNguyHiem(_NutCoIcon):
    def __init__(self, chu: str, icon: QIcon | None = None):
        super().__init__(chu, icon)
        self.setObjectName("nguyHiem")


class NutChu(_NutCoIcon):
    """Nút dạng liên kết, cho thao tác phụ."""

    def __init__(self, chu: str, icon: QIcon | None = None):
        super().__init__(chu, icon)
        self.setObjectName("chu")


class NhanTrangThai(QLabel):
    """Nhãn viên thuốc có chấm màu; chữ luôn hiện."""

    def __init__(self, text: str = "", cham: bool = True):
        super().__init__()
        self._cham = cham
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.dat(text)

    def dat(self, text: str, mau_theo: str | None = None) -> None:
        chu, nen, cham = mau_nhan(mau_theo or text)
        vien = f"border: 1px solid {chu};" if (mau_theo or text) == "Đang chạy" else ""
        self.setStyleSheet(f"QLabel {{ color: {chu}; background: {nen}; border-radius: 11px; padding: 0 10px; font-size: 12px; "
                           f"font-weight: 600; {vien} }}")
        self.setText(f'<span style="color:{cham}">●</span>&nbsp;{text}' if self._cham else text)


def _ve_o_vien_thuoc(p: QPainter, r: QRect, chu: str, mau_theo: str | None = None) -> None:
    c, n, cham = mau_nhan(mau_theo or chu)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    f = _font(12, QFont.Weight.DemiBold)
    p.setFont(f)
    fm = QFontMetrics(f)
    cao = 22
    rong = min(fm.horizontalAdvance(chu) + 34, r.width() - 12)
    o = QRectF(r.x() + 8, r.center().y() - cao / 2 + 1, rong, cao)
    p.setPen(QPen(QColor(c), 1) if chu == "Đang chạy" else Qt.PenStyle.NoPen)
    p.setBrush(QColor(n))
    p.drawRoundedRect(o, cao / 2, cao / 2)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(cham))
    p.drawEllipse(QPointF(o.x() + 12, o.center().y()), 3, 3)
    p.setPen(QColor(c))
    p.drawText(o.adjusted(22, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
               fm.elidedText(chu, Qt.TextElideMode.ElideRight, int(o.width()) - 28))
    p.restore()


def _to_nen_dong(p: QPainter, o: QStyleOptionViewItem, i) -> None:
    """QSS ::item làm mất BackgroundRole của ô, nên tô trực tiếp."""
    nen = i.data(Qt.ItemDataRole.BackgroundRole)
    if nen is not None:
        p.fillRect(o.rect, nen)


class DelegateDong(QStyledItemDelegate):
    """Ô chữ thường nhưng giữ được màu nền riêng của dòng."""

    def paint(self, p: QPainter, o: QStyleOptionViewItem, i) -> None:
        _to_nen_dong(p, o, i)
        super().paint(p, o, i)


class _DelegateNen(QStyledItemDelegate):
    """Vẽ nền, viền, dòng chọn theo QSS của bảng; lớp con chỉ vẽ phần chữ."""

    def _nen(self, p: QPainter, o: QStyleOptionViewItem, i) -> None:
        _to_nen_dong(p, o, i)
        opt = QStyleOptionViewItem(o)
        self.initStyleOption(opt, i)
        opt.text = ""
        w = opt.widget
        (w.style() if w else QApplication.style()).drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, p, w)


class DelegateTrangThai(_DelegateNen):
    """Vẽ viên thuốc theo chữ của ô."""

    def paint(self, p: QPainter, o: QStyleOptionViewItem, i) -> None:
        self._nen(p, o, i)
        chu = i.data(Qt.ItemDataRole.DisplayRole) or ""
        if chu:
            _ve_o_vien_thuoc(p, o.rect, str(chu))

    def sizeHint(self, o: QStyleOptionViewItem, i) -> QSize:
        chu = str(i.data(Qt.ItemDataRole.DisplayRole) or "")
        return QSize(QFontMetrics(_font(12, QFont.Weight.DemiBold)).horizontalAdvance(chu) + 56, 44)


class DelegateHaiDong(_DelegateNen):
    """Chữ đậm ở dòng đầu, chữ phụ ở dòng hai (hoặc cùng một dòng nếu ngang=True)."""

    def __init__(self, parent: QWidget | None = None, ngang: bool = False):
        super().__init__(parent)
        self.ngang = ngang

    def paint(self, p: QPainter, o: QStyleOptionViewItem, i) -> None:
        self._nen(p, o, i)
        p.save()
        r = o.rect.adjusted(12, 4, -8, -4)
        a = str(i.data(Qt.ItemDataRole.DisplayRole) or "")
        b = str(i.data(VAI_PHU) or "")
        dam, phu = _font(14, QFont.Weight.DemiBold), _font(12)
        p.setFont(dam)
        p.setPen(QColor(CHU))
        if self.ngang:
            rong_a = QFontMetrics(dam).horizontalAdvance(a)
            p.drawText(r, Qt.AlignmentFlag.AlignVCenter, a)
            p.setFont(_font(13))
            p.setPen(QColor(CHU_PHU))
            p.drawText(r.adjusted(rong_a + 6, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, b)
        elif not b:
            p.drawText(r, Qt.AlignmentFlag.AlignVCenter, QFontMetrics(dam).elidedText(a, Qt.TextElideMode.ElideRight, r.width()))
        else:
            giua = r.center().y() + 1
            p.drawText(QRect(r.x(), r.y(), r.width(), giua - r.y()), Qt.AlignmentFlag.AlignBottom,
                       QFontMetrics(dam).elidedText(a, Qt.TextElideMode.ElideRight, r.width()))
            p.setFont(phu)
            p.setPen(QColor(CHU_PHU))
            p.drawText(QRect(r.x(), giua + 1, r.width(), r.bottom() - giua), Qt.AlignmentFlag.AlignTop,
                       QFontMetrics(phu).elidedText(b, Qt.TextElideMode.ElideRight, r.width()))
        p.restore()

    def sizeHint(self, o: QStyleOptionViewItem, i) -> QSize:
        s = super().sizeHint(o, i)
        return QSize(max(s.width(), 180), 44 if self.ngang else 56)


class DelegateO(_DelegateNen):
    """Giá trị gốc trong ô nền xám bo 8px, xuống dòng chứ không cắt chữ."""

    def paint(self, p: QPainter, o: QStyleOptionViewItem, i) -> None:
        self._nen(p, o, i)
        chu = str(i.data(Qt.ItemDataRole.DisplayRole) or "")
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = _font(14)
        p.setFont(f)
        ve_rong = o.rect.width() - 24
        kho = QFontMetrics(f).boundingRect(QRect(0, 0, ve_rong - 20, 100), Qt.TextFlag.TextWordWrap, chu)
        khung = QRect(o.rect.x() + 10, o.rect.center().y() - kho.height() // 2 - 5, min(kho.width() + 20, ve_rong), kho.height() + 10)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#F2F4F7"))
        p.drawRoundedRect(QRectF(khung), 8, 8)
        p.setPen(QColor(CHU))
        p.drawText(khung.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, chu)
        p.restore()


def doan_ket_qua(tom_tat: str) -> list[tuple[int, str]]:
    """"20 Thành công · 2 Cần kiểm tra" -> [(20, "Thành công"), (2, "Cần kiểm tra")]."""
    return [(int(m[1]), m[2].strip()) for m in re.finditer(r"(\d+)\s+([^·]+)", tom_tat or "")]


class DelegateKetQua(_DelegateNen):
    """Thanh xếp chồng theo màu trạng thái, dưới là chữ tóm tắt."""

    def paint(self, p: QPainter, o: QStyleOptionViewItem, i) -> None:
        self._nen(p, o, i)
        tom_tat = str(i.data(Qt.ItemDataRole.DisplayRole) or "")
        doan = doan_ket_qua(tom_tat)
        r = o.rect.adjusted(12, 7, -14, -7)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tong = sum(n for n, _ in doan) or 1
        x = float(r.x())
        p.setPen(Qt.PenStyle.NoPen)
        khung = QPainterPath()
        khung.addRoundedRect(QRectF(r.x(), r.y(), r.width(), 8), 4, 4)
        p.setClipPath(khung)
        p.setBrush(QColor(NEN_PHAN_DOAN))
        p.drawRect(QRectF(r.x(), r.y(), r.width(), 8))
        for n, ten in doan:
            rong = r.width() * n / tong
            p.setBrush(QColor(mau_nhan(ten)[2]))
            p.drawRect(QRectF(x, r.y(), rong, 8))
            x += rong
        p.setClipping(False)
        p.setFont(_font(12))
        p.setPen(QColor(CHU_PHU))
        p.drawText(r.adjusted(0, 12, 0, 0), Qt.AlignmentFlag.AlignVCenter, tom_tat.lower())
        p.restore()

    def sizeHint(self, o: QStyleOptionViewItem, i) -> QSize:
        return QSize(180, 52)


class ChipLoc(QPushButton):
    """Nút lọc dạng viên thuốc, có số đếm."""

    def __init__(self, text: str, so: int = 0, cham: str | None = None):
        super().__init__()
        self.ten = text
        self.setObjectName("chip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if cham:
            self.setIcon(QIcon(_anh_cham(cham)))
            self.setIconSize(QSize(8, 8))
        self.dat_so(so)

    def dat_so(self, so: int) -> None:
        self.setText(f"{self.ten} · {so}")


class TheChiSo(QAbstractButton):
    """Ô số lớn có biểu tượng tròn, bấm được để lọc."""

    def __init__(self, so: int, nhan: str, mau: tuple[str, str, str], icon: str = "xong"):
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(84 + BONG)
        self.so, self.nhan, self.mau, self._icon = so, nhan, mau, icon
        self.toggled.connect(lambda _=False: self.update())
        self.setAccessibleName(f"{nhan}: {so}")

    def dat(self, so: int) -> None:
        self.so = so
        self.setAccessibleName(f"{self.nhan}: {so}")
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(220, 84 + BONG)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(BONG, BONG / 2, -BONG, -BONG / 2)
        chu, nen, cham = self.mau
        if self.hasFocus():
            vien, day = VONG_FOCUS, 2
        elif self.isChecked():
            vien, day = cham, 2
        else:
            vien, day = VIEN, 1
        _ve_the(p, r, NEN_THE, vien, day, True)
        tam = QPointF(r.x() + 38, r.center().y())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(nen))
        p.drawEllipse(tam, 20, 20)
        p.drawPixmap(QRectF(tam.x() - 10, tam.y() - 10, 20, 20), ve_anh(self._icon, chu, 20), QRectF(0, 0, 40, 40))
        chu_x = r.adjusted(70, 6, -10, -6)
        p.setFont(_font(26, QFont.Weight.Bold))
        p.setPen(QColor(chu if self.so else CHU))
        p.drawText(chu_x.adjusted(0, 0, 0, -22), Qt.AlignmentFlag.AlignVCenter, str(self.so))
        p.setFont(_font(13))
        p.setPen(QColor(CHU_PHU))
        p.drawText(chu_x.adjusted(0, 36, 0, 0), Qt.AlignmentFlag.AlignVCenter, self.nhan)


class DaiCheDo(QFrame):
    """Dải trên cùng vùng nội dung cho biết đang ở Chạy thử hay Chạy thật."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(32, 0, 32, 0)
        lay.setSpacing(10)
        self.icon, self.chu = QLabel(), QLabel()
        lay.addWidget(self.icon)
        lay.addWidget(self.chu, 1)
        self.hide()

    def dat(self, che_do: str | None) -> None:
        if che_do is None:
            self.hide()
            return
        cd = CHE_DO[che_do]
        self.setStyleSheet(f"DaiCheDo {{ background: {cd['nen_nhan']}; }} QLabel {{ color: {cd['chu_nhan']}; }}")
        self.chu.setText(cd["dai"])
        self.icon.setPixmap(ve_anh("canh_bao" if che_do == "that" else "thong_tin", cd["chu_nhan"], 18))
        self.show()


class O_TimKiem(QLineEdit):
    def __init__(self, goi_y: str = "") -> None:
        super().__init__()
        self.setPlaceholderText(goi_y)
        self.setClearButtonEnabled(True)
        self.addAction(ve_icon("tim", CHU_NHAN), QLineEdit.ActionPosition.LeadingPosition)


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
                x.widget().hide()
                x.widget().deleteLater()
        self._muc = [(n, s) for n, s, _ in muc]
        if not muc:
            self._lay.addWidget(QLabel(rong))
            return
        for nhan, so, mau in muc:
            o = QLabel(str(so))
            o.setFont(_font(26, QFont.Weight.Bold))
            o.setStyleSheet(f"color: {mau or CHU};")
            ten = QLabel(nhan)
            ten.setObjectName("phu")
            self._lay.addWidget(The(o, ten, dem=14), 1)

    def text(self) -> str:
        return "   ".join(f"{n}: {s}" for n, s in self._muc)


# ----- Khung màn hình -----
def khung_man(w: QWidget, tieu_de: str, mo_ta: str) -> QVBoxLayout:
    lay = QVBoxLayout(w)
    lay.setContentsMargins(32 - BONG, 28, 32 - BONG, 16)
    lay.setSpacing(0)
    tren = QHBoxLayout()
    tren.setContentsMargins(BONG, 0, BONG, 10)
    t = QLabel(tieu_de)
    t.setFont(_font(24, QFont.Weight.Bold))
    m = QLabel(mo_ta)
    m.setObjectName("moTa")
    m.setWordWrap(True)
    w.dong_mo_ta, w.hang_mo_ta, w.o_goc = m, QHBoxLayout(), QHBoxLayout()  # màn hình gắn thêm nhãn ở đây
    w.hang_mo_ta.setSpacing(8)
    w.hang_mo_ta.addWidget(m, 1)
    cot = QVBoxLayout()
    cot.setSpacing(2)
    cot.addWidget(t)
    cot.addLayout(w.hang_mo_ta)
    tren.addLayout(cot, 1)
    tren.addLayout(w.o_goc)
    w.o_goc.setAlignment(Qt.AlignmentFlag.AlignTop)
    lay.addLayout(tren)
    return lay


def hang_nut(lay: QVBoxLayout, *nut: QWidget, trai: Sequence[QWidget] = ()) -> None:
    """Hàng nút cuối màn hình: thao tác phụ bên trái, nút chính đứng cuối bên phải."""
    h = QHBoxLayout()
    h.setContentsMargins(BONG, 8, BONG, 0)
    h.setSpacing(12)
    for b in trai:
        h.addWidget(b)
    h.addStretch(1)
    for b in nut:
        h.addWidget(b)
    lay.addLayout(h)


# ----- Hộp thoại -----
_KIEU_HOP = {
    "thuong": (NHAN, "thong_tin", NutChinh),
    "thanh_cong": ("#17803D", "xong", NutChinh),
    "canh_bao": (CAM, "canh_bao", NutChinh),
    "loi": ("#D92D20", "loi", NutChinh),
    "chay_that": ("#B54708", "canh_bao", NutChayThat),
    "nguy_hiem": ("#D92D20", "canh_bao", NutNguyHiem),
}


def _khung_hop(parent: QWidget | None, tieu_de: str, noi_dung: str, kieu: str, than: QLayout | None = None,
               mo_dan: bool = True) -> tuple[QDialog, QHBoxLayout]:
    """Dải màu trên cùng, icon tròn, tiêu đề, mô tả; trả về hộp và hàng nút để nơi gọi thêm nút."""
    mau, icon, _ = _KIEU_HOP[kieu]
    d = QDialog(parent)
    d.setWindowTitle(tieu_de)
    d.setMinimumWidth(460)
    goc = QVBoxLayout(d)
    goc.setContentsMargins(0, 0, 0, 0)
    goc.setSpacing(0)
    dai = QFrame()
    dai.setFixedHeight(6)
    dai.setStyleSheet(f"background: {mau};")
    goc.addWidget(dai)
    trong = QVBoxLayout()
    trong.setContentsMargins(24, 22, 24, 22)
    trong.setSpacing(16)
    goc.addLayout(trong)
    tren = QHBoxLayout()
    tren.setSpacing(14)
    o_icon = QLabel()
    o_icon.setFixedSize(40, 40)
    o_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    c = QColor(mau)
    o_icon.setStyleSheet(f"background: rgba({c.red()},{c.green()},{c.blue()},26); border-radius: 20px;")
    o_icon.setPixmap(ve_anh(icon, mau, 20))
    tren.addWidget(o_icon, 0, Qt.AlignmentFlag.AlignTop)
    cot = QVBoxLayout()
    cot.setSpacing(6)
    t = QLabel(tieu_de)
    t.setFont(_font(18, QFont.Weight.Bold))
    t.setWordWrap(True)
    cot.addWidget(t)
    if noi_dung:
        m = QLabel(noi_dung)
        m.setObjectName("moTa")
        m.setWordWrap(True)
        cot.addWidget(m)
    tren.addLayout(cot, 1)
    trong.addLayout(tren)
    if than is not None:
        trong.addLayout(than)
    nut = QHBoxLayout()
    nut.setSpacing(10)
    nut.addStretch(1)
    trong.addLayout(nut)
    if mo_dan and co_hieu_ung():
        d.setWindowOpacity(0.0)
        hien = QPropertyAnimation(d, b"windowOpacity", d, duration=140, startValue=0.0, endValue=1.0, easingCurve=QEasingCurve.Type.OutCubic)
        QTimer.singleShot(0, d, hien.start)
    return d, nut


def hop_xac_nhan(parent: QWidget | None, tieu_de: str, noi_dung: str, chi_tiet: list[tuple[str, str]], nut_dong_y: str,
                 kieu: str = "thuong") -> bool:
    """Nút mặc định và Esc đều là Quay lại: bấm Enter theo thói quen không làm gì nguy hiểm."""
    than = None
    if chi_tiet:
        than = QVBoxLayout()
        khoi = QFrame()
        khoi.setStyleSheet(f"QFrame {{ background: {NEN_APP}; border-radius: 10px; }}")
        luoi = QGridLayout(khoi)
        luoi.setContentsMargins(14, 12, 14, 12)
        luoi.setHorizontalSpacing(16)
        luoi.setVerticalSpacing(6)
        for r, (a, b) in enumerate(chi_tiet):
            nhan = QLabel(a)
            nhan.setObjectName("phu")
            gia_tri = QLabel(b)
            gia_tri.setWordWrap(True)
            luoi.addWidget(nhan, r, 0, Qt.AlignmentFlag.AlignTop)
            luoi.addWidget(gia_tri, r, 1)
        luoi.setColumnStretch(1, 1)
        than.addWidget(khoi)
    d, nut = _khung_hop(parent, tieu_de, noi_dung, kieu, than)
    quay = NutPhu("Quay lại")
    dong_y = _KIEU_HOP[kieu][2](nut_dong_y)
    dong_y.setAutoDefault(False)
    quay.setDefault(True)
    quay.clicked.connect(d.reject)
    dong_y.clicked.connect(d.accept)
    nut.addWidget(quay)
    nut.addWidget(dong_y)
    quay.setFocus()
    return d.exec() == QDialog.DialogCode.Accepted


def hop_thong_bao(parent: QWidget | None, tieu_de: str, noi_dung: str, kieu: str = "thuong") -> None:
    d, nut = _khung_hop(parent, tieu_de, noi_dung, kieu)
    ok = NutChinh("Đã hiểu")
    ok.setDefault(True)
    ok.clicked.connect(d.accept)
    nut.addWidget(ok)
    ok.setFocus()
    d.exec()


def hop_nhap(parent: QWidget | None, tieu_de: str, mo_ta: str, nhan_o: str, goi_y: str = "", nut_dong_y: str = "Đồng ý",
             nut_bo_qua: str = "Bỏ qua") -> str | None:
    """Hộp hỏi khi tool đang chờ người dùng; luôn nổi trên cửa sổ Chromium."""
    than = QVBoxLayout()
    than.setSpacing(6)
    cho = QLabel()
    mau_cho, nen_cho, _ = TRANG_THAI["Cần kiểm tra"]
    cho.setFixedHeight(22)
    cho.setStyleSheet(f"color: {mau_cho}; background: {nen_cho}; border-radius: 11px; padding: 0 10px; font-size: 12px; font-weight: 600;")
    than.addWidget(cho, 0, Qt.AlignmentFlag.AlignLeft)
    nhan = QLabel(nhan_o)
    nhan.setObjectName("nhanO")
    o = QLineEdit()
    o.setFont(font_so(16))
    o.setMinimumHeight(44)
    than.addWidget(nhan)
    than.addWidget(o)
    if goi_y:
        g = QLabel(goi_y)
        g.setObjectName("phu")
        g.setWordWrap(True)
        than.addWidget(g)
    d, nut = _khung_hop(parent, tieu_de, mo_ta, "canh_bao", than, mo_dan=False)  # hộp đang chờ người dùng phải thấy ngay
    d.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    bo_qua, dong_y = NutPhu(nut_bo_qua), NutChinh(nut_dong_y)
    bo_qua.setAutoDefault(False)
    dong_y.setDefault(True)
    dong_y.setEnabled(False)
    o.textChanged.connect(lambda t: dong_y.setEnabled(bool(t.strip())))
    bo_qua.clicked.connect(d.reject)
    dong_y.clicked.connect(d.accept)
    nut.addWidget(bo_qua)
    nut.addWidget(dong_y)
    dem = QElapsedTimer()
    dem.start()

    def cap_nhat() -> None:
        s = dem.elapsed() // 1000
        cho.setText(f"Tool đang chờ bạn · {s // 60:02d}:{s % 60:02d}")

    cap_nhat()
    gio = QTimer(d, interval=1000)
    gio.timeout.connect(cap_nhat)
    gio.start()
    o.setFocus()
    QTimer.singleShot(0, d, lambda: (d.raise_(), d.activateWindow()))  # gọi show() trước exec() sẽ làm hộp mất tính modal
    return o.text().strip() if d.exec() == QDialog.DialogCode.Accepted else None
