"""Khung cửa sổ chính. TODO(plan.md Giai đoạn 4): dựng M1–M8 theo docs/wireframe.md."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget, QMainWindow,
                               QStackedWidget, QWidget)

from .. import __version__

MAN_HINH = ["Lô mới", "Kiểm tra dữ liệu", "Ánh xạ danh mục", "Chạy", "Kết quả", "Lịch sử", "Cài đặt"]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Thêm mới nhanh hồ sơ tiếp nhận MPLIS — v{__version__}")
        self.resize(1280, 820)
        self.nav = QListWidget()
        self.nav.addItems(MAN_HINH)
        self.nav.setFixedWidth(220)
        self.stack = QStackedWidget()
        for name in MAN_HINH:  # TODO: thay bằng màn hình thật trong app/screens/
            self.stack.addWidget(QLabel(f"{name} — chưa làm (xem docs/wireframe.md)"))
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        root = QWidget()
        lay = QHBoxLayout(root)
        lay.addWidget(self.nav)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()
