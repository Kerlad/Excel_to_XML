# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.path.dirname(os.path.abspath('main.py'))],
    binaries=[],
    datas=[
        ('ico.ico', '.'),
        ('schema', 'schema'),
        ('Protokol_proverki_znanii_OT.docx', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'openpyxl', 'lxml.etree', 'requests', 'cryptography.fernet',
        'docx', 'win32inet', 'win32con',
        'win32security', 'win32api', 'pywintypes', 'win32file',
        # Project modules
        'api', 'api.mintrud_api', 'api.payload_builder', 'api.response_parser',
        'api.backends', 'api.backends.base_backend',
        'api.backends.requests_backend', 'api.backends.wininet_backend',
        'tabs', 'tabs.data_entry_tab', 'tabs.data_view_tab',
        'tabs.data_transfer_tab', 'tabs.exam_journal_tab',
        'tabs.protocol_tab', 'tabs.single_worker_protocol_tab',
        'tabs.employee_summary_tab', 'tabs.programs_dialog',
        'db', 'db.database', 'db.schema',
        'db.workers_data_repo', 'db.exam_journal_repo',
        'db.employees_repo', 'db.employee_programs_repo',
        'journal', 'journal.journal_manager',
        'protocol', 'protocol.commission_manager', 'protocol.programs_manager',
        'exporters', 'exporters.xml_exporter', 'exporters.protocol_exporter',
        'importers', 'importers.xlsx_importer', 'importers.xml_importer', 'importers.error_report',
        'utils', 'utils.logger', 'utils.crypto', 'utils.proxy_manager',
        'utils.tahoe_style', 'utils.app_paths',
        'network', 'network.client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy', 'pandas', 'matplotlib', 'scipy', 'sympy',
        'httpx', 'pycurl', 'requests_ntlm', 'requests_negotiate_sspi',
        'tkinter', 'unittest', 'pydoc', 'email', 'http.server',
        'notebook', 'jupyter', 'ipython', 'ipykernel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ExcelXML-Mintrud',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ico.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ExcelXML-Mintrud',
)
