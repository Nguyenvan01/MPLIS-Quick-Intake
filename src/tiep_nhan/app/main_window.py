"""Cửa sổ chính: thanh điều hướng và các màn hình trong app/screens.py."""
from __future__ import annotations

import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                               QStackedWidget, QWidget)

from .. import __version__
from .giao_dien import ap_giao_dien
from .screens import MAN_HINH, Phien, phien_mac_dinh


class MainWindow(QMainWindow):
    def __init__(self, phien: Phien | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"Thêm mới nhanh hồ sơ tiếp nhận MPLIS — v{__version__}")
        self.resize(1280, 820)
        self.phien = phien or phien_mac_dinh()
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(248)
        self.nav.setSpacing(2)
        self.stack = QStackedWidget()
        self.man = [lop(self.phien, self.di_toi) for _, lop in MAN_HINH]
        for i, ((ten, _), m) in enumerate(zip(MAN_HINH, self.man)):
            muc = QListWidgetItem(f"{i + 1}   {ten}" if i < 5 else ten)  # 5 màn đầu là các bước nối tiếp của một lô
            muc.setSizeHint(QSize(0, 46))  # QSS padding không làm tăng chiều cao dòng của QListWidget
            self.nav.addItem(muc)
            self.stack.addWidget(m)
        self.nav.currentRowChanged.connect(self._doi_man)
        self.nav.setCurrentRow(0)
        root = QWidget()
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.nav)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def di_toi(self, i: int) -> None:
        self.nav.setCurrentRow(i)
        self.man[i].hien()  # gọi lại cả khi đang ở sẵn màn đó, vì dữ liệu lô đã đổi

    def _doi_man(self, i: int) -> None:
        self.stack.setCurrentIndex(i)
        self.man[i].hien()

    def closeEvent(self, e: QCloseEvent) -> None:
        if self.phien.dang_chay:  # đóng QThread đang chạy làm hỏng ứng dụng và có thể ngắt giữa lúc ghi
            QMessageBox.warning(self, "Đang chạy", 'Hãy bấm "Dừng sau hồ sơ này" và chờ lô dừng rồi mới đóng.')
            e.ignore()
        else:
            e.accept()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    ap_giao_dien(app)
    w = MainWindow()
    w.show()
    return app.exec()
