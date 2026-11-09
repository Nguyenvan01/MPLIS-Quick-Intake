from __future__ import annotations

from playwright.sync_api import Page

from ..locators import Locators


class BasePage:
    def __init__(self, page: Page, L: Locators):
        self.page, self.L = page, L

    def el(self, path: str, scope=None):
        return self.L.get(scope or self.page, path)
