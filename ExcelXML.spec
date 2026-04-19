# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ico.ico', '.'),
        ('schema', 'schema'),
        ('data', 'data'),
        ('Protokol_proverki_znanii_OT.docx', '.'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # Сторонние библиотеки
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.workbook',
        'openpyxl.styles',
        'xlrd',
        'xlrd.xldate',
        'lxml',
        'lxml.etree',
        'requests',
        'urllib3',
        'cryptography',
        'cryptography.fernet',
        'PIL',
        # Модули проекта
        'utils',
        'utils.logger',
        'utils.crypto',
        'tabs',
        'tabs.data_entry_tab',
        'tabs.data_view_tab',
        'tabs.data_transfer_tab',
        'tabs.exam_journal_tab',
        'tabs.protocol_tab',
        'tabs.programs_dialog',
        'api',
        'api.mintrud_api',
        'journal',
        'journal.journal_manager',
        'protocol',
        'protocol.commission_manager',
        'protocol.programs_manager',
        'exporters',
        'exporters.xml_exporter',
        'exporters.protocol_exporter',
        'importers',
        'importers.xlsx_importer',
        'importers.xml_importer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ico.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ExcelXML-Mintrud',
)
