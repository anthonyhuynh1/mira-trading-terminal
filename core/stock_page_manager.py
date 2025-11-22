from PyQt6.QtCore import QObject, pyqtSignal
from typing import List, Optional
from core.stock_page import StockPage

class StockPageManager(QObject):
    page_added = pyqtSignal(StockPage)
    page_removed = pyqtSignal(str) # page_id
    active_page_changed = pyqtSignal(str) # page_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages: List[StockPage] = []
        self._active_page_id: Optional[str] = None
        self.create_page() # Create initial page

    @property
    def pages(self) -> List[StockPage]:
        return self._pages

    @property
    def active_page(self) -> Optional[StockPage]:
        return self.get_page_by_id(self._active_page_id)

    def create_page(self, name: str = "Untitled", ticker: str = "SPY", activate: bool = True) -> StockPage:
        new_page = StockPage(page_name=name, primary_ticker=ticker)
        self._pages.append(new_page)
        self.page_added.emit(new_page)
        if activate or not self._active_page_id:
            self.set_active_page(new_page.page_id)
        return new_page

    def remove_page(self, page_id: str):
        if len(self._pages) <= 1:
            return # Don't remove the last page

        page_to_remove = self.get_page_by_id(page_id)
        if page_to_remove:
            self._pages.remove(page_to_remove)
            self.page_removed.emit(page_id)

            if self._active_page_id == page_id:
                # If active page is removed, set a new active page
                new_active_page = self._pages[0] if self._pages else None
                if new_active_page:
                    self.set_active_page(new_active_page.page_id)
                else:
                    self._active_page_id = None
                    self.active_page_changed.emit(None)

    def set_active_page(self, page_id: str):
        if self._active_page_id != page_id:
            self._active_page_id = page_id
            self.active_page_changed.emit(page_id)

    def get_page_by_id(self, page_id: str) -> Optional[StockPage]:
        for page in self._pages:
            if page.page_id == page_id:
                return page
        return None
