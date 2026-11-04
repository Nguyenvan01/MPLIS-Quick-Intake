from __future__ import annotations

from loguru import logger
from playwright.sync_api import expect

from .base import BasePage


class LoginPage(BasePage):
    def dang_nhap(self, url: str, username: str, password: str) -> None:
        self.page.goto(url)
        if self.el("login.da_dang_nhap").count():
            logger.info("Dùng phiên đăng nhập đã lưu")
            return
        self.el("login.o_tai_khoan").fill(username)
        self.el("login.o_mat_khau").fill(password)
        self.el("login.nut_dang_nhap").click()
        expect(self.el("login.da_dang_nhap")).to_be_visible()
        logger.info("Đăng nhập thành công")
