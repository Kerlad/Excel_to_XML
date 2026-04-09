--- main.py (原始)


+++ main.py (修改后)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Основной файл запуска приложения Excel-XML для Минтруда
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    # Включение поддержки высокого DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Настройка шрифтов для HiDPI
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()