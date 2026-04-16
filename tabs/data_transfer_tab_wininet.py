"""
Вкладка передачи данных на базе WinINET API Windows.
"""
from tabs.data_transfer_tab_base import BaseDataTransferTab


class DataTransferTabWininet(BaseDataTransferTab):
    def __init__(self):
        super().__init__(tab_title="Передача данных (WinINET)")
    
    def _get_api_module(self):
        try:
            import api.mintrud_api_wininet as api_module
            return api_module
        except ImportError:
            return None
