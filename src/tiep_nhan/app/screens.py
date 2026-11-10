"""Màn hình M2–M8 (docs/wireframe.md). Không có M1: người dùng tự đăng nhập trong cửa sổ Chromium."""
from __future__ import annotations

import html
import shutil
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ContextManager
from urllib.parse import urlsplit
from zipfile import BadZipFile

from loguru import logger
from openpyxl.utils.exceptions import InvalidFileException
from PySide6.QtCore import QSettings, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QGuiApplication, QIntValidator, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QCompleter, QFileDialog, QFrame,
                               QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QPlainTextEdit, QProgressBar, QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSplitter,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QTextBrowser, QToolButton, QToolTip, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import __version__
from ..core.batch import Lo, nap_lo, xuat_ket_qua
from ..core.runner import RunOptions
from ..core.state import StateStore, TrangThai
from ..domain.chuan_hoa import chuan_ma_phat_hanh, so_phat_hanh_hop_le
from ..domain.danh_muc import DanhMuc
from ..domain.gom_ho_so import CheDoGom
from ..domain.models import HoSo
from ..infra.config import BROWSER_PROFILE, LOG_DIR, STATE_DB, TRACE_DIR, Settings, app_dir, config_file
from ..infra.excel_in import ten_sheet
from ..infra.logging import che_cccd
from ..mplis.locators import Locators
from ..mplis.port import MplisPort
from ..mplis.ui_adapter import PlaywrightMplis
from .giao_dien import (CAM, CHE_DO, CO_TIEU_DE_MAN, LIEN_KET, _font_tieu_de, CHU, CHU_LOI, CHU_MO, CHU_NHAN, CHU_PHU, TRANG, NEN_APP, NEN_BAO_LOI, NEN_DANG_CHAY, NEN_KEO, NEN_THE, NEN_XU_LY_TAY, NHAN,
                        TRANG_THAI, VAI_PHU, VIEN, VIEN_BAO_LOI, VIEN_KEO, VIEN_XU_LY_TAY, ChipLoc, DelegateDong, DelegateHaiDong, DelegateKetQua,
                        DelegateO, DelegateTrangThai, HangSo, NhanRutGon, NhanTrangThai, NutChinh, NutChu, NutNguyHiem, NutPhu, O_TimKiem, The,
                        TheChiSo, bo_dau, che_so_giay_to, dat_thuoc_tinh, dat_tien_do, doan_ket_qua, font_so, hang_nut, hop_nhap, hop_thong_bao,
                        hop_xac_nhan, khop_tim, khung_man, ngay_gio, nhan_icon, rut_gon_ghi_chu, ten_ho_so, tep_trong_ghi_chu, ve_anh,
                        ve_icon)
from .worker import Worker

LO_MOI, KIEM_TRA, DANH_MUC, CHAY, KET_QUA, LICH_SU, CAI_DAT = range(7)
TACH_TEN = " — "  # ô Người xử lý hiện "tài khoản — họ tên"

KHOA = Qt.ItemDataRole.UserRole
VAI_CHI_SO = Qt.ItemDataRole.UserRole + 2
TRANG_THAI_THEO_ENUM = {TrangThai.THANH_CONG: "Thành công", TrangThai.DA_CO_SAN: "Đã có sẵn", TrangThai.CAN_KIEM_TRA: "Cần kiểm tra",
                        TrangThai.LOI: "Lỗi", TrangThai.DA_CHUYEN_NGUOI_KHAC: "Đã chuyển"}
TEN_BANG = {"loai_nha": "Loại nhà", "cap_nha": "Cấp nhà", "ket_cau": "Kết cấu", "thoi_han": "Thời hạn", "xa": "Xã"}
CAN_XU_LY = ("Lỗi", "Cần kiểm tra")
THU_TU_KET_QUA = ("Lỗi", "Cần kiểm tra", "Đã chuyển", "Đã có sẵn", "Thành công", "Chạy thử")


@dataclass
class Phien:
    """Dữ liệu dùng chung giữa các màn hình trong một lần mở ứng dụng."""
    settings: Settings
    store: StateStore
    dm: DanhMuc
    tao_port: Callable[[], ContextManager[MplisPort]]
    dm_path: Path = field(default_factory=lambda: app_dir() / "danh_muc.toml")
    file: Path | None = None
    sheet: str | None = None
    che_do: CheDoGom = CheDoGom.MOI_DONG
    can_bo: str = ""
    lo: Lo | None = None
    ket_qua: dict[str, tuple[str, str, str]] = field(default_factory=dict)  # key -> (trạng thái, ghi chú, mã)
    can_chay: list[HoSo] | None = None  # None = cả lô
    da_reset: bool = False
    dang_chay: bool = False
    che_do_chay: str | None = None      # "thu" | "that" trong lúc đang chạy
    tien_do: tuple[int, int] | None = None  # (hồ sơ đang làm, tổng) trong lúc đang chạy
    lan_chay: dict | None = None        # che_do, file, thoi_gian (ISO), giay: để màn Kết quả mô tả lô

    def nap(self) -> None:
        mac_dinh = {"can_bo": self.can_bo, "thoi_han": self.settings.thoi_han_mac_dinh}
        self.lo = nap_lo(self.file, self.dm, self.che_do, mac_dinh, sheet=self.sheet)

    def nguoi_nhan(self, key: str) -> str:
        return next((hs.dau.ten_chu for hs in self.lo.ho_so if hs.key == key), "") if self.lo else ""


def phien_mac_dinh() -> Phien:
    s = Settings.load()
    L = Locators.doc(config_file("locators.toml"))
    dm = DanhMuc.doc(config_file("danh_muc.toml"))
    return Phien(settings=s, store=StateStore(STATE_DB), dm=dm, tao_port=lambda: PlaywrightMplis(s, L, dm))


# ----- Bảng và ô dùng chung -----
def _bang(*cot: str, rong: int | None = None) -> QTableWidget:
    t = QTableWidget(0, len(cot))
    t.setHorizontalHeaderLabels(cot)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.verticalHeader().hide()
    t.verticalHeader().setDefaultSectionSize(44)
    t.setShowGrid(False)
    tieu_de = t.horizontalHeader()
    tieu_de.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
    tieu_de.setHighlightSections(False)
    tieu_de.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    tieu_de.setSectionResizeMode(len(cot) - 1 if rong is None else rong, QHeaderView.ResizeMode.Stretch)
    return t


def _dien_bang(t: QTableWidget, dong: list[tuple[object, ...]]) -> None:
    t.setRowCount(len(dong))
    for r, d in enumerate(dong):
        for c, v in enumerate(d):
            t.setItem(r, c, QTableWidgetItem("" if v is None else str(v)))


def _o_ho_so(khoa: str, ten_chu: str) -> QTableWidgetItem:
    o = QTableWidgetItem(ten_ho_so(khoa))
    o.setData(KHOA, khoa)
    o.setData(VAI_PHU, ten_chu)
    o.setToolTip(ten_chu)
    return o


def _o_ma(ma: str) -> QTableWidgetItem:
    o = QTableWidgetItem(ma or "—")
    o.setFont(font_so())
    return o


def _o_ghi_chu(ghi_chu: str) -> QTableWidgetItem:
    ngan, day = rut_gon_ghi_chu(ghi_chu)
    o = QTableWidgetItem(ngan)
    o.setToolTip(f"<qt>{html.escape(day)}</qt>" if day else "")  # dạng rich text thì tooltip dài mới tự xuống dòng
    o.setData(KHOA, ghi_chu)  # bản gốc để lấy đường dẫn ảnh, trace
    return o


def _mo(p: str | Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


def _o_nhan(nhan: str, w: QWidget, phu: QWidget | str = "") -> QVBoxLayout:
    """Ô nhập có nhãn nằm trên."""
    lay = QVBoxLayout()
    lay.setSpacing(6)
    t = QLabel(nhan)
    t.setObjectName("nhanO")
    lay.addWidget(t)
    lay.addWidget(w)
    if phu:
        if isinstance(phu, str):
            phu = _chu_phu(phu, xuong_dong=True)
        lay.addSpacing(4)  # ghi chú cách ô ít nhất 8px, không chui dưới ô
        lay.addWidget(phu)
    return lay


def _chu_phu(chu: str = "", xuong_dong: bool = False) -> QLabel:
    o = QLabel(chu)
    o.setObjectName("phu")
    o.setWordWrap(xuong_dong)
    return o


def _tieu_de_the(chu: str) -> QLabel:
    o = QLabel(chu)
    o.setObjectName("tieuDeThe")
    return o


def _ghi_chu_the(ten_icon: str, chu: str) -> The:
    """Hộp ghi chú nền xám, không bóng."""
    hang = QHBoxLayout()
    hang.setSpacing(10)
    hang.addWidget(nhan_icon(ten_icon, CHU_PHU), 0, Qt.AlignmentFlag.AlignTop)
    o = _chu_phu(chu, xuong_dong=True)
    hang.addWidget(o, 1)
    return The(hang, dem=8, nen=NEN_APP)


def _nhom_phan(*ten: str) -> tuple[QFrame, list[QPushButton]]:
    """Nhóm nút phân đoạn; nút đang chọn nền trắng."""
    khung = QFrame()
    khung.setObjectName("nhomPhan")
    lay = QHBoxLayout(khung)
    lay.setContentsMargins(3, 3, 3, 3)
    lay.setSpacing(2)
    nhom = QButtonGroup(khung)
    nut = []
    for t in ten:
        b = QPushButton(t)
        b.setObjectName("phan")
        b.setCheckable(True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        nhom.addButton(b)
        lay.addWidget(b)
        nut.append(b)
    nut[0].setChecked(True)
    return khung, nut


def _xoa_hang(lay: QHBoxLayout) -> None:
    while (x := lay.takeAt(0)) is not None:
        if x.widget():
            x.widget().hide()  # deleteLater chưa xóa ngay: widget đã rời layout sẽ nằm đè lên màn
            x.widget().deleteLater()


def _trang_thai_trong(ten_icon: str, chu: str, *nut: QWidget) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.setSpacing(12)
    icon = nhan_icon(ten_icon, CHU_MO, 40)
    lay.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)
    w.chu = _chu_phu(chu)
    w.chu.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(w.chu)
    for b in nut:
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
    return w


DANG_CHAY_KHONG_XOA = "Đang chạy một lô, chờ chạy xong rồi mới xoá được lịch sử."


def _nut_xoa(bam: Callable[[], None], khoa: bool) -> QToolButton:
    b = QToolButton()
    b.setObjectName("tep")
    b.setIcon(ve_icon("xoa", CHU_PHU, 16))
    b.setFixedSize(30, 30)
    b.setAccessibleName("Xoá khỏi lịch sử")
    b.setToolTip(DANG_CHAY_KHONG_XOA if khoa else "Xoá khỏi lịch sử")
    b.setEnabled(not khoa)
    b.clicked.connect(bam)
    return b


def _xoa_lich_su(man: "ManHinh", ds: list[dict], tat_ca: bool = False) -> bool:
    """Xoá bản ghi lịch sử lô sau khi người dùng xác nhận. Không đụng MPLIS, file Excel hay trạng thái hồ sơ."""
    p = man.p
    if p.dang_chay or not ds:
        return False
    ten = f"{len(ds)} lô" if tat_ca else Path(ds[0]["file"]).name
    if not hop_xac_nhan(man, "Bạn có đồng ý xoá toàn bộ lịch sử?" if tat_ca else "Bạn có đồng ý xoá lô này?", "", [],
                        "Xoá", kieu="nguy_hiem", nut_huy="Huỷ"):
        return False
    if tat_ca:
        p.store.xoa_het_lo()
    else:
        for x in ds:
            p.store.xoa_lo(x["id"])
    logger.info(f"Xoá lịch sử: {ten} ({len(ds)} lần chạy)")
    if p.file and any(Path(x["file"]) == p.file for x in ds):  # xoá đúng lô đang mở thì về Chưa chọn file
        p.file, p.sheet, p.lo, p.ket_qua, p.can_chay, p.lan_chay, p.da_reset = None, None, None, {}, None, None, False
    man.doi.emit()
    return True


class ManHinh(QWidget):
    TIEU_DE, MO_TA, BUOC = "", "", ""
    doi = Signal()  # dữ liệu đổi: cửa sổ chính vẽ lại thanh điều hướng và dải chế độ

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__()
        self.p, self.di_toi = p, di_toi
        self.goc = khung_man(self, self.TIEU_DE, self.MO_TA)
        if self.BUOC:
            self.o_goc.addWidget(NhanTrangThai(self.BUOC, cham=False))

    def phim(self, phim: str, ham: Callable[[], None], cho: QWidget | None = None) -> None:
        """Phím tắt chỉ có tác dụng khi màn này đang hiện."""
        s = QShortcut(QKeySequence(phim), cho or self)
        if cho:
            s.setContext(Qt.ShortcutContext.WidgetShortcut)
        s.activated.connect(ham)

    def hien(self) -> None: ...


class ManLoMoi(ManHinh):
    """M2: chọn file, sheet, chế độ gộp, người xử lý cho cả lô."""
    TIEU_DE, MO_TA, BUOC = "Lô mới", "Chọn file phiếu chuyển và người nhận hồ sơ ở bước Thụ lý.", "Bước 1 / 5"

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.setAcceptDrops(True)
        self.nut_chon = NutChinh("Chọn file Excel…")
        self.nut_chon.clicked.connect(self._chon)
        self.nut_khac = NutPhu("Chọn file khác…")
        self.nut_khac.clicked.connect(self._chon)
        self.trang = QStackedWidget()
        self.trang.addWidget(self._trang_chua_co())
        self.trang.addWidget(self._trang_co_file())
        self.vung = The(self.trang, dem=14, nen=NEN_KEO, vien=VIEN_KEO, day=2, dut=True)
        self.sheet = QComboBox()
        self.che_do = QComboBox()
        self.che_do.addItem("Mỗi dòng một hồ sơ", CheDoGom.MOI_DONG)
        self.che_do.addItem("Gộp các dòng cùng Mã đầu vào", CheDoGom.THEO_MA_DAU_VAO)
        self.can_bo = QComboBox()
        self.can_bo.setEditable(True)
        self.quy_trinh = QComboBox()
        self.quy_trinh.addItem("Chủ đầu tư nộp nhiều hồ sơ (từ 30 hồ sơ trở lên)", "2")
        self.quy_trinh.addItem("Cấp đơn lẻ (dưới 30 hồ sơ)", "1")
        self.quy_trinh.setCurrentIndex(max(self.quy_trinh.findData(p.settings.quy_trinh), 0))
        self.gan_day = QListWidget()
        self.gan_day.setObjectName("ganDay")
        self.gan_day.setSpacing(0)
        self.gan_day.itemActivated.connect(lambda o: self.mo_file(Path(o.data(KHOA))))
        self.gan_day.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.gan_day.customContextMenuRequested.connect(self._menu_gan_day)
        self.rong = _trang_thai_trong("dong_ho", "Chưa có lô nào. Lô bạn chạy sẽ hiện ở đây.")
        self.tiep = NutChinh("Kiểm tra dữ liệu →")
        self.tiep.setEnabled(False)
        self.tiep.setToolTip("Chọn file Excel trước")
        self.tiep.clicked.connect(self._sang_kiem_tra)

        luoi = QGridLayout()
        luoi.setHorizontalSpacing(16)
        luoi.setVerticalSpacing(18)
        luoi.addLayout(_o_nhan("Sheet", self.sheet), 0, 0)
        luoi.addLayout(_o_nhan("Chế độ gộp", self.che_do), 0, 1)
        ghi_chu = _ghi_chu_the("thong_tin", '<b>Người nộp</b> lấy từ cột "Người nộp" trong Excel; ô trống thì tra theo người nhận.')
        luoi.addLayout(_o_nhan("Quy trình 1.012787", self.quy_trinh), 1, 0, 1, 2)
        luoi.addLayout(_o_nhan("Người xử lý tác vụ tiếp theo", self.can_bo, ghi_chu), 2, 0, 1, 2)
        the_lap = The(_tieu_de_the("Thiết lập lô"), luoi)
        the_lap.layout().addStretch(1)
        xem_het = NutChu("Xem tất cả")
        xem_het.clicked.connect(lambda: self.di_toi(LICH_SU))
        dau = QHBoxLayout()
        dau.addWidget(_tieu_de_the("Lô gần đây"))
        dau.addStretch(1)
        dau.addWidget(xem_het)
        the_gan = The(dau, self.gan_day, self.rong)
        giua = QHBoxLayout()
        giua.setSpacing(0)
        giua.addWidget(the_lap, 3)
        giua.addWidget(the_gan, 2)
        lay = self.goc
        lay.addWidget(self.vung)
        lay.addLayout(giua, 1)
        hang_nut(lay, _chu_phu("Ctrl + Enter"), self.tiep)
        for a, b in ((self.nut_chon, self.sheet), (self.sheet, self.che_do), (self.che_do, self.can_bo), (self.can_bo, self.gan_day),
                     (self.gan_day, self.tiep)):
            QWidget.setTabOrder(a, b)
        self.phim("Ctrl+Return", self._phim_tiep)
        self.phim("Ctrl+O", self._chon)

    def _trang_chua_co(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(nhan_icon("excel", NHAN, 32))
        to = QLabel("Kéo thả file phiếu chuyển (.xlsx) vào đây")
        to.setObjectName("tieuDeThe")
        lay.addWidget(to)
        lay.addWidget(_chu_phu("hoặc"))
        lay.addWidget(self.nut_chon)
        lay.addStretch(1)
        return w

    def _trang_co_file(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(nhan_icon("excel", NHAN, 32))
        cot = QVBoxLayout()
        cot.setSpacing(0)
        self.ten_file = QLabel()
        self.ten_file.setObjectName("tieuDeThe")
        self.nhan_doc = NhanTrangThai("Đọc được")
        hang = QHBoxLayout()
        hang.setSpacing(10)
        hang.addWidget(self.ten_file)
        hang.addWidget(self.nhan_doc)
        hang.addStretch(1)
        self.phu_file = _chu_phu()
        goi_y = _chu_phu("Kéo thả file .xlsx khác vào khung này để đổi.")
        duoi = QHBoxLayout()  # số cột và gợi ý chung một dòng để khung chỉ cao bằng nửa trước
        duoi.setSpacing(6)
        duoi.addWidget(self.phu_file)
        duoi.addWidget(_chu_phu("·"))
        duoi.addWidget(goi_y)
        duoi.addStretch(1)
        cot.addLayout(hang)
        cot.addLayout(duoi)
        lay.addLayout(cot, 1)
        lay.addWidget(self.nut_khac)
        return w

    def hien(self) -> None:
        if self.p.file is None:  # lô đang mở vừa bị xoá khỏi lịch sử
            self.trang.setCurrentIndex(0)
            self.sheet.clear()
            self.tiep.setEnabled(False)
            self.tiep.setToolTip("Chọn file Excel trước")
        hien_tai = self.can_bo.currentText()
        self.can_bo.clear()
        danh_ba = self.p.settings.danh_ba_can_bo
        gan_day = self.p.settings.ds_can_bo  # dùng gần đây lên đầu, sau đó toàn bộ danh sách lấy từ MPLIS
        ds = gan_day + sorted((u for u in danh_ba if u not in gan_day), key=lambda u: bo_dau(danh_ba[u] or u))
        self.can_bo.addItems([f"{u}{TACH_TEN}{danh_ba[u]}" if danh_ba.get(u) else u for u in ds])
        goi_y = QCompleter(self.can_bo.model(), self.can_bo)
        goi_y.setFilterMode(Qt.MatchFlag.MatchContains)
        goi_y.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.can_bo.setCompleter(goi_y)
        if hien_tai:
            self.can_bo.setCurrentText(hien_tai)
        self.gan_day.clear()
        theo_file: dict[str, dict] = {}
        for x in self.p.store.ds_lo():  # ds_lo sắp mới nhất trước: giữ lần chạy gần nhất của mỗi file
            theo_file.setdefault(x["file"], x)
        for x in list(theo_file.values())[:5]:
            o = QListWidgetItem()
            o.setData(KHOA, x["file"])
            o.setData(VAI_CHI_SO, x["id"])
            the = self._the_lo(x)
            o.setSizeHint(QSize(0, the.sizeHint().height()))
            self.gan_day.addItem(o)
            self.gan_day.setItemWidget(o, the)
        co = self.gan_day.count() > 0
        self.gan_day.setVisible(co)
        self.rong.setVisible(not co)
        self._chinh_cao_gan_day()

    def _chinh_cao_gan_day(self) -> None:
        """Chiều cao từng thẻ tính theo bề rộng thật, để dòng thống kê xuống dòng mà không dư khoảng trống."""
        rong = self.gan_day.viewport().width()
        for i in range(self.gan_day.count()):
            o = self.gan_day.item(i)
            the = self.gan_day.itemWidget(o)
            if the is not None and rong > 50:
                o.setSizeHint(QSize(0, the.heightForWidth(rong) if the.hasHeightForWidth() else the.sizeHint().height()))

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._chinh_cao_gan_day()

    def _the_lo(self, x: dict) -> The:
        ten = NhanRutGon(Path(x["file"]).name)
        ten.setObjectName("tieuDeThe")
        hang = QHBoxLayout()
        hang.setSpacing(8)
        hang.addWidget(ten, 1)
        hang.addWidget(NhanTrangThai(x["che_do"], cham=False))
        hang.addWidget(_nut_xoa(lambda: self.xoa_gan_day(x["id"]), self.p.dang_chay))
        tt = html.escape(x["tom_tat"].lower())
        phu = _chu_phu(f'<div style="line-height:140%">{ngay_gio(x["thoi_gian"])} · {x["so_ho_so"]} hồ sơ · {tt}</div>', xuong_dong=True)
        phu.setTextFormat(Qt.TextFormat.RichText)
        the = The(hang, phu, dem=8, nen=NEN_APP)
        the.layout().setSpacing(6)
        return the

    def _menu_gan_day(self, vi_tri) -> None:
        o = self.gan_day.itemAt(vi_tri)
        if not o:
            return
        m = QMenu(self)
        m.addAction("Mở lại", lambda: self.mo_file(Path(o.data(KHOA))))
        a = m.addAction(ve_icon("xoa", CHU_PHU), "Xoá", lambda: self.xoa_gan_day(o.data(VAI_CHI_SO)))
        a.setEnabled(not self.p.dang_chay)
        m.exec(self.gan_day.viewport().mapToGlobal(vi_tri))

    def xoa_gan_day(self, id_: int) -> None:
        """Thẻ gộp mọi lần chạy của một file, nên xoá thẻ là xoá hết các lần chạy đó (không thì lần cũ hơn lại hiện lên)."""
        ds = self.p.store.ds_lo()
        x = next((r for r in ds if r["id"] == id_), None)
        if x and _xoa_lich_su(self, [r for r in ds if r["file"] == x["file"]]):
            self.hien()

    def _hop_le(self, e) -> list[Path]:
        return [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.toLocalFile().lower().endswith((".xlsx", ".xlsm"))]

    def dragEnterEvent(self, e) -> None:
        if self._hop_le(e):
            e.acceptProposedAction()
            self.vung.dat(vien=CHU, dut=False)

    def dragLeaveEvent(self, e) -> None:
        self.vung.dat(vien=VIEN_KEO, dut=True)

    def dropEvent(self, e) -> None:
        self.vung.dat(vien=VIEN_KEO, dut=True)
        self.mo_file(self._hop_le(e)[0])

    def _chon(self) -> None:
        cu = QSettings("NhapPhieuMPLIS", "giao_dien")
        f, _ = QFileDialog.getOpenFileName(self, "Chọn file Excel", str(cu.value("thu_muc_mo", "")), "Excel (*.xlsx *.xlsm)")
        if f:
            cu.setValue("thu_muc_mo", str(Path(f).parent))
            self.mo_file(Path(f))

    def _bao_loi(self, f: Path, ly_do: str) -> None:
        self.trang.setCurrentIndex(1)
        self.ten_file.setText(f.name)
        self.nhan_doc.dat("Không đọc được", "Lỗi")
        self.phu_file.setText(ly_do[:120] + ("…" if len(ly_do) > 120 else ""))
        self.phu_file.setToolTip(ly_do)
        self.tiep.setEnabled(False)
        self.tiep.setToolTip("Chọn file Excel trước")

    def mo_file(self, f: Path) -> None:
        if self.p.dang_chay:  # đổi file giữa lúc chạy làm lịch sử ghi nhầm tên lô và mất kết quả
            return
        try:
            ds = ten_sheet(f)
        except (OSError, BadZipFile, InvalidFileException, KeyError) as e:
            self._bao_loi(f, str(e))
            return
        chon = next((x for x in ds if bo_dau(x).startswith("phieu chuyen")), ds[0])
        self.p.file, self.p.sheet = f, chon
        self.sheet.clear()
        self.sheet.addItems(ds)
        self.sheet.setCurrentText(chon)
        self.p.nap()
        d = self.p.lo.doc
        if not d:
            ly_do = next((v.noi_dung for v in self.p.lo.van_de), "Không nhận diện được cấu trúc file.")
            self._bao_loi(f, ly_do)
            return
        self.trang.setCurrentIndex(1)
        self.ten_file.setText(f.name)
        self.nhan_doc.dat("✓ Đọc được", "Thành công")
        self.phu_file.setText(f"Nhận diện {len(d.columns)} cột · {len(d.rows)} dòng dữ liệu")
        self.phu_file.setToolTip("")
        self.tiep.setEnabled(True)
        self.tiep.setToolTip("")

    def _phim_tiep(self) -> None:
        if self.tiep.isEnabled():
            self._sang_kiem_tra()

    def _sang_kiem_tra(self) -> None:
        p = self.p
        if p.dang_chay:
            return
        p.sheet, p.che_do = self.sheet.currentText(), CheDoGom(self.che_do.currentData())
        p.can_bo = self.can_bo.currentText().split(TACH_TEN)[0].strip()  # chỉ tài khoản; họ tên chỉ để dễ tìm
        if p.can_bo:
            p.settings.ds_can_bo = [p.can_bo] + [x for x in p.settings.ds_can_bo if x != p.can_bo]
        p.settings.quy_trinh = self.quy_trinh.currentData()
        p.settings.save()
        p.ket_qua, p.can_chay, p.da_reset, p.lan_chay = {}, None, False, None
        p.nap()
        self.di_toi(KIEM_TRA)


class ManKiemTra(ManHinh):
    """M3: số hợp lệ/lỗi/cảnh báo, bảng hồ sơ, xem trước, lỗi nhóm theo BR."""
    TIEU_DE, BUOC = "Kiểm tra dữ liệu", "Bước 2 / 5"
    MO_TA = "Chọn một hồ sơ để xem chi tiết. Lỗi chặn phải được sửa trong Excel trước khi chạy."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.tong = HangSo()  # giữ để đọc tổng dạng chữ; ba thẻ bấm được bên dưới mới là phần hiển thị
        self.tong.setParent(self)
        self.tong.hide()
        self.loc: str | None = None
        self.loc_ma: str | None = None
        self.van_de_theo_khoa: dict[str, list] = {}

        self.chu_loi = QLabel()
        self.chu_loi.setWordWrap(True)
        doc_lai = NutNguyHiem("Đọc lại file", ve_icon("doc_lai", CHU_PHU))
        doc_lai.clicked.connect(self._doc_lai)
        hang = QHBoxLayout()
        hang.setSpacing(12)
        hang.addWidget(nhan_icon("canh_bao", CHU_LOI, 20))
        hang.addWidget(self.chu_loi, 1)
        hang.addWidget(doc_lai)
        self.dai_loi = The(hang, dem=4, bong=False, nen=NEN_BAO_LOI, vien=VIEN_BAO_LOI)
        self.the_hop_le = TheChiSo(0, "Hợp lệ", TRANG_THAI["Thành công"], "xong")
        self.the_loi = TheChiSo(0, "Lỗi · chặn chạy", TRANG_THAI["Lỗi"], "loi")
        self.the_cb = TheChiSo(0, "Cảnh báo · không chặn", TRANG_THAI["Cần kiểm tra"], "canh_bao")
        self.the_hop_le.clicked.connect(lambda: self._chon_the(None))
        self.the_loi.clicked.connect(lambda: self._chon_the("loi"))
        self.the_cb.clicked.connect(lambda: self._chon_the("canh_bao"))
        so = QHBoxLayout()
        so.setSpacing(0)
        for x in (self.the_hop_le, self.the_loi, self.the_cb):
            so.addWidget(x, 1)

        self.bang = _bang("Dòng", "Hồ sơ", "Người nhận", "Kiểm tra", rong=2)
        self.bang.setItemDelegateForColumn(3, DelegateTrangThai(self.bang))
        self.bang.itemSelectionChanged.connect(self._xem)
        self.bang.itemDoubleClicked.connect(lambda _o: self.p.file and _mo(self.p.file))
        self.bang.horizontalHeader().sortIndicatorChanged.connect(lambda *_: self._ap_loc())  # ẩn dòng theo vị trí nên sắp xong phải lọc lại
        self.cay = QTreeWidget()
        self.cay.setColumnCount(4)
        self.cay.setHeaderHidden(True)
        self.cay.setWordWrap(True)
        self.cay.setColumnWidth(0, 130)
        self.cay.setColumnWidth(1, 110)
        self.cay.setColumnWidth(2, 140)
        self.cay.setItemDelegateForColumn(1, DelegateTrangThai(self.cay))
        self.cay.itemClicked.connect(self._chon_ma)
        self.xem = QTextBrowser()
        self.xem.setOpenLinks(False)
        cot_trai = QVBoxLayout()
        cot_trai.setSpacing(0)
        cot_trai.addWidget(The(self.bang, dem=8), 3)
        cot_trai.addWidget(The(_tieu_de_the("Lỗi và cảnh báo theo mã"), self.cay, dem=14), 2)
        giua = QHBoxLayout()
        giua.setSpacing(0)
        giua.addLayout(cot_trai, 3)
        giua.addWidget(The(self.xem, dem=14), 2)
        self.quay = NutPhu("Quay lại")
        self.quay.clicked.connect(lambda: self.di_toi(LO_MOI))
        self.tiep = NutChinh("Tiếp tục")
        self.tiep.clicked.connect(self._tiep)
        lay = self.goc
        lay.addWidget(self.dai_loi)
        lay.addLayout(so)
        lay.addLayout(giua, 1)
        hang_nut(lay, self.tiep, trai=(self.quay,))
        self.phim("F5", self._doc_lai)

    def _dau_loi(self, loi: list, lo: Lo) -> str:
        n = len(loi)
        dong = list(dict.fromkeys(v.excel_row for v in loi))
        if len(dong) == 1:
            hs = next((h for h in lo.ho_so if dong[0] in h.excel_rows), None)
            ten = f"Tờ {hs.dau.thua.so_to}, thửa {hs.dau.thua.so_thua}, " if hs else ""
            vi_tri = f"ở dòng {dong[0]} ({ten}mã {loi[0].ma})"
        else:
            hien = ", ".join(map(str, dong[:3]))
            vi_tri = f"ở {len(dong)} dòng: {hien}{'…' if len(dong) > 3 else ''}"
        chi_can_anh_xa = all(v.ma == "BR-05" and "chưa ánh xạ" in v.noi_dung for v in loi)
        huong_dan = "Chọn giá trị ở bước Ánh xạ danh mục." if chi_can_anh_xa else "Sửa trong Excel, lưu file rồi bấm Đọc lại."
        return f"<b>{n} lỗi chặn chạy</b> {vi_tri}. {huong_dan}"

    def hien(self) -> None:
        lo = self.p.lo
        self.bang.setSortingEnabled(False)
        self.bang.setRowCount(0)
        self.cay.clear()
        self.xem.clear()
        self.tiep.setEnabled(False)
        self.loc, self.loc_ma = None, None
        self._dong_bo_the()
        self.dai_loi.setVisible(False)
        if not lo:
            self.tong.dat([], "Chưa chọn file. Hãy bắt đầu ở màn Lô mới.")
            for x in (self.the_hop_le, self.the_loi, self.the_cb):
                x.dat(0)
            self.xem.setPlainText("Chưa chọn file. Hãy bắt đầu ở màn Lô mới.")
            return
        loi = [v for v in lo.van_de if v.muc == "loi"]
        cb = [v for v in lo.van_de if v.muc != "loi"]
        self.tong.dat([("Hợp lệ", len(lo.ho_so), ""), ("Lỗi", len(loi), ""), ("Cảnh báo", len(cb), "")])
        self.the_hop_le.dat(len(lo.ho_so))
        self.the_loi.dat(len(loi))
        self.the_cb.dat(len(cb))
        if loi:
            self.chu_loi.setText(self._dau_loi(loi, lo))
            self.dai_loi.setVisible(True)
        self.van_de_theo_khoa = {hs.key: [v for v in lo.van_de if v.excel_row in hs.excel_rows] for hs in lo.ho_so}

        def hang(hs: HoSo) -> int:
            ds = self.van_de_theo_khoa[hs.key]
            return 0 if any(v.muc == "loi" for v in ds) else 1 if ds else 2

        def ket_qua(hs: HoSo) -> str:
            ds = self.van_de_theo_khoa[hs.key]
            n_cb = sum(v.muc != "loi" for v in ds)
            if any(v.muc == "loi" for v in ds):
                return f"Lỗi chặn · {n_cb} cảnh báo" if n_cb else "Lỗi chặn"
            return f"{n_cb} cảnh báo" if n_cb else "Tốt"

        ds_hs = sorted(lo.ho_so, key=hang)
        self.bang.setRowCount(len(ds_hs))
        for r, hs in enumerate(ds_hs):
            so_dong = QTableWidgetItem()
            so_dong.setData(Qt.ItemDataRole.DisplayRole, hs.dau.excel_row)
            so_dong.setData(KHOA, hs.key)
            self.bang.setItem(r, 0, so_dong)
            self.bang.setItem(r, 1, QTableWidgetItem(f"Tờ {hs.dau.thua.so_to}, thửa {hs.dau.thua.so_thua}"))
            self.bang.setItem(r, 2, QTableWidgetItem(hs.dau.ten_chu))
            self.bang.setItem(r, 3, QTableWidgetItem(ket_qua(hs)))
        self.bang.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.bang.setSortingEnabled(True)
        nhom: dict[tuple[str, str], list] = {}
        for v in lo.van_de:
            nhom.setdefault((v.ma, "Lỗi" if v.muc == "loi" else "Cảnh báo"), []).append(v)
        for (ma, muc), ds in sorted(nhom.items(), key=lambda x: (x[0][1] != "Lỗi", x[0][0])):
            dong = list(dict.fromkeys(v.excel_row for v in ds))
            so = "Cả file" if dong == [0] else f"1 dòng: {dong[0]}" if len(ds) == 1 else f"{len(ds)} lần"
            g = QTreeWidgetItem([ma, muc, so, "Chọn dòng"])
            g.setFont(0, font_so(13, QFont.Weight.DemiBold))
            g.setForeground(3, QColor(LIEN_KET))
            g.setData(0, KHOA, ma)
            for v in ds:
                g.addChild(QTreeWidgetItem([f"Dòng {v.excel_row}: {che_so_giay_to(v.noi_dung)}"]))
            self.cay.addTopLevelItem(g)
            for i in range(g.childCount()):
                g.child(i).setFirstColumnSpanned(True)
        self.tiep.setEnabled(bool(lo.ho_so) and not [v for v in loi if v.ma != "BR-05"])
        con_anh_xa = self.p.dm.chua_anh_xa(lo.ho_so)
        self.tiep.setText("Tiếp tục: Ánh xạ danh mục →" if con_anh_xa else "Tiếp tục: Chạy →")
        if self.bang.rowCount():
            self.bang.selectRow(0)
        self.doi.emit()

    def _dong_bo_the(self) -> None:
        self.the_loi.setChecked(self.loc == "loi")
        self.the_cb.setChecked(self.loc == "canh_bao")
        self.the_hop_le.setChecked(False)

    def _chon_the(self, loai: str | None) -> None:
        self.loc = None if loai == self.loc else loai
        self.loc_ma = None
        self._dong_bo_the()
        self._ap_loc()

    def _chon_ma(self, o: QTreeWidgetItem, _cot: int) -> None:
        ma = o.data(0, KHOA)
        if not ma:
            return
        self.loc_ma = None if ma == self.loc_ma else ma
        self.loc = None
        self._dong_bo_the()
        self._ap_loc()

    def _ap_loc(self) -> None:
        dau_tien = None
        for r in range(self.bang.rowCount()):
            ds = self.van_de_theo_khoa.get(self.bang.item(r, 0).data(KHOA), [])
            giu = ((self.loc != "loi" or any(v.muc == "loi" for v in ds)) and (self.loc != "canh_bao" or any(v.muc != "loi" for v in ds))
                   and (not self.loc_ma or any(v.ma == self.loc_ma for v in ds)))
            self.bang.setRowHidden(r, not giu)
            if giu and dau_tien is None:
                dau_tien = r
        if dau_tien is not None and self.bang.isRowHidden(self.bang.currentRow()):
            self.bang.selectRow(dau_tien)

    def _doc_lai(self) -> None:
        if self.p.file and not self.p.dang_chay:
            self.p.nap()
            self.hien()

    def _xem(self) -> None:
        r = self.bang.currentRow()
        if r < 0 or not self.p.lo:
            return
        khoa = self.bang.item(r, 0).data(KHOA)
        hs = next(h for h in self.p.lo.ho_so if h.key == khoa)
        d = hs.dau
        e = html.escape
        chua_co = f'<span style="color:{CHU_PHU}">Chưa có</span>'
        dt = str(d.thua.dien_tich).replace(".", ",") + " m²" if d.thua.dien_tich else chua_co
        hang = [("Địa chỉ", e(d.thua.dia_chi or "") or chua_co), ("Diện tích", dt), ("Số phát hành", e(d.thua.ma_phat_hanh or "") or chua_co),
                ("Cán bộ XL", e(d.can_bo or "") or chua_co), ("Người nộp", e(d.nguoi_nop.ho_ten))]
        o = "".join(f'<tr><td width="110" style="color:{CHU_PHU};padding:3px 0">{a}</td><td style="padding:3px 0">{b}</td></tr>' for a, b in hang)
        nhan = f'<div style="color:{CHU_NHAN};font-size:12px;font-weight:600;margin-top:14px">%s</div>'
        nguoi = "".join(f'<div style="margin-top:4px"><b>{e(n.ho_ten)}</b> · Sinh {n.nam_sinh or "—"} · CCCD {che_cccd(n.cccd)}</div>' for n in d.nguoi)
        gop: dict[tuple[str, str], list[str]] = {}
        for v in self.van_de_theo_khoa.get(khoa, []):
            gop.setdefault((v.ma, v.muc), []).append(che_so_giay_to(v.noi_dung))
        vd = ""
        for (ma, muc), ds in sorted(gop.items(), key=lambda x: x[0][1] != "loi"):
            mau = TRANG_THAI["Lỗi" if muc == "loi" else "Cần kiểm tra"][0]
            lan = f" · {len(ds)} lần" if len(ds) > 1 else ""
            vd += f'<div style="margin-top:6px"><b style="color:{mau}">{e(ma)}</b> {e("; ".join(dict.fromkeys(ds)))}{lan}</div>'
        self.xem.setHtml(f'<div style="color:{CHU_PHU};font-size:12px">Dòng {d.excel_row} trong Excel</div>'
                         f'<div style="font-size:18px;font-weight:500">Tờ {d.thua.so_to}, thửa {d.thua.so_thua}</div>'
                         f'<table cellspacing="0" style="margin-top:8px">{o}</table>'
                         f'{nhan % "NGƯỜI NHẬN"}{nguoi}' + (f'{nhan % "VẤN ĐỀ CỦA HỒ SƠ NÀY"}{vd}' if vd else ""))

    def _tiep(self) -> None:
        self.di_toi(DANH_MUC if self.p.dm.chua_anh_xa(self.p.lo.ho_so) else CHAY)


class ManDanhMuc(ManHinh):
    """M4: gán giá trị MPLIS cho giá trị Excel chưa có, lưu vào danh_muc.toml của người dùng."""
    TIEU_DE, BUOC = "Ánh xạ danh mục", "Bước 3 / 5"
    MO_TA = "Chọn giá trị trên MPLIS tương ứng với chữ trong Excel. Lựa chọn được lưu và dùng lại cho các lô sau."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.nhan = QLabel()
        self.nhan.setObjectName("tieuDeThe")
        self.so_cho = _chu_phu()
        self.tien_do = QProgressBar()
        self.tien_do.setObjectName("manh")
        self.chip_chua, self.chip_het = ChipLoc("Chưa chọn"), ChipLoc("Tất cả")
        self.chip_chua.setChecked(True)
        nhom = QButtonGroup(self)
        nhom.addButton(self.chip_chua)
        nhom.addButton(self.chip_het)
        nhom.buttonClicked.connect(lambda _b: self._ap_loc())
        dau = QHBoxLayout()
        dau.setSpacing(12)
        dau.addWidget(self.nhan)
        dau.addWidget(self.so_cho, 1)
        dau.addWidget(self.chip_chua)
        dau.addWidget(self.chip_het)
        self.the_tien_do = The(dau, self.tien_do, dem=12)
        self.bang = _bang("Trường", "Chữ trong Excel", "Số hồ sơ", "Giá trị trên MPLIS")
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.bang.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tieu_de = self.bang.horizontalHeader()
        for c in range(3):
            tieu_de.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
        self.bang.verticalHeader().setDefaultSectionSize(56)
        self.bang.setItemDelegateForColumn(1, DelegateO(self.bang))
        self.bang.cellClicked.connect(self._hien_ho_so)
        tiep = NutChinh("Tiếp tục: Chạy →")
        tiep.clicked.connect(lambda: self.di_toi(CHAY))
        self.rong = _trang_thai_trong("xong", "Tất cả giá trị đã có đích trên MPLIS.", tiep)
        self.the_bang = The(self.bang, self.rong, dem=8)
        self.goi_y = _chu_phu()
        self.nut_luu = NutChinh("Lưu và kiểm tra lại")
        self.nut_luu.clicked.connect(self.luu)
        quay = NutPhu("Quay lại")
        quay.clicked.connect(lambda: self.di_toi(KIEM_TRA))
        lay = self.goc
        lay.addWidget(self.the_tien_do)
        lay.addWidget(self.the_bang, 1)
        hang_nut(lay, self.goi_y, self.nut_luu, trai=(quay,))
        self.phim("Ctrl+S", self.luu)

    def _combo(self, ds: list[str]) -> QComboBox:
        o = QComboBox()
        o.setEditable(True)
        o.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        o.addItems(ds)
        o.setCurrentIndex(-1)  # không để mục đầu tiên trông như đã chọn
        o.lineEdit().setPlaceholderText("Gõ để tìm trong danh mục MPLIS…")
        goi_y = QCompleter(ds, o)
        goi_y.setFilterMode(Qt.MatchFlag.MatchContains)
        goi_y.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        o.setCompleter(goi_y)
        o.dau_xong = o.lineEdit().addAction(ve_icon("xong", TRANG_THAI["Thành công"][2]), QLineEdit.ActionPosition.TrailingPosition)
        o.currentTextChanged.connect(lambda _t: self._cap_nhat_o(o))
        o.lineEdit().returnPressed.connect(self.focusNextChild)
        self._cap_nhat_o(o, dem=False)
        return o

    def _cap_nhat_o(self, o: QComboBox, dem: bool = True) -> None:
        co = bool(o.currentText().strip())
        dat_thuoc_tinh(o, "chuaChon", "false" if co else "true")
        o.dau_xong.setVisible(co)
        o.setToolTip("" if co else "Chưa chọn. Hồ sơ dùng giá trị này sẽ không chạy được.")
        if dem:
            self._cap_nhat_dem()

    def _chia_cot(self) -> None:
        w = self.bang.viewport().width()
        self.bang.setColumnWidth(0, max(140, int(w * 0.22)))
        self.bang.setColumnWidth(1, max(140, int(w * 0.22)))
        self.bang.setColumnWidth(2, 90)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._chia_cot()

    def hien(self) -> None:
        lo = self.p.lo
        thieu = self.p.dm.chua_anh_xa(lo.ho_so) if lo else {}
        self.dong = list(thieu)
        self.dong_excel = thieu
        self.bang.setRowCount(len(self.dong))
        for r, (b, gv) in enumerate(self.dong):
            ten = QTableWidgetItem(TEN_BANG.get(b, b))
            f = ten.font()
            f.setBold(True)
            ten.setFont(f)
            self.bang.setItem(r, 0, ten)
            self.bang.setItem(r, 1, QTableWidgetItem(gv))
            so = QTableWidgetItem(str(len(thieu[(b, gv)])))
            so.setForeground(QColor(LIEN_KET))
            so.setToolTip(self._ds_ho_so(thieu[(b, gv)]))
            self.bang.setItem(r, 2, so)
            self.bang.setCellWidget(r, 3, self._combo(self.p.dm.bang(b)))
        co = bool(self.dong)
        self.bang.setVisible(co)
        self.the_tien_do.setVisible(co)
        self.nut_luu.setVisible(co)
        self.rong.setVisible(not co)
        self.rong.chu.setText("Tất cả giá trị đã có đích trên MPLIS." if lo else "Chưa chọn file. Hãy bắt đầu ở màn Lô mới.")
        self.chip_chua.setChecked(True)
        self._chia_cot()
        self._cap_nhat_dem()
        self._ap_loc()

    def _ds_ho_so(self, dong: list[int]) -> str:
        ten = dict.fromkeys(f"Tờ {hs.dau.thua.so_to}, thửa {hs.dau.thua.so_thua}" for hs in self.p.lo.ho_so if set(hs.excel_rows) & set(dong))
        return "; ".join(ten)

    def _hien_ho_so(self, r: int, c: int) -> None:
        if c == 2:
            QToolTip.showText(self.bang.viewport().mapToGlobal(self.bang.visualRect(self.bang.model().index(r, c)).bottomLeft()),
                              self.bang.item(r, c).toolTip(), self.bang)

    def _da_chon(self, r: int) -> bool:
        return bool(self.bang.cellWidget(r, 3).currentText().strip())

    def _cap_nhat_dem(self) -> None:
        n = len(self.dong)
        x = sum(self._da_chon(r) for r in range(n))
        ho_so = len({d for r in range(n) if not self._da_chon(r) for d in self.dong_excel[self.dong[r]]})
        self.nhan.setText(f"Đã ánh xạ {x} / {n} giá trị")
        self.so_cho.setText(f"{ho_so} hồ sơ đang chờ")
        self.tien_do.setRange(0, max(n, 1))
        self.tien_do.setValue(x)
        self.chip_chua.dat_so(n - x)
        self.chip_het.dat_so(n)
        self.goi_y.setText(f"Chọn đủ {n} giá trị để tiếp tục" if x < n else "")

    def _ap_loc(self) -> None:
        # chỉ lọc khi bấm chip: đang chọn mà dòng biến mất ngay thì rất khó thao tác
        for r in range(len(self.dong)):
            self.bang.setRowHidden(r, self.chip_chua.isChecked() and self._da_chon(r))

    def luu(self) -> None:
        if self.p.dang_chay:
            return
        them = [(b, gv, self.bang.cellWidget(r, 3).currentText().strip()) for r, (b, gv) in enumerate(self.dong)]
        them = [x for x in them if x[2] and x[2] != "TODO"]
        if not them:
            return
        for x in them:
            self.p.dm.them(*x)
        self.p.dm.luu(self.p.dm_path)
        self.p.nap()
        if self.p.dm.chua_anh_xa(self.p.lo.ho_so):
            self.hien()
        else:
            self.di_toi(KIEM_TRA)
        self.doi.emit()


class _TheCheDo(The):
    """Thẻ chọn chế độ: bấm vào đâu trên thẻ cũng chọn."""

    def __init__(self, nut: QRadioButton, che_do: str, mo_ta: str):
        self.nut, self.cd = nut, CHE_DO[che_do]
        nut.setStyleSheet(f"QRadioButton {{ color: {self.cd['chu']}; font-size: 18px; font-weight: 500; }}")
        phu = _chu_phu(mo_ta, xuong_dong=True)
        phu.setIndent(32)
        super().__init__(nut, phu, dem=10)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mo = QGraphicsOpacityEffect(self)
        self.mo.setOpacity(1)
        self.setGraphicsEffect(self.mo)
        self.lam_moi()

    def mousePressEvent(self, e) -> None:
        if self.isEnabled():
            self.nut.setChecked(True)

    def lam_moi(self) -> None:
        chon = self.nut.isChecked()
        self.dat(nen=self.cd["nen_nhat"] if chon else NEN_THE, vien=self.cd["chu"] if chon else VIEN, day=2 if chon else 1)
        self.mo.setOpacity(0.55 if not self.isEnabled() and not chon else 1)


class ManChay(ManHinh):
    """M5: chạy thử hoặc chạy thật. Mặc định chạy thử; chạy thật phải xác nhận."""
    TIEU_DE, MO_TA, BUOC = "Chạy", "Chạy thử để xem form đã điền. Chạy thật mới tạo hồ sơ trên MPLIS.", "Bước 4 / 5"

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.worker: Worker | None = None
        self.hang: dict[str, int] = {}
        self.dang = ""
        self.t_dau = 0.0
        self.r_thu, self.r_that = QRadioButton("Chạy thử"), QRadioButton("Chạy thật")
        self.r_thu.setChecked(True)
        self.nhom = QButtonGroup(self)
        self.nhom.addButton(self.r_thu)
        self.nhom.addButton(self.r_that)
        self.the_thu = _TheCheDo(self.r_thu, "thu", "Điền form, không Lưu. Dùng để soát trước khi chạy thật.")
        self.the_that = _TheCheDo(self.r_that, "that", "Lưu lên MPLIS, tạo hồ sơ thật. Hỏi xác nhận trước khi bắt đầu.")
        self.r_thu.toggled.connect(lambda _c: self._doi_che_do())
        chon = QHBoxLayout()
        chon.setSpacing(0)
        chon.addWidget(self.the_thu, 1)
        chon.addWidget(self.the_that, 1)

        self.so_lon = QLabel("0")
        self.so_lon.setFont(_font_tieu_de(CO_TIEU_DE_MAN))
        self.tren_so = _chu_phu("/ 0 hồ sơ")
        self.dang_chu = QLabel("Sẵn sàng")
        self.dang_chu.setStyleSheet("font-weight: 600;")
        self.uoc = _chu_phu("Mỗi hồ sơ mất khoảng 3–4 phút")
        for o in (self.dang_chu, self.uoc):  # tên người nhận dài không được đẩy cửa sổ rộng ra
            o.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.gioi_han = QLineEdit()
        self.gioi_han.setPlaceholderText("Tất cả")
        self.gioi_han.setValidator(QIntValidator(1, 9999, self.gioi_han))
        self.gioi_han.setFixedWidth(82)
        self.chay = NutChinh("Bắt đầu chạy thử", ve_icon("chay", TRANG))
        self.chay.clicked.connect(self.bat_dau)
        self.dung = NutPhu("Dừng sau hồ sơ này", ve_icon("tam_dung", CHU_PHU))
        self.dung.hide()
        self.dung.clicked.connect(self._dung)
        giua = QVBoxLayout()
        giua.setSpacing(2)
        giua.addWidget(self.dang_chu)
        giua.addWidget(self.uoc)
        tren = QHBoxLayout()
        tren.setSpacing(10)
        tren.addWidget(self.so_lon)
        tren.addWidget(self.tren_so)
        tren.addSpacing(14)
        tren.addLayout(giua, 1)
        tren.addWidget(QLabel("Chạy tối đa"))
        tren.addWidget(self.gioi_han)
        tren.addWidget(QLabel("hồ sơ"))
        tren.addWidget(self.dung)
        tren.addWidget(self.chay)
        self.tien_do = QProgressBar()
        self.tien_do.setFormat("%v/%m hồ sơ")
        self.tien_do.setAccessibleName("Tiến độ chạy")
        self.hang_dem = QHBoxLayout()
        self.hang_dem.setSpacing(8)
        self.chu_loi = QLabel()
        self.chu_loi.setTextFormat(Qt.TextFormat.RichText)
        self.chu_loi.linkActivated.connect(lambda _l: self.di_toi(KIEM_TRA))
        self.chu_loi.hide()
        duoi_tt = QHBoxLayout()
        duoi_tt.addLayout(self.hang_dem)
        duoi_tt.addStretch(1)
        duoi_tt.addWidget(self.chu_loi)
        self.the_tien_do = The(tren, self.tien_do, duoi_tt, dem=14)

        self.bang = _bang("Hồ sơ", "Trạng thái", "Mã hồ sơ", "Ghi chú")
        self.bang.setWordWrap(True)
        self.bang.setItemDelegate(DelegateDong(self.bang))
        self.bang.setItemDelegateForColumn(0, DelegateHaiDong(self.bang))
        self.bang.setItemDelegateForColumn(1, DelegateTrangThai(self.bang))
        self.bang.itemSelectionChanged.connect(self._xem_anh)
        self.bang.horizontalHeader().sectionResized.connect(lambda *_: self.bang.resizeRowsToContents())

        khung_nut, (nut_log, nut_anh) = _nhom_phan("Nhật ký", "Ảnh form")
        self.nhat_ky = QPlainTextEdit()
        self.nhat_ky.setReadOnly(True)
        self.anh = QLabel("Chọn một hồ sơ trong bảng để xem ảnh form.")
        self.anh.setObjectName("phu")
        self.anh.setWordWrap(True)
        self.anh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chu_anh = _chu_phu()
        self.nut_anh = NutPhu("Mở ảnh lớn")
        self.nut_anh.hide()
        self.nut_anh.clicked.connect(lambda: self.duong_anh and _mo(self.duong_anh))
        self.duong_anh: str | None = None
        trang_anh = QWidget()
        cot_anh = QVBoxLayout(trang_anh)
        cot_anh.setContentsMargins(0, 0, 0, 0)
        cot_anh.addWidget(self.anh, 1)
        cot_anh.addWidget(self.chu_anh)
        cot_anh.addWidget(self.nut_anh)
        self.khung_phu = QStackedWidget()
        self.khung_phu.addWidget(self.nhat_ky)
        self.khung_phu.addWidget(trang_anh)
        nut_log.clicked.connect(lambda: self.khung_phu.setCurrentIndex(0))
        nut_anh.clicked.connect(lambda: self.khung_phu.setCurrentIndex(1))
        ben = The(khung_nut, self.khung_phu, dem=8)
        ben.layout().setAlignment(khung_nut, Qt.AlignmentFlag.AlignLeft)
        tach = QSplitter(Qt.Orientation.Horizontal)
        tach.setChildrenCollapsible(True)
        tach.addWidget(The(self.bang, dem=8))
        tach.addWidget(ben)
        tach.setStretchFactor(0, 1)
        tach.setStretchFactor(1, 0)
        tach.setCollapsible(0, False)
        tach.setSizes([800, 300])
        lay = self.goc
        lay.addLayout(chon)
        lay.addWidget(self.the_tien_do)
        lay.addWidget(tach, 1)
        self.gio = QTimer(self, interval=30_000)
        self.gio.timeout.connect(self._cap_nhat_tien_do)
        self.phim("Ctrl+Return", self._phim_bat_dau)
        self.phim("Ctrl+.", self._phim_dung)
        self._doi_che_do()

    def che_do_chon(self) -> str:
        return "that" if self.r_that.isChecked() else "thu"

    def _doi_che_do(self) -> None:
        that = self.r_that.isChecked()
        self.chay.setText("Bắt đầu chạy thật" if that else "Bắt đầu chạy thử")
        self.chay.dat_chay_that(that)
        dat_thuoc_tinh(self.tien_do, "cheDo", self.che_do_chon())
        self.the_thu.lam_moi()
        self.the_that.lam_moi()
        self.doi.emit()

    def hien(self) -> None:
        p = self.p
        if not p.dang_chay:  # không nhớ lựa chọn chạy thật từ lần trước
            self.r_thu.setChecked(True)
        self.chay.setEnabled(bool(p.lo and not p.lo.co_loi) and not p.dang_chay)
        loi = sum(v.muc == "loi" for v in p.lo.van_de) if p.lo else 0
        self.chu_loi.setVisible(loi > 0)
        self.chu_loi.setText(f'<span style="color:{CHU_LOI}">Lô còn {loi} lỗi chặn. Sửa ở </span><a href="kt" style="color:{CHU_LOI}">bước Kiểm tra dữ liệu</a>.')
        self._doi_che_do()

    def _phim_bat_dau(self) -> None:
        if self.chay.isEnabled() and self.chay.isVisible():
            self.bat_dau()

    def _phim_dung(self) -> None:
        if self.dung.isEnabled() and self.dung.isVisible():
            self._dung()

    def _khoa_che_do(self, khoa: bool) -> None:
        for the in (self.the_thu, self.the_that):
            the.setEnabled(not khoa)
            the.lam_moi()
        self.gioi_han.setEnabled(not khoa)
        self.chay.setVisible(not khoa)
        self.dung.setVisible(khoa)

    def bat_dau(self) -> None:
        p = self.p
        if not p.lo or p.lo.co_loi:
            hop_thong_bao(self, "Chưa chạy được", "Lô còn lỗi chặn, hãy xem màn Kiểm tra dữ liệu.", "loi")
            return
        if not p.settings.cho_chay_khi_canh_bao and any(v.muc != "loi" for v in p.lo.van_de):
            hop_thong_bao(self, "Chưa chạy được", "Lô còn cảnh báo và Cài đặt đang không cho chạy khi có cảnh báo.", "canh_bao")
            return
        ho_so = p.can_chay if p.can_chay is not None else p.lo.ho_so
        that = self.r_that.isChecked()
        bo_qua = (TrangThai.CAN_KIEM_TRA, TrangThai.THANH_CONG, TrangThai.DA_CO_SAN, TrangThai.DA_CHUYEN_NGUOI_KHAC)
        con = [hs for hs in ho_so if p.store.get(hs.key).trang_thai not in bo_qua]
        if self.gioi_han.hasAcceptableInput():  # giới hạn chỉ tính hồ sơ còn phải làm
            ho_so = con = con[:int(self.gioi_han.text())]
        if that and not hop_xac_nhan(self, f"Chạy thật {len(con)} hồ sơ?", f"Tool sẽ Lưu {len(con)} hồ sơ lên MPLIS. Hồ sơ đã lưu không xóa được từ tool.",
                                     [("File", p.file.name if p.file else ""), ("Hệ thống", urlsplit(p.settings.mplis_url).netloc),
                                      ("Tài khoản", p.settings.username or "Chưa khai"), ("Người xử lý tiếp theo", p.can_bo or "Theo Excel"),
                                      ("Tra trùng", "Bật" if p.settings.tim_trung_truoc or p.da_reset else "Tắt")],
                                     f"Chạy thật {len(con)} hồ sơ", kieu="chay_that"):
            return
        self.hang = {hs.key: i for i, hs in enumerate(ho_so)}
        self.bang.setRowCount(len(ho_so))
        for i, hs in enumerate(ho_so):
            self._dat_dong(i, hs.key, "Chờ", "", "")
        self.tien_do.setRange(0, len(ho_so))
        self.tien_do.setValue(0)
        self.nhat_ky.clear()
        self.dang = ""
        opts = RunOptions(dry_run=not that, tai_khoan=p.settings.username,
                          tim_trung_truoc=p.settings.tim_trung_truoc or p.da_reset)  # đã reset thì buộc tra trùng
        self.che_do = "Chạy thật" if that else "Chạy thử"
        self.ho_so_chay = ho_so
        self.worker = Worker(ho_so, p.store, p.tao_port, opts)
        self.worker.event.connect(self._su_kien)
        self.worker.hoi_so.connect(self._hoi_so)
        self.worker.danh_ba.connect(self._luu_danh_ba)
        self.worker.finished.connect(self._xong)
        p.dang_chay, p.che_do_chay, p.tien_do = True, self.che_do_chon(), (0, len(ho_so))
        self.t_dau = time.monotonic()
        self.dung.setText("Dừng sau hồ sơ này")
        self.dung.setEnabled(True)
        self._khoa_che_do(True)
        self._cap_nhat_tien_do()
        self.gio.start()
        self.doi.emit()
        self.worker.start()

    def _luu_danh_ba(self, ds: dict) -> None:
        self.p.settings.danh_ba_can_bo.update(ds)
        self.p.settings.save()

    def _dung(self) -> None:
        self.worker.stop()
        self.dung.setEnabled(False)
        self.dung.setText("Sẽ dừng sau hồ sơ này")
        self._ghi_nhat_ky("Sẽ dừng sau hồ sơ đang chạy.", CHU_PHU)

    def _dat_dong(self, r: int, k: str, st: str, ma: str, note: str) -> None:
        self.bang.setItem(r, 0, _o_ho_so(k, self.p.nguoi_nhan(k)))
        self.bang.setItem(r, 1, QTableWidgetItem(st))
        self.bang.setItem(r, 2, _o_ma(ma))
        self.bang.setItem(r, 3, _o_ghi_chu(note))
        nen = QColor(NEN_DANG_CHAY) if st == "Đang chạy" else None
        for c in range(4):
            if nen:
                self.bang.item(r, c).setBackground(nen)
        self.bang.resizeRowToContents(r)

    def _ghi_nhat_ky(self, chu: str, mau: str) -> None:
        gio = f'<span style="font-family:Consolas,Menlo,monospace;color:{CHU_PHU}">{datetime.now():%H:%M:%S}</span>'
        self.nhat_ky.appendHtml(f'{gio}&nbsp;&nbsp;<span style="color:{mau}">{html.escape(chu)}</span>')

    def _su_kien(self, k: str, st: str, note: str, ma: str) -> None:
        ngan, _ = rut_gon_ghi_chu(note)
        chu = f"{ten_ho_so(k)}: {st.lower()}" + (f", mã {ma}" if ma else "") + (f". {ngan}" if ngan else "")
        self._ghi_nhat_ky(chu, TRANG_THAI[st][0] if st in CAN_XU_LY + ("Thành công",) else CHU)
        if k not in self.hang:
            return
        self._dat_dong(self.hang[k], k, st, ma, note)
        if st == "Đang chạy":
            self.dang = k
            self.bang.scrollToItem(self.bang.item(self.hang[k], 0))
        else:
            self.p.ket_qua[k] = (st, note, ma)
            dat_tien_do(self.tien_do, self._so_xong())
        self._cap_nhat_tien_do()
        self.doi.emit()

    def _so_xong(self) -> int:
        return sum(1 for x in self.hang if x in self.p.ket_qua)

    def _cap_nhat_tien_do(self) -> None:
        tong, xong = len(self.hang), self._so_xong()
        dang_lam = min(xong + 1, tong) if self.p.dang_chay else xong
        self.so_lon.setText(str(dang_lam))
        self.tren_so.setText(f"/ {tong} hồ sơ")
        if self.p.dang_chay:
            self.p.tien_do = (dang_lam, tong)
            self.dang_chu.setText(f"Đang chạy: {ten_ho_so(self.dang)} · {self.p.nguoi_nhan(self.dang)}" if self.dang else "Đang mở trình duyệt…")
            self.dang_chu.setToolTip(self.dang_chu.text())
            phut = int((time.monotonic() - self.t_dau) / 60)
            if xong:
                con = round((time.monotonic() - self.t_dau) / xong * (tong - xong) / 60)
                self.uoc.setText(f"Đã chạy {phut} phút · còn khoảng {con} phút")
            else:
                self.uoc.setText("Mỗi hồ sơ mất khoảng 3–4 phút")
        _xoa_hang(self.hang_dem)
        dem = Counter(self.p.ket_qua[k][0] for k in self.hang if k in self.p.ket_qua)
        for st in dict.fromkeys(["Thành công", "Cần kiểm tra", "Lỗi", *dem]):
            o = NhanTrangThai()
            o.dat(f"{dem[st]} {st}", st)
            self.hang_dem.addWidget(o)

    def _hoi_so(self, mo_ta: str, so: str) -> None:
        self._ghi_nhat_ky(f"MPLIS báo trùng số phát hành {so} ({mo_ta}).", TRANG_THAI["Cần kiểm tra"][0])
        cua_so = self.window()
        cua_so.raise_()  # cửa sổ Chromium đang che tool
        cua_so.activateWindow()
        QApplication.alert(cua_so)
        nguoi = self.p.nguoi_nhan(self.dang)
        ten = f"{mo_ta[:1].upper()}{mo_ta[1:]}" + (f" · {nguoi}" if nguoi else "")
        moi = hop_nhap(self, "MPLIS báo trùng số phát hành",
                       f'<b>{html.escape(ten)}</b><br>Số đang dùng: <span style="color:{CHU_LOI};text-decoration:line-through">{html.escape(so)}</span>',
                       "Số phát hành mới", goi_y="Bỏ qua thì hồ sơ được ghi là Cần kiểm tra, tool chạy tiếp hồ sơ sau.",
                       nut_dong_y="Dùng số mới", nut_bo_qua="Bỏ qua hồ sơ này", hop_le=so_phat_hanh_hop_le,
                       bao_sai="Số phát hành gồm 2 chữ cái và 8 chữ số, ví dụ AA 12345678.")
        moi = chuan_ma_phat_hanh(moi) if moi and so_phat_hanh_hop_le(moi) else None  # số sai dạng không bao giờ được gửi đi
        self.worker.tra_loi(moi or "")

    def _xem_anh(self) -> None:
        r = self.bang.currentRow()
        o = self.bang.item(r, 3) if r >= 0 else None
        duong = tep_trong_ghi_chu(o.data(KHOA))[0] if o else None
        pm = QPixmap(duong) if duong else QPixmap()
        self.duong_anh = None if pm.isNull() else duong
        self.nut_anh.setVisible(not pm.isNull())
        if pm.isNull():
            self.anh.setText("Không có ảnh cho dòng này." if o else "Chọn một hồ sơ trong bảng để xem ảnh form.")
            self.chu_anh.setText("")
            return
        self.anh.setPixmap(pm.scaledToWidth(max(self.anh.width(), 200), Qt.TransformationMode.SmoothTransformation))
        gio = datetime.fromtimestamp(Path(duong).stat().st_mtime)
        self.chu_anh.setText(f"{self.bang.item(r, 0).text()} · chụp lúc {gio:%H:%M}")

    def _xong(self) -> None:
        p = self.p
        giay = time.monotonic() - self.t_dau
        p.dang_chay, p.che_do_chay, p.tien_do = False, None, None
        self.gio.stop()
        self._cap_nhat_tien_do()
        self.dang_chu.setText(f"Đã chạy xong {self._so_xong()} hồ sơ")
        self.uoc.setText(f"Mất {round(giay / 60)} phút" if giay >= 30 else "Mất dưới 1 phút")
        self._khoa_che_do(False)
        kq = {hs.key: p.ket_qua[hs.key] for hs in self.ho_so_chay if hs.key in p.ket_qua}
        tom_tat = " · ".join(f"{n} {st}" for st, n in Counter(v[0] for v in kq.values()).most_common())
        p.store.ghi_lo(str(p.file), self.che_do, len(self.ho_so_chay), tom_tat, [hs.key for hs in self.ho_so_chay],
                       che_do_gom=p.che_do.value, sheet=p.sheet or "")
        p.lan_chay = {"che_do": self.che_do, "file": p.file.name if p.file else "", "thoi_gian": datetime.now().isoformat(timespec="seconds"), "giay": giay}
        p.can_chay, p.da_reset = None, False
        if not self.window().isActiveWindow():
            QApplication.alert(self.window())
        self.di_toi(KET_QUA)  # chạy xong chuyển ngay sang Kết quả, không cần thêm một bước bấm


class ManKetQua(ManHinh):
    """M6: tổng kết, xuất Excel, mở ảnh/trace, chạy lại dòng lỗi."""
    TIEU_DE, MO_TA, BUOC = "Kết quả", "Xuất file kết quả hoặc chọn các dòng lỗi để làm lại.", "Bước 5 / 5"

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.tong = HangSo()
        self.tong.setParent(self)
        self.tong.hide()
        self.keys: list[str] = []
        self.chips: dict[str, ChipLoc] = {}
        self.chip_chon: str | None = None
        self.nhan_che_do = NhanTrangThai("", cham=False)
        self.nhan_che_do.hide()
        self.hang_mo_ta.insertWidget(0, self.nhan_che_do)

        self.tieu_de_tay = QLabel()
        self.tieu_de_tay.setObjectName("tieuDeThe")
        self.phu_tay = _chu_phu(xuong_dong=True)
        self.phu_tay.setTextFormat(Qt.TextFormat.RichText)
        self.nut_tay = NutPhu("Chỉ xem các hồ sơ này")
        self.nut_tay.clicked.connect(lambda: self.chips.get("Cần xử lý tay") and self.chips["Cần xử lý tay"].click())
        self.icon_tay = QLabel()
        cot = QVBoxLayout()
        cot.setSpacing(2)
        cot.addWidget(self.tieu_de_tay)
        cot.addWidget(self.phu_tay)
        hang_tay = QHBoxLayout()
        hang_tay.setSpacing(12)
        hang_tay.addWidget(self.icon_tay)
        hang_tay.addLayout(cot, 1)
        hang_tay.addWidget(self.nut_tay)
        self.the_tay = The(hang_tay, dem=8, bong=False)

        self.hang_chip = QHBoxLayout()
        self.hang_chip.setSpacing(8)
        self.nhom_chip = QButtonGroup(self)
        self.tim = O_TimKiem("Tờ/thửa, người nhận, mã hồ sơ")
        self.tim.setMinimumWidth(180)
        self.tim.setMaximumWidth(280)
        self.tim.textChanged.connect(lambda _t: self._ap_loc())
        khung_chip = QWidget()
        trong_chip = QHBoxLayout(khung_chip)
        trong_chip.setContentsMargins(0, 0, 0, 0)
        trong_chip.addLayout(self.hang_chip)
        trong_chip.addStretch(1)
        cuon_chip = QScrollArea()  # lô có nhiều trạng thái thì chip cuộn ngang, không đẩy vỡ màn
        cuon_chip.setWidgetResizable(True)
        cuon_chip.setFrameShape(QFrame.Shape.NoFrame)
        cuon_chip.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cuon_chip.setFixedHeight(46)
        cuon_chip.setWidget(khung_chip)
        loc = QHBoxLayout()
        loc.setContentsMargins(10, 4, 10, 0)
        loc.setSpacing(12)
        loc.addWidget(cuon_chip, 1)
        loc.addWidget(self.tim)

        self.bang = _bang("☐", "Hồ sơ", "Trạng thái", "Mã hồ sơ", "Ghi chú", "Tệp", rong=4)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.bang.setWordWrap(True)
        self.bang.setItemDelegateForColumn(1, DelegateHaiDong(self.bang))
        self.bang.setItemDelegateForColumn(2, DelegateTrangThai(self.bang))
        self.bang.horizontalHeader().sectionClicked.connect(self._tich_tat_ca)
        self.bang.horizontalHeader().sectionResized.connect(lambda *_: self.bang.resizeRowsToContents())
        self.bang.itemChanged.connect(lambda _o: self._cap_nhat_chon())
        self.bang.itemSelectionChanged.connect(self._cap_nhat_chon)
        self.bang.cellDoubleClicked.connect(self._chep_ma)
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(self._menu)
        self.rong = _chu_phu("Không có hồ sơ nào ở trạng thái này.")
        self.rong.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rong.hide()

        self.so_chon = _chu_phu("Đã chọn 0 hồ sơ")
        log, trace = NutChu("Thư mục log", ve_icon("thu_muc", NHAN)), NutChu("Thư mục trace", ve_icon("thu_muc", NHAN))
        log.clicked.connect(lambda: _mo(LOG_DIR))
        trace.clicked.connect(lambda: _mo(TRACE_DIR))
        self.nut_lai = NutPhu("Chạy lại 0 hồ sơ đã chọn", ve_icon("doc_lai", CHU_PHU))
        self.nut_lai.clicked.connect(self.chay_lai)
        xuat = NutChinh("Xuất Excel", ve_icon("tai_xuong", TRANG))
        xuat.clicked.connect(self.xuat)
        self.chu_xuat = QLabel()
        self.mo_xuat, self.mo_tm = NutChu("Mở file"), NutChu("Mở thư mục")
        self.tep_xuat: Path | None = None
        self.mo_xuat.clicked.connect(lambda: self.tep_xuat and _mo(self.tep_xuat))
        self.mo_tm.clicked.connect(lambda: self.tep_xuat and _mo(self.tep_xuat.parent))
        hang_xuat = QHBoxLayout()
        hang_xuat.addWidget(self.chu_xuat, 1)
        hang_xuat.addWidget(self.mo_xuat)
        hang_xuat.addWidget(self.mo_tm)
        self.the_xuat = The(hang_xuat, dem=4, bong=False, nen=TRANG_THAI["Thành công"][1], vien=TRANG_THAI["Thành công"][1])
        self.the_xuat.hide()
        self.gio_xuat = QTimer(self, singleShot=True, interval=6_000)
        self.gio_xuat.timeout.connect(self.the_xuat.hide)

        lay = self.goc
        lay.addWidget(self.the_tay)
        lay.addLayout(loc)
        lay.addWidget(The(self.bang, self.rong, dem=8), 1)
        lay.addWidget(self.the_xuat)
        hang_nut(lay, self.nut_lai, xuat, trai=(self.so_chon, log, trace))
        self.phim("Ctrl+F", self.tim.setFocus)
        self.phim("Ctrl+E", self.xuat)
        self.phim("Space", self._tich_dong, self.bang)

    def _dem(self, st: str) -> int:
        return sum(1 for v in self.p.ket_qua.values() if v[0] == st)

    def _mo_ta_lo(self) -> None:
        lan = self.p.lan_chay
        self.nhan_che_do.setVisible(bool(lan))
        if not lan:
            self.dong_mo_ta.setText(self.MO_TA)
            return
        self.nhan_che_do.dat(lan["che_do"])
        phan = [lan["file"], ngay_gio(lan["thoi_gian"])]
        if lan.get("giay") is not None:
            phut = round(lan["giay"] / 60)
            phan.append(f"{len(self.keys)} hồ sơ trong " + (f"{phut} phút" if phut else "dưới 1 phút"))
        self.dong_mo_ta.setText(" · ".join(phan))

    def _lam_the_tay(self) -> None:
        tay = [k for k in self.keys if self.p.ket_qua[k][0] in CAN_XU_LY]
        n = len(tay)
        co = n > 0
        self.nut_tay.setVisible(co)
        self.the_tay.dat(*((NEN_XU_LY_TAY, VIEN_XU_LY_TAY) if co else (TRANG_THAI["Thành công"][1], TRANG_THAI["Thành công"][1])))
        self.icon_tay.setPixmap(ve_anh("co_le" if co else "xong", CAM if co else TRANG_THAI["Thành công"][2], 20))
        self.tieu_de_tay.setText(f"{n} hồ sơ cần xử lý tay" if co else "✓ Không có hồ sơ nào cần xử lý tay.")
        phu = "<br>".join(f"{html.escape(ten_ho_so(k))}: {html.escape(rut_gon_ghi_chu(self.p.ket_qua[k][1])[0][:90])}" for k in tay) if 0 < n <= 3 else ""
        self.phu_tay.setText(phu)
        self.phu_tay.setVisible(bool(phu))

    def _lam_chip(self) -> None:
        _xoa_hang(self.hang_chip)
        for b in self.nhom_chip.buttons():
            self.nhom_chip.removeButton(b)
        self.chips = {}
        tay = sum(self._dem(s) for s in CAN_XU_LY)
        ds = [("Tất cả", len(self.keys), None), ("Cần xử lý tay", tay, TRANG_THAI["Cần kiểm tra"][2])]
        ds += [(st, self._dem(st), TRANG_THAI[st][2]) for st in THU_TU_KET_QUA if self._dem(st)]
        for ten, so, cham in ds:
            b = ChipLoc(ten, so, cham)
            b.clicked.connect(lambda _c=False, t=ten: self._chon_chip(t))
            self.nhom_chip.addButton(b)
            self.hang_chip.addWidget(b)
            self.chips[ten] = b
        macdinh = "Cần xử lý tay" if tay else "Tất cả"
        chon = self.chip_chon if self.chip_chon in self.chips else macdinh
        self.chips[chon].setChecked(True)

    def _chon_chip(self, ten: str) -> None:
        self.chip_chon = ten
        self._ap_loc()

    def hien(self) -> None:
        kq = self.p.ket_qua
        dem = Counter(v[0] for v in kq.values())
        self.tong.dat([(st, dem[st], "") for st in TRANG_THAI if dem[st]], "Chưa có kết quả. Hãy chạy một lô ở màn Chạy.")
        thu_tu = {st: i for i, st in enumerate(THU_TU_KET_QUA)}
        self.keys = sorted((hs.key for hs in self.p.lo.ho_so if hs.key in kq) if self.p.lo else [], key=lambda k: thu_tu.get(kq[k][0], 99))
        t = self.bang
        t.blockSignals(True)
        t.setRowCount(len(self.keys))
        for r, k in enumerate(self.keys):
            st, note, ma = kq[k]
            tich = QTableWidgetItem()
            tich.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            tich.setCheckState(Qt.CheckState.Unchecked)
            t.setItem(r, 0, tich)
            t.setItem(r, 1, _o_ho_so(k, self.p.nguoi_nhan(k)))
            t.setItem(r, 2, QTableWidgetItem(st))
            t.setItem(r, 3, _o_ma(ma))
            t.setItem(r, 4, _o_ghi_chu(note))
            t.setCellWidget(r, 5, self._o_tep(note))
        t.blockSignals(False)
        t.resizeRowsToContents()
        self._mo_ta_lo()
        self._lam_the_tay()
        self.the_tay.setVisible(bool(self.keys))
        self._lam_chip()
        self._ap_loc()
        self._cap_nhat_chon()
        self.doi.emit()

    def _o_tep(self, note: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(6)
        anh, trace = tep_trong_ghi_chu(note)
        for duong, icon, ten in ((anh, "anh", "Ảnh form"), (trace, "trace", "Trace")):
            if not duong:
                continue
            b = QToolButton()
            b.setObjectName("tep")
            b.setIcon(ve_icon(icon, CHU_PHU, 18))
            b.setFixedSize(36, 36)
            b.setToolTip(ten)
            b.setAccessibleName(ten)
            b.clicked.connect(lambda _c=False, d=duong: _mo(d))
            lay.addWidget(b)
        lay.addStretch(1)
        return w

    def _ap_loc(self) -> None:
        chip = next((t for t, b in self.chips.items() if b.isChecked()), "Tất cả")
        q = self.tim.text()
        t = self.bang
        con = 0
        for r in range(t.rowCount()):
            st = t.item(r, 2).text()
            hop = (chip == "Tất cả" or (chip == "Cần xử lý tay" and st in CAN_XU_LY) or st == chip)
            giu = hop and khop_tim(q, t.item(r, 1).text(), t.item(r, 1).data(KHOA), t.item(r, 1).data(VAI_PHU), t.item(r, 3).text())
            t.setRowHidden(r, not giu)
            con += giu
        t.setVisible(con > 0 or not t.rowCount())
        self.rong.setVisible(con == 0 and t.rowCount() > 0)
        self._cap_nhat_chon()

    def _chon(self) -> list[str]:
        t = self.bang
        tich = [t.item(r, 1).data(KHOA) for r in range(t.rowCount()) if not t.isRowHidden(r) and t.item(r, 0).checkState() == Qt.CheckState.Checked]
        boi = [t.item(i.row(), 1).data(KHOA) for i in t.selectionModel().selectedRows() if not t.isRowHidden(i.row())]
        return list(dict.fromkeys(tich + boi))

    def _cap_nhat_chon(self) -> None:
        chon = self._chon()
        n = sum(1 for k in chon if self.p.ket_qua.get(k, ("",))[0] in CAN_XU_LY)
        self.so_chon.setText(f"Đã chọn {len(chon)} hồ sơ")
        self.nut_lai.setText(f"Chạy lại {n} hồ sơ đã chọn")
        self.nut_lai.setEnabled(n > 0)

    def _tich_tat_ca(self, cot: int) -> None:
        if cot != 0:
            return
        t = self.bang
        hien = [r for r in range(t.rowCount()) if not t.isRowHidden(r)]
        bat = not all(t.item(r, 0).checkState() == Qt.CheckState.Checked for r in hien)
        t.blockSignals(True)
        for r in hien:
            t.item(r, 0).setCheckState(Qt.CheckState.Checked if bat else Qt.CheckState.Unchecked)
        t.blockSignals(False)
        t.horizontalHeaderItem(0).setText("☑" if bat and hien else "☐")
        self._cap_nhat_chon()

    def _tich_dong(self) -> None:
        o = self.bang.item(self.bang.currentRow(), 0) if self.bang.currentRow() >= 0 else None
        if o:
            o.setCheckState(Qt.CheckState.Unchecked if o.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def _chep_ma(self, r: int, c: int) -> None:
        if c == 3 and self.bang.item(r, 3).text() != "—":
            QGuiApplication.clipboard().setText(self.bang.item(r, 3).text())

    def _menu(self, vi_tri) -> None:
        r = self.bang.rowAt(vi_tri.y())
        if r < 0:
            return
        t = self.bang
        khoa, ma = t.item(r, 1).data(KHOA), t.item(r, 3).text()
        anh, trace = tep_trong_ghi_chu(t.item(r, 4).data(KHOA))
        m = QMenu(self)
        chep = QGuiApplication.clipboard().setText
        a = m.addAction("Chép mã hồ sơ", lambda: chep(ma))
        a.setEnabled(ma != "—")
        m.addAction("Chép Tờ/thửa", lambda: chep(ten_ho_so(khoa)))
        m.addAction("Mở ảnh form", lambda: _mo(anh)).setEnabled(bool(anh))
        m.addAction("Mở trace", lambda: _mo(trace)).setEnabled(bool(trace))

        def chay_lai_dong() -> None:
            self.chay_lai([khoa])  # chỉ hồ sơ này, không gộp các dòng đang tích

        m.addAction("Chạy lại hồ sơ này", chay_lai_dong).setEnabled(self.p.ket_qua[khoa][0] in CAN_XU_LY)
        m.exec(t.viewport().mapToGlobal(vi_tri))

    def xuat(self) -> None:
        if not self.keys:
            return
        try:
            d = xuat_ket_qua(self.p.lo, self.p.ket_qua)
        except PermissionError:
            hop_thong_bao(self, "Không ghi được", "Hãy đóng file kết quả trong Excel rồi bấm lại.", "canh_bao")
            return
        self.tep_xuat = Path(d)
        self.chu_xuat.setText(f"Đã xuất {self.tep_xuat.name}")
        self.the_xuat.show()
        self.gio_xuat.start()

    def chay_lai(self, khoa: list[str] | None = None) -> None:
        p = self.p
        chon = khoa if khoa is not None else self._chon()
        loi = [k for k in chon if p.ket_qua[k][0] in CAN_XU_LY]
        # DANG_TAO có thể đã tạo trên MPLIS: giữ nguyên trạng thái để Runner bắt buộc tra trùng, không xoá về CHO
        dang_tao = [k for k in loi if p.store.get(k).trang_thai is TrangThai.DANG_TAO]
        chon = [k for k in loi if not p.store.get(k).ma_ho_so and k not in dang_tao]  # có mã: tra trùng gặp chính nó, che mất phần dở
        if len(chon) + len(dang_tao) < len(loi):
            hop_thong_bao(self, "Chạy lại", f"{len(loi) - len(chon) - len(dang_tao)} hồ sơ đã có mã trên MPLIS, không làm lại từ đầu được. "
                                            "Hãy xử lý tiếp các hồ sơ này trên MPLIS.", "canh_bao")
        if not loi:
            hop_thong_bao(self, "Chạy lại", 'Chọn ít nhất một dòng "Lỗi" hoặc "Cần kiểm tra".')
        tat_ca = chon + dang_tao
        if not tat_ca:
            return
        if not hop_xac_nhan(self, "Chạy lại", f"Làm lại {len(tat_ca)} hồ sơ đã chọn? Tool sẽ tra trùng trên MPLIS trước.", [],
                            f"Làm lại {len(tat_ca)} hồ sơ"):
            return
        for k in chon:
            p.store.reset(k)
        for k in tat_ca:
            p.ket_qua.pop(k, None)
        p.can_chay, p.da_reset = [hs for hs in p.lo.ho_so if hs.key in tat_ca], True
        self.di_toi(CHAY)


class _OSapXep(QTableWidgetItem):
    """Sắp theo giá trị gốc thay vì chữ đang hiện."""

    def __lt__(self, khac: QTableWidgetItem) -> bool:
        return self.data(KHOA) < khac.data(KHOA)


class ManLichSu(ManHinh):
    """M7: các lô đã chạy; tìm theo tên file hoặc tờ/thửa."""
    TIEU_DE, MO_TA = "Lịch sử", "Mở lại kết quả hoặc chạy tiếp một lô đã làm."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.ds: list[dict] = []
        self.tim = O_TimKiem("Tìm theo tên file hoặc tờ/thửa, ví dụ: thửa 3938")
        self.tim.textChanged.connect(lambda _: self.hien())
        khung, (self.nut_tat_ca, self.nut_that, self.nut_thu) = _nhom_phan("Tất cả", "Chạy thật", "Chạy thử")
        for b in (self.nut_tat_ca, self.nut_that, self.nut_thu):
            b.clicked.connect(lambda _c=False: self.hien())
        cong_cu = QHBoxLayout()
        cong_cu.setContentsMargins(10, 0, 10, 2)
        cong_cu.setSpacing(12)
        cong_cu.addWidget(self.tim, 1)
        cong_cu.addWidget(khung)
        self.bang = _bang("Thời gian", "File", "Chế độ", "Số hồ sơ", "Kết quả", "", rong=1)
        self.bang.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.bang.setColumnWidth(4, 240)
        self.bang.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.bang.setColumnWidth(5, 52)
        self.bang.setItemDelegateForColumn(0, DelegateHaiDong(self.bang, ngang=True))
        self.bang.setItemDelegateForColumn(2, DelegateTrangThai(self.bang))
        self.bang.setItemDelegateForColumn(4, DelegateKetQua(self.bang))
        self.bang.verticalHeader().setDefaultSectionSize(52)
        self.bang.itemSelectionChanged.connect(self._cap_nhat_nut)
        self.bang.itemActivated.connect(lambda _o: self.mo(KET_QUA))
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(self._menu)
        moi = NutChinh("Tạo lô mới")
        moi.clicked.connect(lambda: self.di_toi(LO_MOI))
        xoa = NutPhu("Xóa tìm kiếm")
        xoa.clicked.connect(self.tim.clear)
        self.rong = _trang_thai_trong("dong_ho", "Chưa có lô nào được chạy.", moi, xoa)
        self.nut_moi, self.nut_xoa = moi, xoa
        self.tong_ket = _chu_phu()
        self.nut_xoa_het = NutNguyHiem("Xoá toàn bộ lịch sử", ve_icon("xoa", CHU_PHU))
        self.nut_xoa_het.clicked.connect(self.xoa_het)
        self.nut_tiep, self.nut_mo = NutPhu("Chạy tiếp lô này"), NutChinh("Mở kết quả")
        self.nut_tiep.clicked.connect(lambda: self.mo(CHAY))
        self.nut_mo.clicked.connect(lambda: self.mo(KET_QUA))
        lay = self.goc
        lay.addLayout(cong_cu)
        lay.addWidget(The(self.bang, self.rong, self.tong_ket, dem=8), 1)
        hang_nut(lay, self.nut_tiep, self.nut_mo, trai=(self.nut_xoa_het, _chu_phu("Bấm đúp một dòng để mở kết quả")))
        self.phim("Ctrl+F", self.tim.setFocus)
        self.phim("Esc", self.tim.clear, self.tim)

    def hien(self) -> None:
        q = self.tim.text().strip()
        cd = "Chạy thật" if self.nut_that.isChecked() else "Chạy thử" if self.nut_thu.isChecked() else None
        self.ds = [x for x in self.p.store.ds_lo() if (not cd or x["che_do"] == cd) and khop_tim(q, Path(x["file"]).name, *x["keys"], *map(ten_ho_so, x["keys"]))]
        t = self.bang
        t.setSortingEnabled(False)
        t.setRowCount(len(self.ds))
        for r, x in enumerate(self.ds):
            tg = datetime.fromisoformat(x["thoi_gian"])
            o = _OSapXep(f"{tg:%H:%M}")
            o.setData(KHOA, x["thoi_gian"])
            o.setData(VAI_PHU, f"· {tg:%d/%m/%Y}")
            o.setData(VAI_CHI_SO, r)
            t.setItem(r, 0, o)
            ten = QTableWidgetItem(Path(x["file"]).name)
            ten.setToolTip(x["file"])
            t.setItem(r, 1, ten)
            t.setItem(r, 2, QTableWidgetItem(x["che_do"]))
            so = QTableWidgetItem()
            so.setData(Qt.ItemDataRole.DisplayRole, x["so_ho_so"])
            t.setItem(r, 3, so)
            t.setItem(r, 4, QTableWidgetItem(x["tom_tat"]))
            o_xoa = QWidget()
            hang_xoa = QHBoxLayout(o_xoa)
            hang_xoa.setContentsMargins(4, 0, 8, 0)
            hang_xoa.addWidget(_nut_xoa(lambda _c=False, id_=x["id"]: self._xoa_id(id_), self.p.dang_chay))
            t.setCellWidget(r, 5, o_xoa)
        t.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        t.setSortingEnabled(True)
        co = bool(self.ds)
        t.setVisible(co)
        self.tong_ket.setVisible(co)
        self.rong.setVisible(not co)
        co_lo = bool(self.p.store.ds_lo())
        self.nut_moi.setVisible(not co_lo)
        self.nut_xoa.setVisible(co_lo and bool(q))
        self.rong.chu.setText(f'Không tìm thấy lô khớp với "{q}".' if co_lo and q else "Không có lô nào ở chế độ này." if co_lo else "Chưa có lô nào được chạy.")
        ho_so = sum(x["so_ho_so"] for x in self.ds)
        tc = sum(n for x in self.ds for n, ten in doan_ket_qua(x["tom_tat"]) if ten == "Thành công")
        self.tong_ket.setText(f"{len(self.ds)} lô · {ho_so} hồ sơ · {tc} thành công")
        self.nut_xoa_het.setEnabled(co_lo and not self.p.dang_chay)
        self.nut_xoa_het.setToolTip(DANG_CHAY_KHONG_XOA if self.p.dang_chay else "")
        self._cap_nhat_nut()

    def _xoa_id(self, id_: int) -> None:
        x = next((r for r in self.ds if r["id"] == id_), None)
        if x and _xoa_lich_su(self, [x]):
            self.hien()

    def xoa_dong(self, r: int) -> None:
        if 0 <= r < self.bang.rowCount():
            self._xoa_id(self.ds[self.bang.item(r, 0).data(VAI_CHI_SO)]["id"])

    def xoa_het(self) -> None:
        if _xoa_lich_su(self, self.p.store.ds_lo(), tat_ca=True):
            self.hien()

    def _dong(self) -> dict | None:
        r = self.bang.currentRow()
        return self.ds[self.bang.item(r, 0).data(VAI_CHI_SO)] if r >= 0 and not self.bang.isRowHidden(r) and self.bang.selectedItems() else None

    def _cap_nhat_nut(self) -> None:
        x = self._dong()
        self.nut_mo.setEnabled(bool(x))
        self.nut_tiep.setEnabled(bool(x) and any(not self.p.store.get(k).trang_thai.ket_thuc for k in x["keys"]))

    def _menu(self, vi_tri) -> None:
        if self.bang.rowAt(vi_tri.y()) < 0:
            return
        self.bang.selectRow(self.bang.rowAt(vi_tri.y()))
        x = self._dong()
        m = QMenu(self)
        m.addAction("Mở kết quả", lambda: self.mo(KET_QUA))
        m.addAction("Chạy tiếp", lambda: self.mo(CHAY)).setEnabled(self.nut_tiep.isEnabled())
        m.addAction("Mở file Excel gốc", lambda: _mo(x["file"])).setEnabled(Path(x["file"]).exists())
        m.addAction("Mở thư mục log của lô", lambda: _mo(LOG_DIR))
        m.addSeparator()
        m.addAction(ve_icon("xoa", CHU_PHU), "Xoá", lambda: self._xoa_id(x["id"])).setEnabled(not self.p.dang_chay)
        m.exec(self.bang.viewport().mapToGlobal(vi_tri))

    def mo(self, man: int) -> None:
        x, p = self._dong(), self.p
        if not x or p.dang_chay:
            return
        p.can_chay, p.da_reset = None, False  # danh sách chạy lại của lô trước không áp sang lô này
        f = Path(x["file"])
        if not f.exists():
            hop_thong_bao(self, "Không thấy file", str(f), "canh_bao")
            return
        p.file, p.sheet = f, x.get("sheet") or None
        if x.get("che_do_gom"):  # lô cũ chưa lưu chế độ gộp thì giữ chế độ đang chọn
            p.che_do = CheDoGom(x["che_do_gom"])
        p.nap()
        p.ket_qua = {}
        for k in x["keys"]:
            bg = p.store.get(k)
            if bg.so_lan:
                p.ket_qua[k] = (TRANG_THAI_THEO_ENUM.get(bg.trang_thai, bg.trang_thai.value), bg.ghi_chu, bg.ma_ho_so)
        p.lan_chay = {"che_do": x["che_do"], "file": f.name, "thoi_gian": x["thoi_gian"]}
        self.di_toi(man)


class ManCaiDat(ManHinh):
    """M8: các trường của Settings, tự lưu khi đổi."""
    TIEU_DE, MO_TA = "Cài đặt", "Thay đổi được lưu ngay khi bạn rời khỏi ô."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        s = p.settings
        self.trang_thai_luu = QLabel()
        self.o_goc.addWidget(self.trang_thai_luu)
        self.chu: dict[str, QLineEdit] = {}
        for ten in ("mplis_url", "username", "nguoi_ky", "thoi_han_mac_dinh"):
            o = QLineEdit(getattr(s, ten))
            o.editingFinished.connect(self._luu)
            self.chu[ten] = o
        self.so: dict[str, QLineEdit] = {}
        self.quy_doi: dict[str, QLabel] = {}
        for ten, hi in (("timeout_ms", 600_000), ("slow_mo_ms", 10_000)):
            o = QLineEdit(str(getattr(s, ten)))
            o.setValidator(QIntValidator(0, hi, o))
            o.editingFinished.connect(self._luu)
            o.textChanged.connect(lambda _t, t=ten: self._quy_doi(t))
            self.so[ten] = o
            self.quy_doi[ten] = _chu_phu()
        self.tich: dict[str, QCheckBox] = {}
        for ten, nhan in (("cho_chay_khi_canh_bao", "Cho chạy khi còn cảnh báo"), ("tim_trung_truoc", "Tra trùng trước khi tạo"),
                          ("headless", "Chạy Chromium ẩn")):
            o = QCheckBox(nhan)
            o.setStyleSheet("QCheckBox { font-weight: 600; }")
            o.setChecked(getattr(s, ten))
            o.toggled.connect(lambda _=False: self._luu())
            self.tich[ten] = o

        mo_url = NutPhu("Mở")
        mo_url.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.chu["mplis_url"].text().strip())))
        hang_url = QHBoxLayout()
        hang_url.setSpacing(8)
        hang_url.addWidget(self.chu["mplis_url"], 1)
        hang_url.addWidget(mo_url)
        nhan_url = QLabel("Địa chỉ MPLIS")
        nhan_url.setObjectName("nhanO")
        the_ket_noi = The(_tieu_de_the("Kết nối MPLIS"), nhan_url, hang_url,
                          _o_nhan("Tài khoản của tôi", self.chu["username"], "Mật khẩu MPLIS không lưu trong tool; bạn đăng nhập trong cửa sổ Chromium."))
        the_mac_dinh = The(_tieu_de_the("Giá trị mặc định của hồ sơ"), _o_nhan("Người ký", self.chu["nguoi_ky"]),
                           _o_nhan("Thời hạn mặc định", self.chu["thoi_han_mac_dinh"]))
        giai_thich = {"cho_chay_khi_canh_bao": "Lỗi chặn vẫn luôn chặn, dù bật hay tắt.", "tim_trung_truoc": "Thửa đã có hồ sơ trên MPLIS sẽ ghi là Đã có sẵn.",
                      "headless": "Không thấy form đang điền; hộp hỏi số phát hành vẫn hiện."}

        def tich_co_mo_ta(ten: str) -> QVBoxLayout:
            lay = QVBoxLayout()
            lay.setSpacing(0)
            lay.addWidget(self.tich[ten])
            phu = _chu_phu(giai_thich[ten], xuong_dong=True)
            phu.setIndent(32)
            lay.addWidget(phu)
            return lay

        the_quy_tac = The(_tieu_de_the("Quy tắc khi chạy"), tich_co_mo_ta("cho_chay_khi_canh_bao"), tich_co_mo_ta("tim_trung_truoc"))
        luoi_so = QHBoxLayout()
        luoi_so.setSpacing(16)
        for ten, nhan in (("timeout_ms", "Thời gian chờ"), ("slow_mo_ms", "Làm chậm")):
            hang = QHBoxLayout()
            hang.setSpacing(6)
            hang.addWidget(self.so[ten], 1)
            hang.addWidget(_chu_phu("ms"))
            cot = QVBoxLayout()
            cot.setSpacing(6)
            t = QLabel(nhan)
            t.setObjectName("nhanO")
            cot.addWidget(t)
            cot.addLayout(hang)
            cot.addWidget(self.quy_doi[ten])
            luoi_so.addLayout(cot, 1)
        the_trinh = The(_tieu_de_the("Trình duyệt và tốc độ"), luoi_so, tich_co_mo_ta("headless"))
        self.nut_xoa = NutNguyHiem("Xóa phiên đăng nhập Chromium…")
        self.nut_xoa.clicked.connect(self._xoa_phien)
        tm = NutPhu("Mở thư mục dữ liệu", ve_icon("thu_muc", CHU_PHU))
        tm.clicked.connect(lambda: _mo(app_dir()))
        cot_bt = QVBoxLayout()
        cot_bt.setSpacing(2)
        cot_bt.addWidget(_tieu_de_the("Bảo trì"))
        cot_bt.addWidget(_chu_phu(f"Phiên bản {__version__}"))
        bt = QHBoxLayout()
        bt.setSpacing(12)
        bt.addLayout(cot_bt, 1)
        bt.addWidget(tm)
        bt.addWidget(self.nut_xoa)
        the_bt = The(bt, dem=14, bong=False)
        for the in (the_ket_noi, the_mac_dinh, the_quy_tac, the_trinh):
            the.layout().addStretch(1)
        luoi = QGridLayout()
        luoi.setContentsMargins(0, 0, 0, 0)
        luoi.setSpacing(0)
        luoi.addWidget(the_ket_noi, 0, 0)
        luoi.addWidget(the_mac_dinh, 0, 1)
        luoi.addWidget(the_quy_tac, 1, 0)
        luoi.addWidget(the_trinh, 1, 1)
        luoi.addWidget(the_bt, 2, 0, 1, 2)
        luoi.setRowStretch(3, 1)
        than = QWidget()
        than.setLayout(luoi)
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.Shape.NoFrame)
        cuon.setWidget(than)
        self.goc.addWidget(cuon, 1)
        for ten in self.so:
            self._quy_doi(ten)

    def _quy_doi(self, ten: str) -> None:
        o = self.so[ten]
        if not o.hasAcceptableInput():
            self.quy_doi[ten].setText("")
            return
        ms = int(o.text())
        if ten == "slow_mo_ms" and ms == 0:
            self.quy_doi[ten].setText("0 = không làm chậm")
        else:
            self.quy_doi[ten].setText(f"= {ms / 1000:g} giây")

    def hien(self) -> None:
        self.nut_xoa.setEnabled(not self.p.dang_chay)
        self.nut_xoa.setToolTip("Không xóa được khi đang chạy" if self.p.dang_chay else "")

    def _luu(self) -> None:
        s = self.p.settings
        loi: list[str] = []
        for ten, o in self.chu.items():
            gt = o.text().strip()
            sai = ten == "mplis_url" and not gt.startswith("https://")
            dat_thuoc_tinh(o, "loi", "true" if sai else "false")
            if sai:
                loi.append("Địa chỉ MPLIS phải bắt đầu bằng https://")
            else:
                setattr(s, ten, gt)
        for ten, o in self.so.items():
            dung = o.hasAcceptableInput()
            dat_thuoc_tinh(o, "loi", "false" if dung else "true")
            if dung:
                setattr(s, ten, int(o.text()))
            else:
                loi.append(("Thời gian chờ" if ten == "timeout_ms" else "Làm chậm") + " phải là số")
        for ten, o in self.tich.items():
            setattr(s, ten, o.isChecked())
        s.save()
        if loi:
            self.trang_thai_luu.setStyleSheet(f"color: {CHU_LOI}; font-weight: 600;")
            self.trang_thai_luu.setText("Chưa lưu: " + "; ".join(loi))
        else:
            self.trang_thai_luu.setStyleSheet(f"color: {TRANG_THAI['Thành công'][0]}; font-weight: 600;")
            self.trang_thai_luu.setText(f"✓ Đã lưu lúc {datetime.now():%H:%M}")

    def _xoa_phien(self) -> None:
        if self.p.dang_chay:
            return
        if hop_xac_nhan(self, "Xóa phiên đăng nhập Chromium?", "Lần chạy sau bạn phải đăng nhập MPLIS lại. Dữ liệu lô và lịch sử không bị ảnh hưởng.", [],
                        "Xóa phiên", kieu="nguy_hiem"):
            shutil.rmtree(BROWSER_PROFILE, ignore_errors=True)


MAN_HINH = [("Lô mới", ManLoMoi), ("Kiểm tra dữ liệu", ManKiemTra), ("Ánh xạ danh mục", ManDanhMuc), ("Chạy", ManChay),
            ("Kết quả", ManKetQua), ("Lịch sử", ManLichSu), ("Cài đặt", ManCaiDat)]
