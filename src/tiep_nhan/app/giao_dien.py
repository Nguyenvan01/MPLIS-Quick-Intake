"""Hệ giao diện: bảng màu, QSS, thành phần và hộp thoại dùng chung. Mọi màn hình chỉ lấy màu từ đây."""
from __future__ import annotations

import re
import sys
import unicodedata
from collections.abc import Callable, Sequence
from datetime import date, datetime

from PySide6.QtCore import QByteArray, QEasingCurve, QElapsedTimer, QEvent, QObject, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QComboBox, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
                               QLabel, QLayout, QLineEdit, QProgressBar, QPushButton, QSizePolicy, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                               QVBoxLayout, QWidget)

from ..infra.config import assets_dir, sub_dir
from ..infra.logging import che_cccd, che_so_trong_chu
from .icon_lucide import ICON

# ===== Token của hệ thiết kế: mọi màn hình chỉ lấy màu, font từ đây =====
# Tông xanh dương – trắng (người dùng chốt 10/11/2026): nền trắng, card xanh rất nhạt, nút chính và mục đang chọn xanh dương.
NEN_APP, NEN_THE, VIEN, VIEN_DAM = "#FFFFFF", "#F5F8FF", "#DCE3F0", "#B6C3DD"   # nền trang, card inset, kẻ mảnh, viền khi rê
VIEN_O = VIEN                                                                   # viền ô nhập, nút phụ
CHU, CHU_PHU, CHU_NHAN = "#0F172A", "#475569", "#5B6B82"                        # chữ chính, phụ, mờ
CHU_NUT, TRANG = CHU, "#FFFFFF"                                                 # chữ nút phụ; chữ trên nền xanh
NUT_CHINH, NUT_CHINH_RE, NUT_CHINH_BAM = "#2563EB", "#1D4ED8", "#1E40AF"
NUT_TAT_NEN, NUT_TAT_CHU = "#E2E8F0", "#475569"                                 # nút chính bị tắt: vẫn đọc được chữ
LIEN_KET = VONG_FOCUS = "#2563EB"
VONG_FOCUS_NUT = "#1E3A8A"                                                      # viền focus trên nút nền xanh
NHAN, NHAN_DAM = "#1D4ED8", NUT_CHINH_BAM                                       # mục đang chọn, mốc bước, icon nhấn
NEN_RE, NEN_CHON, CHON_THE = "#F0F5FF", "#E3ECFD", "#DCE7FC"                    # rê chuột, mục chọn, dòng chọn trong card
NEN_PHAN_DOAN = "#E4EBF7"                                                       # rãnh nhóm phân đoạn, thanh tiến độ
KE_BANG, NEN_DANG_CHAY = NEN_CHON, "#EDECED"
VIEN_KEO, NEN_KEO = VIEN_DAM, NEN_THE                                           # khung kéo thả file
CHU_MO = "#8A8A8A"                                                              # icon trang trí ở trạng thái trống
FONT_TIEU_DE = ["Segoe UI", ".AppleSystemUIFont", "Helvetica Neue", "Arial"]  # ponytail: Host Grotesk thiếu chữ Việt, chờ người dùng chọn font
FONT_NOI_DUNG = ["Segoe UI", ".AppleSystemUIFont", "Helvetica Neue", "Arial"]  # ponytail: Instrument Sans thiếu chữ Việt, như trên
CO_TIEU_DE_MAN, CO_TIEU_DE_THE, CO_CHU, CO_NHAN, CO_NHO = 30, 18, 14, 13, 12   # đúng 5 cỡ chữ

# trạng thái -> (chữ, nền, chấm); chữ trên nền đạt WCAG AA >= 4.5:1 (đo trong tests/test_giao_dien.py)
TRANG_THAI = {
    "Thành công": ("#166534", "#DCFCE7", "#16A34A"),
    "Đã có sẵn": ("#3F3F46", "#ECECEC", "#71717A"),
    "Cần kiểm tra": ("#92400E", "#FEF3C7", "#D97706"),
    "Lỗi": ("#991B1B", "#FEE2E2", "#DC2626"),
    "Chạy thử": ("#1E40AF", "#DBEAFE", "#3B82F6"),
    "Đã chuyển": ("#5B21B6", "#EDE9FE", "#8B5CF6"),
    "Đang chạy": (CHU, NEN_APP, CHU),
    "Chờ": (CHU_PHU, NEN_CHON, CHU_MO),
}
NEN_BAO_LOI, VIEN_BAO_LOI, CHU_LOI = TRANG_THAI["Lỗi"][1], TRANG_THAI["Lỗi"][1], TRANG_THAI["Lỗi"][0]
NEN_XU_LY_TAY, VIEN_XU_LY_TAY = TRANG_THAI["Cần kiểm tra"][1], TRANG_THAI["Cần kiểm tra"][1]
CAM = "#B45309"                                                                 # viền ô chưa chọn ở màn Ánh xạ
CHE_DO = {
    "thu": {"ten": "Chạy thử", "chu": "#1E40AF", "nen": "#DBEAFE", "nen_nhat": "#EFF6FF", "chu_nhan": "#1E40AF", "nen_nhan": "#DBEAFE",
            "dai": "<b>CHẠY THỬ</b> · Chỉ điền form, không Lưu. Không tạo hồ sơ trên MPLIS."},
    "that": {"ten": "Chạy thật", "chu": "#9A3412", "nen": "#9A3412", "nen_nhat": "#FFF7ED", "chu_nhan": TRANG, "nen_nhan": "#9A3412",
             "dai": "<b>CHẠY THẬT</b> · Hồ sơ được Lưu lên MPLIS. Không đóng cửa sổ khi đang chạy."},
}
BONG = 10         # khoảng chừa quanh thẻ: hai thẻ kề nhau cách nhau 20px
VAI_PHU = Qt.ItemDataRole.UserRole + 1  # dòng chữ thứ hai trong ô bảng


def _font(co: int, dam: QFont.Weight = QFont.Weight.Normal, gian: float = 0.0) -> QFont:
    f = QFont()
    f.setFamilies(FONT_NOI_DUNG)
    f.setPixelSize(co)
    f.setWeight(dam)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, gian)
    return f


def _font_tieu_de(co: int) -> QFont:
    f = _font(co, QFont.Weight.Medium)
    f.setFamilies(FONT_TIEU_DE)
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
QDialog {{ background: {NEN_APP}; }}
QToolTip {{ background: {CHU}; color: {TRANG}; border: none; padding: 6px 10px; }}
QLabel#moTa, QLabel#phu {{ color: {CHU_PHU}; }}
QLabel#nhanNhom {{ color: {CHU_NHAN}; }}
QLabel#nhanO {{ font-size: {CO_NHAN}px; font-weight: 600; color: {CHU}; }}
QLabel#tieuDeThe {{ font-size: {CO_TIEU_DE_THE}px; font-weight: 500; font-family: "{FONT_TIEU_DE[0]}"; }}
QWidget#khungNav {{ background: {NEN_APP}; border-right: 1px solid {VIEN}; }}
QListWidget#nav, QListWidget#ganDay {{ background: transparent; border: none; outline: 0; }}
QListWidget#ganDay::item {{ border: none; padding: 0; }}
QListWidget#ganDay::item:selected {{ background: transparent; }}
QLineEdit, QComboBox {{
    background: {NEN_APP}; border: 1px solid {VIEN}; border-radius: 12px; padding: 0 12px; min-height: 40px; color: {CHU};
    selection-background-color: {NEN_PHAN_DOAN}; selection-color: {CHU}; }}
QLineEdit:hover, QComboBox:hover {{ border-color: {VIEN_DAM}; }}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {VONG_FOCUS}; padding: 0 11px; }}
QLineEdit[loi="true"] {{ border: 2px solid {TRANG_THAI["Lỗi"][2]}; padding: 0 11px; }}
QComboBox[chuaChon="true"] {{ border: 2px solid {CAM}; padding: 0 11px; }}
QComboBox {{ combobox-popup: 0; }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{ image: url("MUI_TEN"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {NEN_APP}; border: 1px solid {VIEN}; border-radius: 12px; padding: 4px; outline: 0;
    font-size: {CO_CHU}px; selection-background-color: {NEN_CHON}; selection-color: {CHU}; }}
QComboBox QAbstractItemView::item {{ min-height: 20px; padding: 8px 12px; border-radius: 8px; color: {CHU}; }}
QComboBox QAbstractItemView::item:hover {{ background: {NEN_THE}; }}
QComboBox QAbstractItemView::item:selected {{ background: {NEN_CHON}; color: {NHAN}; font-weight: 600; }}
QPushButton {{ background: transparent; color: {CHU}; border: 1px solid {VIEN}; border-radius: 20px; padding: 0 18px;
    min-height: 38px; max-height: 38px; font-weight: 600; }}
QPushButton:hover {{ background: {NEN_THE}; border-color: {VIEN_DAM}; }}
QPushButton:pressed {{ background: {NEN_CHON}; }}
QPushButton:focus {{ border: 2px solid {VONG_FOCUS}; padding: 0 17px; min-height: 36px; max-height: 36px; }}
QPushButton:disabled {{ color: {CHU_NHAN}; border-color: {NEN_CHON}; background: transparent; }}
QPushButton#chinh {{ background: {NUT_CHINH}; color: {TRANG}; border: none; padding: 0 22px; min-height: 40px; max-height: 40px; }}
QPushButton#chinh:hover {{ background: {NUT_CHINH_RE}; }}
QPushButton#chinh:pressed {{ background: {NUT_CHINH_BAM}; }}
QPushButton#chinh:focus {{ border: 2px solid {VONG_FOCUS_NUT}; padding: 0 20px; min-height: 36px; max-height: 36px; }}
QPushButton#chinh:disabled {{ background: {NUT_TAT_NEN}; color: {NUT_TAT_CHU}; }}
QPushButton#chu {{ background: transparent; border: none; color: {LIEN_KET}; padding: 0 8px; min-height: 28px; max-height: 28px;
    border-radius: 14px; }}
QPushButton#chu:hover {{ text-decoration: underline; background: transparent; }}
QPushButton#chu:focus {{ border: 2px solid {VONG_FOCUS}; padding: 0 6px; min-height: 24px; max-height: 24px; }}
QPushButton#chip {{ border-radius: 16px; min-height: 30px; max-height: 30px; padding: 0 14px; font-weight: 500; }}
QPushButton#chip:focus {{ padding: 0 13px; min-height: 28px; max-height: 28px; }}
QPushButton#chip:checked {{ background: {NUT_CHINH}; color: {TRANG}; border: 1px solid {NUT_CHINH}; }}
QPushButton#phan {{ background: transparent; border: 2px solid transparent; border-radius: 15px; min-height: 26px; max-height: 26px;
    padding: 0 12px; color: {CHU_PHU}; }}
QPushButton#phan:focus {{ border-color: {VONG_FOCUS}; }}
QPushButton#phan:checked {{ background: {NEN_APP}; color: {NHAN}; }}
QFrame#nhomPhan {{ background: {NEN_PHAN_DOAN}; border-radius: 18px; }}
QToolButton#tep {{ background: transparent; border: 1px solid {VIEN}; border-radius: 15px; }}
QToolButton#tep:hover {{ background: {NEN_APP}; border-color: {VIEN_DAM}; }}
QToolButton#tep:focus {{ border: 2px solid {VONG_FOCUS}; }}
QToolButton#tep:disabled {{ border-color: {NEN_CHON}; }}
QCheckBox, QRadioButton {{ spacing: 8px; border: 2px solid transparent; border-radius: 8px; padding: 2px; }}
QCheckBox:focus, QRadioButton:focus {{ border-color: {VONG_FOCUS}; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 20px; height: 20px; }}
QCheckBox::indicator:unchecked {{ image: url("O_TICH_TAT"); }}
QCheckBox::indicator:checked {{ image: url("O_TICH_BAT"); }}
QRadioButton::indicator:unchecked {{ image: url("O_TRON_TAT"); }}
QRadioButton::indicator:checked {{ image: url("O_TRON_BAT"); }}
QTableWidget, QTreeWidget {{ background: transparent; border: 2px solid transparent; border-radius: 10px; outline: 0; }}
QTableWidget:focus, QTreeWidget:focus {{ border-color: {VONG_FOCUS}; }}
QListWidget, QTextBrowser, QPlainTextEdit {{ background: transparent; border: none; outline: 0; }}
QTableWidget::item, QTreeWidget::item {{ border: none; padding: 2px 10px; }}
QTableWidget::item:selected, QTreeWidget::item:selected {{ background: {CHON_THE}; color: {CHU}; }}
QHeaderView, QHeaderView::section {{ background: transparent; }}
QHeaderView::section {{ border: none; padding: 10px; font-size: {CO_NHO}px; font-weight: 600; color: {CHU_PHU}; }}
QProgressBar {{ border: none; background: {NEN_PHAN_DOAN}; border-radius: 5px; max-height: 10px; color: transparent; }}
QProgressBar::chunk {{ background: {NUT_CHINH}; border-radius: 5px; }}
QProgressBar[cheDo="thu"]::chunk {{ background: {CHE_DO["thu"]["chu"]}; }}
QProgressBar[cheDo="that"]::chunk {{ background: {CHE_DO["that"]["chu"]}; }}
QProgressBar#manh {{ max-height: 8px; border-radius: 4px; }}
QProgressBar#manh::chunk {{ border-radius: 4px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: transparent; width: 6px; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle {{ background: {VIEN_DAM}; border-radius: 4px; min-height: 28px; min-width: 28px; }}
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
        p.setPen(QPen(QColor(NHAN if bat else VIEN_DAM), 1.5))
        p.setBrush(QColor(NEN_APP))
        p.drawEllipse(r) if tron else p.drawRoundedRect(r, 5, 5)
        if bat:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(NHAN))
            p.drawEllipse(QPointF(10, 10), 5, 5)
    p.end()
    pm.save(str(path))
    return path.as_posix()


class _ChinhCombo(QObject):
    """Áp cho mọi QComboBox: bộ vẽ mặc định của popup bỏ qua QSS ::item nên thay bằng QStyledItemDelegate;
    popup rộng ít nhất bằng ô và nở theo chữ dài nhất thay vì cắt chữ."""

    def __init__(self, app: QApplication):
        super().__init__(app)
        self._cua: dict[int, QComboBox] = {}

    def eventFilter(self, o: QObject, e: QEvent) -> bool:
        if e.type() == QEvent.Type.Polish and isinstance(o, QComboBox) and not o.property("daChinh"):
            o.setProperty("daChinh", True)
            o.setItemDelegate(QStyledItemDelegate(o))
            o.view().setTextElideMode(Qt.TextElideMode.ElideNone)
            self._cua[id(o.view())] = o
            o.view().installEventFilter(self)
            o.destroyed.connect(lambda _=None, k=id(o.view()): self._cua.pop(k, None))
        elif e.type() == QEvent.Type.Show and id(o) in self._cua:
            c, v = self._cua[id(o)], o
            rong = max(c.width(), v.sizeHintForColumn(0) + 24 + 8 + v.verticalScrollBar().sizeHint().width())
            if v.window().width() < rong:
                v.window().resize(rong, v.window().height())
        return False


def nap_font() -> list[str]:
    """Nạp font trong assets/fonts; trả về tên các họ font đã nạp."""
    ho: list[str] = []
    for f in sorted((assets_dir() / "fonts").glob("*.ttf")):
        ho += QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(f.resolve())))
    return sorted(set(ho))


def ap_giao_dien(app: QApplication) -> None:
    nap_font()
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
    app.chinh_combo = _ChinhCombo(app)  # giữ tham chiếu để bộ lọc không bị thu hồi
    app.installEventFilter(app.chinh_combo)


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
    return che_so_trong_chu(chu)


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
def _ve_the(p: QPainter, r: QRectF, nen: str, vien: str | None, day: float, dut: bool = False, bo: float = 16) -> None:
    """Card inset: nền phẳng, bo 16px, không bóng; chỉ có viền khi cần (khung kéo thả, đang chọn, focus)."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if vien:
        but = QPen(QColor(vien), day)
        if dut:
            but.setStyle(Qt.PenStyle.DashLine)
        p.setPen(but)
    else:
        p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(nen))
    nua = day / 2 if vien else 0
    p.drawRoundedRect(r.adjusted(nua, nua, -nua, -nua), bo, bo)


class The(QFrame):
    """Thẻ nội dung dạng inset. vien=None: không viền; bong giữ để gọi cũ không lỗi, hệ thiết kế không dùng bóng."""

    def __init__(self, *noi_dung: QWidget | QLayout, dem: int = 24, bong: bool = False, nen: str = NEN_THE, vien: str | None = None,
                 day: float = 1, dut: bool = False):
        super().__init__()
        self._kieu = (nen, vien, day, dut)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(BONG + dem, BONG + dem, BONG + dem, BONG + dem)
        lay.setSpacing(10)
        for x in noi_dung:
            lay.addLayout(x) if isinstance(x, QLayout) else lay.addWidget(x)

    def dat(self, nen: str | None = None, vien: str | None = None, day: float | None = None, dut: bool | None = None) -> None:
        n, v, d, du = self._kieu
        self._kieu = (nen or n, vien or v, day or d, du if dut is None else dut)
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(BONG, BONG, -BONG, -BONG)
        _ve_the(p, r, *self._kieu)


class _NutCoIcon(QPushButton):
    def __init__(self, chu: str, icon: QIcon | None = None):
        super().__init__(chu)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon is not None:
            self.setIcon(icon)


class NutChinh(_NutCoIcon):
    """Nút hành động chính: nền tối, dạng viên thuốc (bo bằng nửa chiều cao, đặt trong QSS)."""

    def __init__(self, chu: str, icon: QIcon | None = None):
        super().__init__(chu, icon)
        self.setObjectName("chinh")

    def dat_chay_that(self, that: bool) -> None:
        dat_thuoc_tinh(self, "that", "true" if that else "false")


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


class NhanRutGon(QLabel):
    """Nhãn một dòng tự cắt bớt ở giữa theo bề rộng còn lại, tooltip là chữ đầy đủ; không đẩy widget bên cạnh."""

    def __init__(self, text: str = ""):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.dat(text)

    def dat(self, text: str) -> None:
        self._day = text
        self.setToolTip(text)
        self._cat()

    def _cat(self) -> None:
        super().setText(QFontMetrics(self.font()).elidedText(self._day, Qt.TextElideMode.ElideMiddle, max(self.width(), 40)))

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._cat()

    def minimumSizeHint(self) -> QSize:
        return QSize(40, super().minimumSizeHint().height())


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
        p.setBrush(QColor(NEN_APP))
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
        p.drawText(r.adjusted(0, 12, 0, 0), Qt.AlignmentFlag.AlignVCenter,
                   QFontMetrics(_font(12)).elidedText(tom_tat.lower(), Qt.TextElideMode.ElideRight, r.width()))
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
        _ve_the(p, r, NEN_THE, vien, day)
        tam = QPointF(r.x() + 38, r.center().y())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(nen))
        p.drawEllipse(tam, 20, 20)
        p.drawPixmap(QRectF(tam.x() - 10, tam.y() - 10, 20, 20), ve_anh(self._icon, chu, 20), QRectF(0, 0, 40, 40))
        chu_x = r.adjusted(70, 6, -10, -6)
        p.setFont(_font_tieu_de(CO_TIEU_DE_MAN))
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
            o.setFont(_font_tieu_de(CO_TIEU_DE_MAN))
            o.setStyleSheet(f"color: {mau or CHU};")
            ten = QLabel(nhan)
            ten.setObjectName("phu")
            self._lay.addWidget(The(o, ten, dem=14), 1)

    def text(self) -> str:
        return "   ".join(f"{n}: {s}" for n, s in self._muc)


# ----- Khung màn hình -----
def khung_man(w: QWidget, tieu_de: str, mo_ta: str) -> QVBoxLayout:
    lay = QVBoxLayout(w)
    lay.setContentsMargins(24 - BONG, 24, 24 - BONG, 16)  # lề trang 24px
    lay.setSpacing(0)
    tren = QHBoxLayout()
    tren.setContentsMargins(BONG, 0, BONG, 10)
    t = QLabel(tieu_de)
    t.setFont(_font_tieu_de(CO_TIEU_DE_MAN))
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
    "thanh_cong": (TRANG_THAI["Thành công"][2], "xong", NutChinh),
    "canh_bao": (CAM, "canh_bao", NutChinh),
    "loi": (TRANG_THAI["Lỗi"][2], "loi", NutChinh),
    "chay_that": (CHE_DO["that"]["chu"], "canh_bao", NutChayThat),
    "nguy_hiem": (TRANG_THAI["Lỗi"][2], "canh_bao", NutChinh),  # nút xác nhận vẫn là nút chính; màu đỏ chỉ ở dải báo
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
    t.setFont(_font_tieu_de(CO_TIEU_DE_THE))
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
                 kieu: str = "thuong", nut_huy: str = "Quay lại") -> bool:
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
    quay = NutPhu(nut_huy)
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
             nut_bo_qua: str = "Bỏ qua", hop_le: Callable[[str], bool] | None = None, bao_sai: str = "") -> str | None:
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
    o.setFont(font_so(CO_CHU))
    o.setMinimumHeight(44)
    than.addWidget(nhan)
    than.addWidget(o)
    sai = QLabel(bao_sai)
    sai.setStyleSheet(f"color: {CHU_LOI}; font-size: 13px;")
    sai.hide()
    than.addWidget(sai)
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
    def kiem(t: str) -> None:
        co = bool(t.strip())
        dung = co and (hop_le is None or hop_le(t))
        dong_y.setEnabled(dung)
        sai.setVisible(co and not dung and bool(bao_sai))

    o.textChanged.connect(kiem)
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
