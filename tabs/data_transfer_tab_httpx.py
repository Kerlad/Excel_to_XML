"""
Вкладка передачи данных на базе httpx.
"""
from tabs.data_transfer_tab_base import BaseDataTransferTab


class DataTransferTabHttpx(BaseDataTransferTab):
    def __init__(self):
        super().__init__(tab_title="Передача данных (httpx)")
    
    def _get_api_module(self):
        try:
            import api.mintrud_api_httpx as api_module
            return api_module
        except ImportError:
            return None
