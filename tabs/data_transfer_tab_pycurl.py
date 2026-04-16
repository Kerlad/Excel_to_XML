"""
Вкладка передачи данных на базе pycurl.
"""
from tabs.data_transfer_tab_base import BaseDataTransferTab


class DataTransferTabPycurl(BaseDataTransferTab):
    def __init__(self):
        super().__init__(tab_title="Передача данных (pycurl)")
    
    def _get_api_module(self):
        try:
            import api.mintrud_api_pycurl as api_module
            return api_module
        except ImportError:
            return None
