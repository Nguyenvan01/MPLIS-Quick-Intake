from __future__ import annotations

from playwright.sync_api import Page, expect

from ..locators import Locators


class BasePage:
    def __init__(self, page: Page, L: Locators):
        self.page, self.L = page, L

    def el(self, path: str, scope=None):
        return self.L.get(scope or self.page, path)

    def dien_o(self, path: str, value: str, scope=None, kind: str = "text") -> None:
        """Điền một ô và kiểm tra ngay giá trị đã vào."""
        box = self.el(path, scope)
        if kind == "select":
            box.select_option(label=value)          # TODO: nếu là combobox tự viết, đổi cách chọn
            return
        box.fill(value)
        expect(box).to_have_value(value)
