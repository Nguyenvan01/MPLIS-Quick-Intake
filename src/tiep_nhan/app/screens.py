"""Màn hình M2–M8 (docs/wireframe.md). Không có M1: người dùng tự đăng nhập trong cửa sổ Chromium."""
from __future__ import annotations

import re
import shutil
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ContextManager
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIntValidator, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QRadioButton, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import __version__
from ..core.batch import Lo, nap_lo, xuat_ket_qua
from ..core.runner import RunOptions
from ..core.state import StateStore, TrangThai
from ..domain.danh_muc import DanhMuc
from ..domain.gom_ho_so import CheDoGom
from ..domain.models import HoSo
from ..infra.config import BROWSER_PROFILE, LOG_DIR, STATE_DB, TRACE_DIR, Settings, app_dir, config_file
from ..infra.excel_in import ten_sheet
from ..infra.logging import che_cccd
from ..mplis.locators import Locators
from ..mplis.port import MplisPort
from ..mplis.ui_adapter import PlaywrightMplis
from .giao_dien import HangSo, NutChinh, The, hang_nut, khung_man
from .worker import Worker

LO_MOI, KIEM_TRA, DANH_MUC, CHAY, KET_QUA, LICH_SU, CAI_DAT = range(7)

MAU = {"Thành công": "#1b7f3b", "Đã có sẵn": "#1f5fbf", "Cần kiểm tra": "#b35c00", "Lỗi": "#c0261c",
       "Chạy thử": "#3a86c8", "Đã chuyển": "#6a3fb5"}
NHAN = {TrangThai.THANH_CONG: "Thành công", TrangThai.DA_CO_SAN: "Đã có sẵn", TrangThai.CAN_KIEM_TRA: "Cần kiểm tra",
        TrangThai.LOI: "Lỗi", TrangThai.DA_CHUYEN_NGUOI_KHAC: "Đã chuyển"}
TEN_BANG = {"loai_nha": "Loại nhà", "cap_nha": "Cấp nhà", "ket_cau": "Kết cấu", "thoi_han": "Thời hạn", "xa": "Xã"}


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

    def nap(self) -> None:
        mac_dinh = {"can_bo": self.can_bo, "thoi_han": self.settings.thoi_han_mac_dinh}
        self.lo = nap_lo(self.file, self.dm, self.che_do, mac_dinh, sheet=self.sheet)


def phien_mac_dinh() -> Phien:
    s = Settings.load()
    L = Locators.doc(config_file("locators.toml"))
    dm = DanhMuc.doc(config_file("danh_muc.toml"))
    return Phien(settings=s, store=StateStore(STATE_DB), dm=dm, tao_port=lambda: PlaywrightMplis(s, L, dm))


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


def _form() -> QFormLayout:
    f = QFormLayout()
    f.setVerticalSpacing(14)
    f.setHorizontalSpacing(24)
    return f


def _dat_dong(t: QTableWidget, r: int, gia_tri: tuple[object, ...]) -> None:
    for c, v in enumerate(gia_tri):
        o = QTableWidgetItem("" if v is None else str(v))
        if str(v) in MAU:  # luôn kèm chữ, màu chỉ để nhìn nhanh
            o.setForeground(QColor(MAU[str(v)]))
        t.setItem(r, c, o)


def _dien_bang(t: QTableWidget, dong: list[tuple[object, ...]]) -> None:
    t.setRowCount(len(dong))
    for r, d in enumerate(dong):
        _dat_dong(t, r, d)


def _mo(p: str | Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


class ManHinh(QWidget):
    TIEU_DE, MO_TA = "", ""

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__()
        self.p, self.di_toi = p, di_toi
        self.goc = khung_man(self, self.TIEU_DE, self.MO_TA)

    def hien(self) -> None: ...


class ManLoMoi(ManHinh):
    """M2: chọn file, sheet, chế độ gộp, người xử lý cho cả lô."""
    TIEU_DE, MO_TA = "Lô mới", "Chọn file phiếu chuyển và người nhận hồ sơ ở bước Thụ lý."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.setAcceptDrops(True)
        nut = QPushButton("Chọn file Excel…")
        nut.clicked.connect(self._chon)
        self.the = QLabel("Kéo thả file Excel vào đây, hoặc bấm Chọn file.")
        self.sheet = QComboBox()
        self.che_do = QComboBox()
        self.che_do.addItem("Mỗi dòng một hồ sơ", CheDoGom.MOI_DONG)
        self.che_do.addItem("Gộp các dòng cùng Mã đầu vào", CheDoGom.THEO_MA_DAU_VAO)
        self.can_bo = QComboBox()
        self.can_bo.setEditable(True)
        self.gan_day = QListWidget()
        self.gan_day.itemDoubleClicked.connect(lambda o: self.mo_file(Path(o.data(Qt.ItemDataRole.UserRole))))
        self.tiep = NutChinh("Kiểm tra dữ liệu")
        self.tiep.setEnabled(False)
        self.tiep.clicked.connect(self._sang_kiem_tra)
        f = _form()
        f.addRow("Sheet", self.sheet)
        f.addRow("Chế độ gộp", self.che_do)
        f.addRow("Người xử lý tác vụ tiếp theo", self.can_bo)
        f.addRow("Người nộp", QLabel('Lấy từ cột "Người nộp" trong Excel; ô trống thì tra theo người nhận.'))
        hang = QHBoxLayout()
        hang.addWidget(self.the, 1)
        hang.addWidget(nut)
        phu = QLabel("Lô gần đây, bấm đúp để mở")
        phu.setObjectName("phu")
        lay = self.goc
        lay.addWidget(The(hang))
        lay.addWidget(The(f))
        lay.addWidget(The(phu, self.gan_day), 1)
        hang_nut(lay, self.tiep)

    def hien(self) -> None:
        hien_tai = self.can_bo.currentText()
        self.can_bo.clear()
        self.can_bo.addItems(self.p.settings.ds_can_bo)
        if hien_tai:
            self.can_bo.setCurrentText(hien_tai)
        self.gan_day.clear()
        for x in {r["file"]: r for r in self.p.store.ds_lo()}.values():
            o = QListWidgetItem(f"{x['thoi_gian']} · {Path(x['file']).name} · {x['tom_tat']}")
            o.setData(Qt.ItemDataRole.UserRole, x["file"])
            self.gan_day.addItem(o)

    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        self.mo_file(Path(e.mimeData().urls()[0].toLocalFile()))

    def _chon(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Chọn file Excel", "", "Excel (*.xlsx *.xlsm)")
        if f:
            self.mo_file(Path(f))

    def mo_file(self, f: Path) -> None:
        try:
            ds = ten_sheet(f)
        except (OSError, BadZipFile, InvalidFileException, KeyError) as e:
            QMessageBox.warning(self, "Không đọc được file", str(e))
            return
        self.p.file, self.p.sheet = f, ds[0]
        self.sheet.clear()
        self.sheet.addItems(ds)
        self.p.nap()
        d = self.p.lo.doc
        self.the.setText(f"{f.name}: {len(d.columns)} cột nhận diện, {len(d.rows)} dòng dữ liệu" if d
                         else f"{f.name}: không nhận diện được cấu trúc, xem màn Kiểm tra")
        self.tiep.setEnabled(True)

    def _sang_kiem_tra(self) -> None:
        p = self.p
        p.sheet, p.che_do, p.can_bo = self.sheet.currentText(), CheDoGom(self.che_do.currentData()), self.can_bo.currentText().strip()
        if p.can_bo:
            p.settings.ds_can_bo = [p.can_bo] + [x for x in p.settings.ds_can_bo if x != p.can_bo]
            p.settings.save()
        p.ket_qua, p.can_chay, p.da_reset = {}, None, False
        p.nap()
        self.di_toi(KIEM_TRA)


class ManKiemTra(ManHinh):
    """M3: số hợp lệ/lỗi/cảnh báo, bảng hồ sơ, xem trước, lỗi nhóm theo BR."""
    TIEU_DE, MO_TA = "Kiểm tra dữ liệu", "Chọn một hồ sơ để xem chi tiết. Lỗi chặn phải được sửa trong Excel trước khi chạy."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.tong = HangSo()
        self.bang = _bang("STT", "Dòng", "Tờ/thửa", "Người nhận", "Kiểm tra", rong=3)
        self.bang.itemSelectionChanged.connect(self._xem)
        self.xem = QTextBrowser()
        self.cay = QTreeWidget()
        self.cay.setHeaderLabels(["Mã / dòng", "Nội dung"])
        self.cay.setColumnWidth(0, 200)
        self.tiep = NutChinh("Tiếp tục")
        self.tiep.clicked.connect(self._tiep)
        phai = QVBoxLayout()
        phai.addWidget(The(self.xem))
        phai.addWidget(The(self.cay))
        giua = QHBoxLayout()
        giua.setSpacing(0)
        giua.addWidget(The(self.bang), 3)
        giua.addLayout(phai, 2)
        lay = self.goc
        lay.addWidget(self.tong)
        lay.addLayout(giua, 1)
        hang_nut(lay, self.tiep)

    def hien(self) -> None:
        lo = self.p.lo
        self.bang.setRowCount(0)
        self.cay.clear()
        self.xem.clear()
        self.tiep.setEnabled(False)
        if not lo:
            self.tong.dat([], "Chưa chọn file. Hãy bắt đầu ở màn Lô mới.")
            return
        loi = [v for v in lo.van_de if v.muc == "loi"]
        cb = [v for v in lo.van_de if v.muc != "loi"]
        self.tong.dat([("Hợp lệ", len(lo.ho_so), MAU["Thành công"]), ("Lỗi", len(loi), MAU["Lỗi"] if loi else ""),
                       ("Cảnh báo", len(cb), MAU["Cần kiểm tra"] if cb else "")])
        theo_dong = Counter(v.excel_row for v in cb)
        loi_dong = {v.excel_row for v in loi}
        _dien_bang(self.bang, [(hs.dau.stt, hs.dau.excel_row, f"{hs.dau.thua.so_to}/{hs.dau.thua.so_thua}", hs.dau.ten_chu,
                                "Lỗi" if hs.dau.excel_row in loi_dong else
                                (f"{theo_dong[hs.dau.excel_row]} cảnh báo" if theo_dong[hs.dau.excel_row] else "Tốt"))
                               for hs in lo.ho_so])
        nhom: dict[str, list] = {}
        for v in lo.van_de:
            nhom.setdefault(f"{v.ma} ({'lỗi' if v.muc == 'loi' else 'cảnh báo'})", []).append(v)
        for ten, ds in sorted(nhom.items()):
            g = QTreeWidgetItem([f"{ten}: {len(ds)}", ""])
            g.addChildren([QTreeWidgetItem([f"Dòng {v.excel_row}", v.noi_dung]) for v in ds])
            self.cay.addTopLevelItem(g)
        self.tiep.setEnabled(bool(lo.ho_so) and not [v for v in loi if v.ma != "BR-05"])

    def _xem(self) -> None:
        r = self.bang.currentRow()
        if r < 0 or not self.p.lo:
            return
        d = self.p.lo.ho_so[r].dau
        nguoi = "<br>".join(f"{n.ho_ten} · {n.nam_sinh or '—'} · {che_cccd(n.cccd)}" for n in d.nguoi)
        self.xem.setHtml(f"<b>Tờ {d.thua.so_to}, thửa {d.thua.so_thua}</b><br>Địa chỉ: {d.thua.dia_chi or '—'}<br>"
                         f"Diện tích: {d.thua.dien_tich or '—'} m²<br>Số phát hành: {d.thua.ma_phat_hanh or '—'}<br>"
                         f"Cán bộ XL: {d.can_bo or '—'}<br>Người nộp: {d.nguoi_nop.ho_ten}<br><br>Người nhận:<br>{nguoi}")

    def _tiep(self) -> None:
        self.di_toi(DANH_MUC if self.p.dm.chua_anh_xa(self.p.lo.ho_so) else CHAY)


class ManDanhMuc(ManHinh):
    """M4: gán giá trị MPLIS cho giá trị Excel chưa có, lưu vào danh_muc.toml của người dùng."""
    TIEU_DE, MO_TA = "Ánh xạ danh mục", "Chọn giá trị trên MPLIS tương ứng với chữ trong Excel."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.nhan = QLabel()
        self.bang = _bang("Trường", "Giá trị Excel", "Số hồ sơ", "Giá trị MPLIS")
        nut = NutChinh("Lưu và kiểm tra lại")
        nut.clicked.connect(self.luu)
        lay = self.goc
        lay.addWidget(The(self.nhan, self.bang), 1)
        hang_nut(lay, nut)

    def hien(self) -> None:
        self.dong = list(self.p.dm.chua_anh_xa(self.p.lo.ho_so)) if self.p.lo else []
        thieu = self.p.dm.chua_anh_xa(self.p.lo.ho_so) if self.p.lo else {}
        self.nhan.setText(f"Còn {len(self.dong)} giá trị chưa ánh xạ." if self.dong else "Không còn giá trị nào chưa ánh xạ.")
        _dien_bang(self.bang, [(TEN_BANG.get(b, b), gv, len(thieu[(b, gv)])) for b, gv in self.dong])
        for r, (b, _) in enumerate(self.dong):
            o = QComboBox()
            o.setEditable(True)
            o.addItems(self.p.dm.bang(b))
            o.setCurrentText("")
            self.bang.setCellWidget(r, 3, o)

    def luu(self) -> None:
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


class ManChay(ManHinh):
    """M5: chạy thử hoặc chạy thật. Mặc định chạy thử; chạy thật phải xác nhận."""
    TIEU_DE, MO_TA = "Chạy", "Chạy thử để xem form đã điền. Chạy thật mới tạo hồ sơ trên MPLIS."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.worker: Worker | None = None
        self.hang: dict[str, int] = {}
        self.r_thu, self.r_that = QRadioButton("Chạy thử (điền form, không Lưu)"), QRadioButton("Chạy thật (Lưu lên MPLIS)")
        self.r_thu.setChecked(True)
        self.nhom = QButtonGroup(self)
        self.nhom.addButton(self.r_thu)
        self.nhom.addButton(self.r_that)
        self.chay = NutChinh("Bắt đầu")
        self.chay.clicked.connect(self.bat_dau)
        self.dung = QPushButton("Dừng sau hồ sơ này")
        self.dung.setEnabled(False)
        self.dung.clicked.connect(self._dung)
        self.gioi_han = QLineEdit()
        self.gioi_han.setPlaceholderText("Tất cả")
        self.gioi_han.setValidator(QIntValidator(1, 9999, self.gioi_han))
        self.gioi_han.setFixedWidth(90)
        self.tien_do = QProgressBar()
        self.bang = _bang("Hồ sơ", "Trạng thái", "Mã hồ sơ", "Ghi chú")
        self.bang.itemSelectionChanged.connect(self._xem_anh)
        self.nhat_ky = QPlainTextEdit()
        self.nhat_ky.setReadOnly(True)
        self.anh = QLabel("Chọn một dòng để xem ảnh form.")
        self.anh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tren = QHBoxLayout()
        tren.setSpacing(16)
        tren.addWidget(self.r_thu)
        tren.addWidget(self.r_that)
        tren.addWidget(QLabel("Chạy tối đa"))
        tren.addWidget(self.gioi_han)
        tren.addWidget(QLabel("hồ sơ"))
        tren.addStretch(1)
        tren.addWidget(self.dung)
        tren.addWidget(self.chay)
        duoi = QHBoxLayout()
        duoi.setSpacing(0)
        duoi.addWidget(The(self.nhat_ky), 1)
        duoi.addWidget(The(self.anh), 1)
        lay = self.goc
        lay.addWidget(The(tren, self.tien_do))
        lay.addWidget(The(self.bang), 2)
        lay.addLayout(duoi, 1)

    def hien(self) -> None:
        self.chay.setEnabled(bool(self.p.lo and not self.p.lo.co_loi) and not self.p.dang_chay)

    def bat_dau(self) -> None:
        p = self.p
        if not p.lo or p.lo.co_loi:
            QMessageBox.warning(self, "Chưa chạy được", "Lô còn lỗi chặn, hãy xem màn Kiểm tra dữ liệu.")
            return
        if not p.settings.cho_chay_khi_canh_bao and any(v.muc != "loi" for v in p.lo.van_de):
            QMessageBox.warning(self, "Chưa chạy được", "Lô còn cảnh báo và Cài đặt đang không cho chạy khi có cảnh báo.")
            return
        ho_so = p.can_chay if p.can_chay is not None else p.lo.ho_so
        that = self.r_that.isChecked()
        bo_qua = (TrangThai.CAN_KIEM_TRA, TrangThai.THANH_CONG, TrangThai.DA_CO_SAN, TrangThai.DA_CHUYEN_NGUOI_KHAC)
        con = [hs for hs in ho_so if p.store.get(hs.key).trang_thai not in bo_qua]
        if self.gioi_han.hasAcceptableInput():  # giới hạn chỉ tính hồ sơ còn phải làm
            ho_so = con = con[:int(self.gioi_han.text())]
        if that:
            chon = QMessageBox.question(self, "Xác nhận chạy thật",
                                        f"Tool sẽ xử lý {len(con)} hồ sơ thật trên MPLIS. Có thể dừng sau mỗi hồ sơ. Tiếp tục?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
            if chon != QMessageBox.StandardButton.Yes:
                return
        self.hang = {hs.key: i for i, hs in enumerate(ho_so)}
        _dien_bang(self.bang, [(hs.key.split("|", 1)[-1], "Chờ", "", "") for hs in ho_so])
        self.tien_do.setRange(0, len(ho_so))
        self.tien_do.setValue(0)
        self.nhat_ky.clear()
        opts = RunOptions(dry_run=not that, tai_khoan=p.settings.username,
                          tim_trung_truoc=p.settings.tim_trung_truoc or p.da_reset)  # đã reset thì buộc tra trùng
        self.che_do = "Chạy thật" if that else "Chạy thử"
        self.ho_so_chay = ho_so
        self.worker = Worker(ho_so, p.store, p.tao_port, opts)
        self.worker.event.connect(self._su_kien)
        self.worker.hoi_so.connect(self._hoi_so)
        self.worker.finished.connect(self._xong)
        p.dang_chay = True
        self.chay.setEnabled(False)
        self.dung.setEnabled(True)
        self.worker.start()

    def _dung(self) -> None:
        self.worker.stop()
        self.dung.setEnabled(False)
        self.nhat_ky.appendPlainText("Sẽ dừng sau hồ sơ đang chạy.")

    def _su_kien(self, k: str, st: str, note: str, ma: str) -> None:
        self.nhat_ky.appendPlainText(f"{st}: {k.split('|', 1)[-1]} {ma} {note}".strip())
        if k not in self.hang:
            return
        _dat_dong(self.bang, self.hang[k], (k.split("|", 1)[-1], st, ma, note))
        if st != "Đang chạy":
            self.p.ket_qua[k] = (st, note, ma)
            self.tien_do.setValue(sum(1 for x in self.hang if x in self.p.ket_qua))

    def _hoi_so(self, mo_ta: str, so: str) -> None:
        self.nhat_ky.appendPlainText(f"MPLIS báo trùng số phát hành {so} ({mo_ta}).")
        self.window().raise_()  # cửa sổ Chromium đang che tool
        self.window().activateWindow()
        moi, ok = QInputDialog.getText(self, "Trùng số phát hành",
                                       f"MPLIS báo số {so} của {mo_ta} đã được cấp cho giấy chứng nhận khác.\n"
                                       "Nhập số phát hành mới, hoặc bấm Cancel để chuyển hồ sơ sang Cần kiểm tra:")
        self.worker.tra_loi(moi.strip() if ok else "")

    def _xem_anh(self) -> None:
        o = self.bang.item(self.bang.currentRow(), 3)
        m = re.search(r"Ảnh: (.+?)$", o.text()) if o else None
        pm = QPixmap(m[1]) if m else QPixmap()
        if pm.isNull():
            self.anh.setText("Không có ảnh cho dòng này.")
        else:
            self.anh.setPixmap(pm.scaledToWidth(max(self.anh.width(), 200), Qt.TransformationMode.SmoothTransformation))

    def _xong(self) -> None:
        p = self.p
        p.dang_chay = False
        self.dung.setEnabled(False)
        kq = {hs.key: p.ket_qua[hs.key] for hs in self.ho_so_chay if hs.key in p.ket_qua}
        tom_tat = " · ".join(f"{n} {st}" for st, n in Counter(v[0] for v in kq.values()).most_common())
        p.store.ghi_lo(str(p.file), self.che_do, len(self.ho_so_chay), tom_tat, [hs.key for hs in self.ho_so_chay])
        p.can_chay, p.da_reset = None, False
        self.di_toi(KET_QUA)


class ManKetQua(ManHinh):
    """M6: tổng kết, xuất Excel, mở ảnh/trace, chạy lại dòng lỗi."""
    TIEU_DE, MO_TA = "Kết quả", "Xuất file kết quả hoặc chọn các dòng lỗi để làm lại."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.tong = HangSo()
        self.bang = _bang("Hồ sơ", "Trạng thái", "Mã hồ sơ", "Ghi chú")
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        nut = []
        for lop, ten, h in ((QPushButton, "Mở ảnh/trace", self._mo_tep), (QPushButton, "Thư mục log", lambda: _mo(LOG_DIR)),
                            (QPushButton, "Thư mục trace", lambda: _mo(TRACE_DIR)), (QPushButton, "Chạy lại dòng chọn", self.chay_lai),
                            (NutChinh, "Xuất Excel", self.xuat)):
            b = lop(ten)
            b.clicked.connect(h)
            nut.append(b)
        lay = self.goc
        lay.addWidget(self.tong)
        lay.addWidget(The(self.bang), 1)
        hang_nut(lay, *nut)

    def hien(self) -> None:
        kq = self.p.ket_qua
        self.keys = [hs.key for hs in self.p.lo.ho_so if hs.key in kq] if self.p.lo else []
        dem = Counter(v[0] for v in kq.values())
        self.tong.dat([(st, dem[st], MAU[st]) for st in MAU if dem[st]], "Chưa có kết quả. Hãy chạy một lô ở màn Chạy.")
        _dien_bang(self.bang, [(k.split("|", 1)[-1], kq[k][0], kq[k][2], kq[k][1]) for k in self.keys])

    def xuat(self) -> None:
        if not self.keys:
            return
        try:
            d = xuat_ket_qua(self.p.lo, self.p.ket_qua)
        except PermissionError:
            QMessageBox.warning(self, "Không ghi được", "Hãy đóng file kết quả trong Excel rồi bấm lại.")
            return
        QMessageBox.information(self, "Đã xuất", str(d))

    def _mo_tep(self) -> None:
        o = self.bang.item(self.bang.currentRow(), 3)
        m = re.search(r"(?:Ảnh|trace): (.+?)(?: · |$)", o.text()) if o else None
        if m:
            _mo(m[1])

    def chay_lai(self) -> None:
        p = self.p
        chon = [self.keys[i.row()] for i in self.bang.selectionModel().selectedRows()]
        loi = [k for k in chon if p.ket_qua[k][0] in ("Lỗi", "Cần kiểm tra")]
        chon = [k for k in loi if not p.store.get(k).ma_ho_so]  # tra trùng sẽ gặp chính nó và báo "Đã có sẵn", che mất phần dở
        if len(chon) < len(loi):
            QMessageBox.information(self, "Chạy lại", f"{len(loi) - len(chon)} hồ sơ đã có mã trên MPLIS, không làm lại từ đầu được. "
                                                      "Hãy xử lý tiếp các hồ sơ này trên MPLIS.")
        if not loi:
            QMessageBox.information(self, "Chạy lại", 'Chọn ít nhất một dòng "Lỗi" hoặc "Cần kiểm tra".')
        if not chon:
            return
        hoi = QMessageBox.question(self, "Chạy lại", f"Làm lại {len(chon)} hồ sơ đã chọn? Tool sẽ tra trùng trên MPLIS trước.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
        if hoi != QMessageBox.StandardButton.Yes:
            return
        for k in chon:
            p.store.reset(k)
            p.ket_qua.pop(k, None)
        p.can_chay, p.da_reset = [hs for hs in p.lo.ho_so if hs.key in chon], True
        self.di_toi(CHAY)


class ManLichSu(ManHinh):
    """M7: các lô đã chạy; tìm theo tên file hoặc tờ/thửa."""
    TIEU_DE, MO_TA = "Lịch sử", "Mở lại kết quả hoặc chạy tiếp một lô đã làm."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        self.tim = QLineEdit()
        self.tim.setPlaceholderText("Tìm theo tên file hoặc tờ/thửa (vd: thua3938)")
        self.tim.textChanged.connect(lambda _: self.hien())
        self.bang = _bang("Thời gian", "File", "Chế độ", "Số hồ sơ", "Kết quả")
        mo, tiep = QPushButton("Chạy tiếp"), NutChinh("Mở kết quả")
        mo.clicked.connect(lambda: self.mo(CHAY))
        tiep.clicked.connect(lambda: self.mo(KET_QUA))
        lay = self.goc
        lay.addWidget(The(self.tim, self.bang), 1)
        hang_nut(lay, mo, tiep)

    def hien(self) -> None:
        q = self.tim.text().strip().lower()
        self.ds = [x for x in self.p.store.ds_lo() if not q or q in x["file"].lower() or any(q in k.lower() for k in x["keys"])]
        _dien_bang(self.bang, [(x["thoi_gian"], Path(x["file"]).name, x["che_do"], x["so_ho_so"], x["tom_tat"]) for x in self.ds])

    def mo(self, man: int) -> None:
        r, p = self.bang.currentRow(), self.p
        if r < 0:
            return
        f = Path(self.ds[r]["file"])
        if not f.exists():
            QMessageBox.warning(self, "Không thấy file", str(f))
            return
        p.file, p.sheet = f, None
        p.nap()
        p.ket_qua = {}
        for k in self.ds[r]["keys"]:
            bg = p.store.get(k)
            if bg.so_lan:
                p.ket_qua[k] = (NHAN.get(bg.trang_thai, bg.trang_thai.value), bg.ghi_chu, bg.ma_ho_so)
        self.di_toi(man)


class ManCaiDat(ManHinh):
    """M8: các trường của Settings, tự lưu khi đổi."""
    TIEU_DE, MO_TA = "Cài đặt", "Thay đổi được lưu ngay."

    def __init__(self, p: Phien, di_toi: Callable[[int], None]):
        super().__init__(p, di_toi)
        s = p.settings
        f = _form()
        self.chu: dict[str, QLineEdit] = {}
        for ten, nhan in (("mplis_url", "Địa chỉ MPLIS"), ("username", "Tài khoản của tôi"), ("nguoi_ky", "Người ký"),
                          ("thoi_han_mac_dinh", "Thời hạn mặc định")):
            o = QLineEdit(getattr(s, ten))
            o.editingFinished.connect(self._luu)
            self.chu[ten] = o
            f.addRow(nhan, o)
        self.so: dict[str, QLineEdit] = {}
        for ten, nhan, hi in (("timeout_ms", "Thời gian chờ (ms)", 600_000), ("slow_mo_ms", "Làm chậm (ms)", 10_000)):
            o = QLineEdit(str(getattr(s, ten)))
            o.setValidator(QIntValidator(0, hi, o))
            o.editingFinished.connect(self._luu)
            self.so[ten] = o
            f.addRow(nhan, o)
        self.tich: dict[str, QCheckBox] = {}
        for ten, nhan in (("cho_chay_khi_canh_bao", "Cho chạy khi còn cảnh báo"), ("tim_trung_truoc", "Tra trùng trước khi tạo"),
                          ("headless", "Chạy Chromium ẩn")):
            o = QCheckBox(nhan)
            o.setChecked(getattr(s, ten))
            o.toggled.connect(lambda _=False: self._luu())
            self.tich[ten] = o
            f.addRow("", o)
        xoa, tm = QPushButton("Xóa phiên đăng nhập Chromium"), QPushButton("Mở thư mục dữ liệu")
        xoa.clicked.connect(self._xoa_phien)
        tm.clicked.connect(lambda: _mo(app_dir()))
        lay = self.goc
        lay.addWidget(The(f))
        ban = QLabel(f"Phiên bản {__version__}. Mật khẩu MPLIS không lưu trong tool.")
        ban.setObjectName("phu")
        ban.setIndent(14)
        lay.addWidget(ban)
        lay.addStretch(1)
        hang_nut(lay, tm, xoa)

    def _luu(self) -> None:
        s = self.p.settings
        for ten, o in self.chu.items():
            setattr(s, ten, o.text().strip())
        for ten, o in self.so.items():
            if o.hasAcceptableInput():
                setattr(s, ten, int(o.text()))
        for ten, o in self.tich.items():
            setattr(s, ten, o.isChecked())
        s.save()

    def _xoa_phien(self) -> None:
        if self.p.dang_chay:
            return
        hoi = QMessageBox.question(self, "Xóa phiên", "Lần chạy sau sẽ phải đăng nhập lại. Tiếp tục?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
        if hoi == QMessageBox.StandardButton.Yes:
            shutil.rmtree(BROWSER_PROFILE, ignore_errors=True)


MAN_HINH = [("Lô mới", ManLoMoi), ("Kiểm tra dữ liệu", ManKiemTra), ("Ánh xạ danh mục", ManDanhMuc), ("Chạy", ManChay),
            ("Kết quả", ManKetQua), ("Lịch sử", ManLichSu), ("Cài đặt", ManCaiDat)]
