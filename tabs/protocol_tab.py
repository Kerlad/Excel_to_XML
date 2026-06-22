import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QComboBox, QTabWidget, QFormLayout,
    QCheckBox,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from protocol.commission_manager import CommissionManager
from protocol.programs_manager import ProgramsManager
from tabs.programs_dialog import ProgramsDialog
from utils.error_utils import safe_message_box

from utils.toast import Toast

logger = logging.getLogger(__name__)


class _MemberCard(QFrame):
    def __init__(self, title, fio="", position="", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("memberCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        self.title_label = QLabel(title)
        f = self.title_label.font()
        f.setBold(True)
        self.title_label.setFont(f)
        header.addWidget(self.title_label)
        header.addStretch()
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setToolTip("Удалить")
        self.remove_btn.setObjectName("memberRemoveBtn")
        header.addWidget(self.remove_btn)
        layout.addLayout(header)

        form = QFormLayout()
        form.setSpacing(4)
        form.setContentsMargins(0, 0, 0, 0)
        self.fio_input = QLineEdit()
        self.fio_input.setPlaceholderText("Иванов И.И.")
        self.fio_input.setText(fio)
        form.addRow("ФИО:", self.fio_input)

        self.pos_input = QLineEdit()
        self.pos_input.setPlaceholderText("Инженер по ОТ")
        self.pos_input.setText(position)
        form.addRow("Должность:", self.pos_input)

        layout.addLayout(form)

    def set_title(self, text):
        self.title_label.setText(text)

    def get_fio(self):
        return self.fio_input.text().strip()

    def get_position(self):
        return self.pos_input.text().strip()


class ProtocolTab(QWidget):
    def __init__(self, commission_manager: CommissionManager, programs_manager: ProgramsManager,
                 data_dir: str, journal_manager=None, data_source=None):
        super().__init__()
        self.commission = commission_manager
        self.programs = programs_manager
        self.journal_manager = journal_manager
        self.data_source = data_source
        self.data_dir = data_dir
        self.last_save_path = self._load_last_save_path()
        self.member_cards = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tab1(), "Данные организации")
        self.tabs.addTab(self._build_tab2(), "Состав комиссии")
        self.tabs.addTab(self._build_tab3(), "Программы обучения")

        main_layout.addWidget(self.tabs)

        self._load_commission_data()
        self._populate_protocol_combo()

    # ============ Tab 1: Данные протокола и организации ============

    def _build_tab1(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        org_group = QGroupBox("Организация")
        org_layout = QFormLayout(org_group)
        self.org_name_input = QLineEdit()
        self.org_name_input.setPlaceholderText('ООО "Организация"')
        org_layout.addRow("Название организации:", self.org_name_input)

        order_row = QHBoxLayout()
        self.order_number_input = QLineEdit()
        self.order_number_input.setFixedWidth(120)
        self.order_number_input.setPlaceholderText("№ приказа")
        self.order_date_input = QLineEdit()
        self.order_date_input.setFixedWidth(140)
        self.order_date_input.setPlaceholderText("ДД.ММ.ГГГГ")
        order_row.addWidget(self.order_number_input)
        order_row.addWidget(QLabel("от"))
        order_row.addWidget(self.order_date_input)
        order_row.addStretch()
        org_layout.addRow("Приказ о создании комиссии:", order_row)
        layout.addWidget(org_group)

        self.protocol_combo = QComboBox()
        self.protocol_combo.currentTextChanged.connect(self._on_protocol_selected)
        self.exam_date_input = QLineEdit()

        layout.addStretch()
        return w

    # ============ Tab 2: Состав комиссии ============

    def _build_tab2(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        chairman_group = QGroupBox("Председатель комиссии")
        chairman_layout = QFormLayout(chairman_group)
        self.chairman_fio_input = QLineEdit()
        self.chairman_fio_input.setPlaceholderText("Иванов И.И.")
        chairman_layout.addRow("ФИО:", self.chairman_fio_input)
        self.chairman_pos_input = QLineEdit()
        self.chairman_pos_input.setPlaceholderText("Директор")
        chairman_layout.addRow("Должность:", self.chairman_pos_input)
        layout.addWidget(chairman_group)

        members_group = QGroupBox("Члены комиссии")
        self._members_scroll = QScrollArea()
        self._members_scroll.setWidgetResizable(True)
        self._members_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._members_container = QWidget()
        self._members_layout = QVBoxLayout(self._members_container)
        self._members_layout.setSpacing(6)
        self._members_layout.setContentsMargins(0, 0, 0, 0)
        self._members_scroll.setWidget(self._members_container)

        members_inner = QVBoxLayout(members_group)
        members_inner.setSpacing(6)
        members_inner.addWidget(self._members_scroll)
        layout.addWidget(members_group)

        self._add_member_card("Член комиссии №1")
        self._add_member_card("Член комиссии №2")
        self._add_member_card("Член комиссии №3")

        for card in self.member_cards:
            card.remove_btn.hide()

        union_group = QGroupBox("Представитель профсоюза")
        union_layout = QFormLayout(union_group)
        self.union_fio_input = QLineEdit()
        self.union_fio_input.setPlaceholderText("Петров П.П.")
        union_layout.addRow("ФИО:", self.union_fio_input)
        self.union_pos_input = QLineEdit()
        self.union_pos_input.setPlaceholderText("Председатель профкома")
        union_layout.addRow("Должность:", self.union_pos_input)
        layout.addWidget(union_group)

        btn_row = QHBoxLayout()
        self.save_commission_btn = QPushButton("Сохранить данные комиссии")
        self.save_commission_btn.setToolTip("Сохранить введённый состав комиссии для повторного использования")
        self.save_commission_btn.setObjectName("saveCommissionBtn")
        self.save_commission_btn.clicked.connect(self._save_commission_data)
        self.load_commission_btn = QPushButton("Загрузить данные комиссии")
        self.load_commission_btn.setToolTip("Подставить ранее сохранённый состав комиссии")
        self.load_commission_btn.setObjectName("loadCommissionBtn")
        self.load_commission_btn.clicked.connect(self._load_commission_data)
        btn_row.addWidget(self.save_commission_btn)
        btn_row.addWidget(self.load_commission_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        return w

    def _add_member_card(self, title=None, fio="", position=""):
        if len(self.member_cards) >= 3:
            return
        idx = len(self.member_cards) + 1
        if title is None:
            title = f"Член комиссии №{idx}"
        card = _MemberCard(title, fio, position)
        card.remove_btn.clicked.connect(lambda: self._remove_member_card(card))
        self.member_cards.append(card)
        self._members_layout.addWidget(card)
        self._renumber_members()
        return card

    def _remove_member_card(self, card):
        if len(self.member_cards) <= 1:
            return
        self.member_cards.remove(card)
        self._members_layout.removeWidget(card)
        card.deleteLater()
        self._renumber_members()

    def _renumber_members(self):
        for i, card in enumerate(self.member_cards):
            card.set_title(f"Член комиссии №{i + 1}")

    # ============ Tab 3: Программы обучения ============

    def _build_tab3(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        hint = QLabel("Двойной клик по ячейке «Номер документа» или «Часы» для редактирования")
        hint.setObjectName("programsHint")
        layout.addWidget(hint)

        # Режим «обучение программам В по одной программе»
        single_b_group = QGroupBox("Обучение программам В по одной программе")
        single_b_group.setObjectName("singleBGroup")
        sb_layout = QVBoxLayout(single_b_group)
        sb_layout.setContentsMargins(10, 6, 10, 10)
        sb_layout.setSpacing(6)

        self.single_b_checkbox = QCheckBox(
            "Сводить программы 6–29 в одну запись в протоколе"
        )
        self.single_b_checkbox.setToolTip(
            "При включении вместо всех записей по программам 6–29 в протокол "
            "вносится одна сводная запись. Регистрационные номера не меняются."
        )
        sb_layout.addWidget(self.single_b_checkbox)

        sb_form = QFormLayout()
        sb_form.setContentsMargins(0, 0, 0, 0)
        sb_form.setSpacing(6)
        self.single_b_doc_input = QLineEdit()
        self.single_b_doc_input.setPlaceholderText("Номер документа")
        self.single_b_hours_input = QLineEdit()
        self.single_b_hours_input.setPlaceholderText("Часы")
        sb_form.addRow("Номер документа:", self.single_b_doc_input)
        sb_form.addRow("Часы:", self.single_b_hours_input)
        sb_layout.addLayout(sb_form)
        layout.addWidget(single_b_group)

        self._load_single_b_settings()
        self.single_b_checkbox.toggled.connect(self._on_single_b_changed)
        self.single_b_doc_input.editingFinished.connect(self._on_single_b_changed)
        self.single_b_hours_input.editingFinished.connect(self._on_single_b_changed)

        self.programs_table = QTableWidget()
        self.programs_table.setColumnCount(4)
        self.programs_table.setHorizontalHeaderLabels(["№\nпрограммы", "Название", "Номер документа", "Часы"])
        self.programs_table.setAlternatingRowColors(True)
        self.programs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.programs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.programs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.programs_table.verticalHeader().setDefaultSectionSize(28)
        self.programs_table.verticalHeader().setVisible(False)
        self.programs_table.setColumnWidth(0, 100)
        self.programs_table.setColumnWidth(3, 80)
        self.programs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.programs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.programs_table.setColumnWidth(2, 200)
        header = self.programs_table.horizontalHeader()
        header.setDefaultSectionSize(40)
        self.programs_table.doubleClicked.connect(self._on_program_double_click)
        self.programs_table.setObjectName("programsTable")
        layout.addWidget(self.programs_table, 1)

        btn_row = QHBoxLayout()
        save_prog_btn = QPushButton("Сохранить")
        save_prog_btn.setToolTip("Сохранить список программ обучения")
        save_prog_btn.setObjectName("saveProgramsBtn")
        save_prog_btn.clicked.connect(self._save_programs)
        btn_row.addWidget(save_prog_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._populate_programs_table()
        return w

    def _populate_programs_table(self):
        self.programs_table.setRowCount(0)
        programs = self.programs.get_all_programs()
        sorted_ids = sorted(programs.keys(), key=lambda x: int(x) if x.isdigit() else 0)
        for prog_id in sorted_ids:
            prog = programs[prog_id]
            row = self.programs_table.rowCount()
            self.programs_table.insertRow(row)
            items = [prog_id, prog.get("name", ""), prog.get("doc", ""), prog.get("hours", "")]
            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col in [2, 3] and not str(text):
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setText("(двойной клик для ввода)")
                self.programs_table.setItem(row, col, item)

    def _on_program_double_click(self, index):
        col = index.column()
        if col not in [2, 3]:
            return
        row = index.row()
        prog_id_item = self.programs_table.item(row, 0)
        if not prog_id_item:
            return
        prog_id = prog_id_item.text()
        current = self.programs_table.item(row, col).text() if self.programs_table.item(row, col) else ""
        if current == "(двойной клик для ввода)":
            current = ""
        col_name = "Номер документа" if col == 2 else "Часы"
        new_value = self._program_input_dialog(col_name, current, digits_only=(col == 3))
        if new_value is not None:
            self.programs_table.item(row, col).setText(new_value)
            if new_value:
                self.programs_table.item(row, col).setForeground(Qt.GlobalColor.black)
            if col == 2:
                self.programs.programs[prog_id]["doc"] = new_value
            elif col == 3:
                self.programs.programs[prog_id]["hours"] = new_value

    def _program_input_dialog(self, title, current_value, digits_only=False):
        from PySide6.QtWidgets import QDialog as QD
        dialog = QD(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(400)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(16, 16, 16, 16)
        input_field = QLineEdit()
        input_field.setText(current_value)
        input_field.setPlaceholderText(f"Введите {title.lower()}")
        dlg_layout.addWidget(input_field)

        btn_grp = QHBoxLayout()
        ok_btn = QPushButton("ОК")
        ok_btn.setObjectName("dialogPrimaryBtn")
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("dialogDangerBtn")

        def on_ok():
            val = input_field.text().strip()
            if digits_only and val:
                try:
                    float(val)
                except ValueError:
                    QMessageBox.warning(dialog, "Ошибка", "Допускается введение только цифр")
                    return
            dialog.accept()
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        btn_grp.addWidget(ok_btn)
        btn_grp.addWidget(cancel_btn)
        btn_grp.addStretch()
        dlg_layout.addLayout(btn_grp)

        if dialog.exec() == QD.DialogCode.Accepted:
            return input_field.text().strip()
        return None

    def _load_single_b_settings(self):
        """Загружает сохранённое состояние режима «одна программа В»."""
        try:
            cfg = self.programs.get_single_b_settings()
        except Exception:
            cfg = {"single_b_mode": False, "single_b_doc": "", "single_b_hours": ""}
        self.single_b_checkbox.blockSignals(True)
        self.single_b_doc_input.blockSignals(True)
        self.single_b_hours_input.blockSignals(True)
        self.single_b_checkbox.setChecked(bool(cfg.get("single_b_mode")))
        self.single_b_doc_input.setText(str(cfg.get("single_b_doc", "") or ""))
        self.single_b_hours_input.setText(str(cfg.get("single_b_hours", "") or ""))
        self.single_b_checkbox.blockSignals(False)
        self.single_b_doc_input.blockSignals(False)
        self.single_b_hours_input.blockSignals(False)
        self._update_single_b_enabled()

    def _update_single_b_enabled(self):
        enabled = self.single_b_checkbox.isChecked()
        self.single_b_doc_input.setEnabled(enabled)
        self.single_b_hours_input.setEnabled(enabled)

    def _on_single_b_changed(self, *args):
        """Сохраняет настройки режима при изменении."""
        self._update_single_b_enabled()
        try:
            self.programs.set_single_b_settings(
                self.single_b_checkbox.isChecked(),
                self.single_b_doc_input.text().strip(),
                self.single_b_hours_input.text().strip(),
                autosave=True,
            )
        except Exception:
            logger.debug("не удалось сохранить настройки режима", exc_info=True)

    def _save_programs(self):
        ok, msg = self.programs.save()
        try:
            self.programs.set_single_b_settings(
                self.single_b_checkbox.isChecked(),
                self.single_b_doc_input.text().strip(),
                self.single_b_hours_input.text().strip(),
                autosave=True,
            )
        except Exception:
            logger.debug("не удалось сохранить настройки режима", exc_info=True)
        if ok:
            Toast.success(self, "Программы обучения сохранены")
        else:
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", msg)

    # ============ Протокол комбо / автозаполнение даты ============

    def _populate_protocol_combo(self):
        if not hasattr(self, 'journal_manager') or self.journal_manager is None:
            return
        all_records = self.journal_manager.get_all_records()
        protocols = set()
        for rec in all_records:
            if rec.protocol:
                protocols.add(rec.protocol)
        self.protocol_combo.clear()
        self.protocol_combo.addItem("Все")
        for proto in sorted(protocols):
            self.protocol_combo.addItem(proto)

    def _on_protocol_selected(self, protocol_number):
        if protocol_number == "Все" or not protocol_number:
            return
        if not hasattr(self, 'journal_manager') or self.journal_manager is None:
            return
        records = self.journal_manager.get_records_by_protocol(protocol_number)
        if records:
            for rec in records:
                if rec.exam_date:
                    self.exam_date_input.setText(rec.exam_date)
                    break

    # ============ Сохранение / загрузка данных комиссии ============

    def _collect_commission_data(self):
        members = []
        for card in self.member_cards:
            members.append({
                "fio": card.get_fio(),
                "position": card.get_position()
            })
        data = {
            "org_name": self.org_name_input.text().strip(),
            "order_number": self.order_number_input.text().strip(),
            "order_date": self.order_date_input.text().strip(),
            "exam_date": self.exam_date_input.text().strip(),
            "chairman_fio": self.chairman_fio_input.text().strip(),
            "chairman_position": self.chairman_pos_input.text().strip(),
            "member1_fio": members[0]["fio"] if len(members) > 0 else "",
            "member1_position": members[0]["position"] if len(members) > 0 else "",
            "member2_fio": members[1]["fio"] if len(members) > 1 else "",
            "member2_position": members[1]["position"] if len(members) > 1 else "",
            "member3_fio": members[2]["fio"] if len(members) > 2 else "",
            "member3_position": members[2]["position"] if len(members) > 2 else "",
            "union_fio": self.union_fio_input.text().strip(),
            "union_position": self.union_pos_input.text().strip(),
        }
        return data

    def _apply_commission_data(self, data):
        self.org_name_input.setText(data.get("org_name", ""))
        self.order_number_input.setText(data.get("order_number", ""))
        self.order_date_input.setText(data.get("order_date", ""))
        self.exam_date_input.setText(data.get("exam_date", ""))
        self.chairman_fio_input.setText(data.get("chairman_fio", ""))
        self.chairman_pos_input.setText(data.get("chairman_position", ""))
        self.union_fio_input.setText(data.get("union_fio", ""))
        self.union_pos_input.setText(data.get("union_position", ""))

        while self.member_cards:
            card = self.member_cards.pop()
            self._members_layout.removeWidget(card)
            card.deleteLater()

        base_members = []
        for i in range(1, 4):
            fio = data.get(f"member{i}_fio", "")
            pos = data.get(f"member{i}_position", "")
            base_members.append((fio, pos))

        extra = data.get("extra_members", [])
        all_members = list(base_members)
        for em in extra:
            if len(all_members) >= 3:
                break
            all_members.append((em.get("fio", ""), em.get("position", "")))

        for i, (fio, pos) in enumerate(all_members):
            self._add_member_card(f"Член комиссии №{i + 1}", fio, pos)

        for card in self.member_cards:
            card.remove_btn.hide()

    def _save_commission_data(self):
        data = self._collect_commission_data()
        self.commission.data = data
        ok, msg = self.commission.save(data)
        if ok:
            Toast.success(self, "Данные комиссии сохранены")
        else:
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", msg)

    def _load_commission_data(self):
        data = self.commission.load()
        self._apply_commission_data(data)

    # ============ Пути сохранения ============

    def _load_last_save_path(self):
        import json
        settings_file = os.path.join(self.data_dir, "protocol_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('last_save_path', '')
            except (OSError, json.JSONDecodeError) as e:
                logger.debug("Could not load last_save_path: %s", e)
        return ''

    def _save_last_save_path(self, path):
        import json
        settings_file = os.path.join(self.data_dir, "protocol_settings.json")
        settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.debug("Could not load settings: %s", e)
        settings['last_save_path'] = path
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("Could not save settings: %s", e, exc_info=True)

    # ============ Внешние ссылки ============

    def set_data_source(self, data_view_tab):
        self.data_source = data_view_tab

    def set_journal_manager(self, journal_manager):
        self.journal_manager = journal_manager

    # ============ Генерация протокола ============

    def _generate_protocol(self):
        from exporters.protocol_exporter import ProtocolExporter

        commission_data = self._collect_commission_data()

        missing = []
        if not commission_data.get("org_name"):
            missing.append("Название организации")
        if not commission_data.get("order_number"):
            missing.append("Номер приказа")
        if not commission_data.get("chairman_fio"):
            missing.append("ФИО председателя")
        if missing:
            QMessageBox.warning(self, "Ошибка", f"Не заполнены обязательные поля:\n{', '.join(missing)}")
            return

        selected_protocol = self.protocol_combo.currentText()

        if selected_protocol == "Все":
            if not hasattr(self, 'journal_manager') or self.journal_manager is None:
                QMessageBox.warning(self, "Ошибка", "Журнал недоступен")
                return
            all_records = self.journal_manager.get_all_records()
            protocols = sorted(set(rec.protocol for rec in all_records if rec.protocol))
            if not protocols:
                QMessageBox.warning(self, "Ошибка", "Нет протоколов в журнале")
                return
        else:
            protocols = [selected_protocol]

        protocols_with_data = []
        for proto in protocols:
            worker_records = self._get_worker_records_by_protocol(proto)
            if worker_records:
                protocols_with_data.append(proto)

        if not protocols_with_data:
            QMessageBox.warning(self, "Ошибка", "Нет данных работников для выбранных протоколов")
            return

        exam_date = commission_data.get("exam_date", "")
        date_for_filename = ""
        if exam_date:
            try:
                from datetime import datetime
                date_part = exam_date.split()[0] if ' ' in exam_date else exam_date
                for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                    try:
                        dt = datetime.strptime(date_part, fmt)
                        date_for_filename = dt.strftime("%d-%m-%Y")
                        break
                    except ValueError:
                        continue
            except ValueError:
                pass

        if not date_for_filename and exam_date:
            date_for_filename = exam_date.replace('.', '-').replace('/', '-').split()[0]

        from utils.export_safe import safe_filename_part
        if len(protocols_with_data) == 1:
            safe_proto = safe_filename_part(protocols_with_data[0], 'протокол')
            if date_for_filename:
                default_file = f"Протокол {safe_proto} от {date_for_filename}.docx"
            else:
                default_file = f"Протокол {safe_proto}.docx"
        else:
            default_file = "Протоколы.docx"

        if self.last_save_path and os.path.exists(self.last_save_path):
            basename = os.path.basename(self.last_save_path)
            if len(protocols_with_data) == 1:
                if protocols_with_data[0] in basename and "Протоколы" not in basename:
                    default_path = self.last_save_path
                else:
                    default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
            else:
                if "Протоколы" in basename:
                    default_path = self.last_save_path
                else:
                    default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
        elif self.last_save_path and os.path.exists(os.path.dirname(self.last_save_path)):
            default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
        else:
            default_path = default_file

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол",
            default_path,
            "Word Files (*.docx)"
        )
        if not file_path:
            return

        self._save_last_save_path(file_path)

        from utils.app_paths import get_resource_dir
        template_path = os.path.join(
            get_resource_dir(), "templates",
            "Protokol_proverki_znanii_OT.docx"
        )

        if len(protocols_with_data) == 1:
            protocol_number = protocols_with_data[0]
            worker_records = self._get_worker_records_by_protocol(protocol_number)

            success, msg = ProtocolExporter.generate_from_commission(
                commission_data=commission_data,
                protocol_number=protocol_number,
                worker_records=worker_records,
                programs_manager=self.programs,
                output_path=file_path,
                template_path=template_path,
                data_dir=self.data_dir
            )

            if success:
                safe_message_box(self, QMessageBox.Icon.Information, "Успех", msg)
            else:
                safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка генерации", msg)
        else:
            save_dir = QFileDialog.getExistingDirectory(
                self, "Выберите папку для сохранения протоколов",
                os.path.dirname(file_path) if file_path else ""
            )
            if not save_dir:
                return

            saved_count = 0
            for protocol_number in protocols_with_data:
                worker_records = self._get_worker_records_by_protocol(protocol_number)
                if not worker_records:
                    continue

                exam_date = commission_data.get("exam_date", "")
                date_str = ""
                if exam_date:
                    try:
                        from datetime import datetime
                        date_part = exam_date.split()[0] if ' ' in exam_date else exam_date
                        for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                            try:
                                dt = datetime.strptime(date_part, fmt)
                                date_str = "_" + dt.strftime("%d-%m-%Y")
                                break
                            except ValueError:
                                continue
                    except ValueError:
                        pass

                output_file = os.path.join(save_dir, f"Протокол {safe_filename_part(protocol_number, 'протокол')}{date_str}.docx")

                success, _ = ProtocolExporter.generate_from_commission(
                    commission_data=commission_data,
                    protocol_number=protocol_number,
                    worker_records=worker_records,
                    programs_manager=self.programs,
                    output_path=output_file,
                    template_path=template_path,
                    data_dir=self.data_dir
                )

                if success:
                    saved_count += 1

            safe_message_box(self, QMessageBox.Icon.Information, "Успех", f"Сохранено протоколов: {saved_count}\nПапка: {save_dir}")

    def _get_worker_records_by_protocol(self, protocol_number: str) -> list:
        if not hasattr(self, 'journal_manager') or self.journal_manager is None:
            return []

        journal_records = self.journal_manager.get_records_by_protocol(protocol_number)

        records = []
        for rec in journal_records:
            record = {'last_name': rec.last_name,
                'first_name': rec.first_name,
                'middle_name': rec.middle_name,
                'snils': rec.snils,
                'position': rec.position,
                'employer_inn': '',
                'employer_title': '',
                'tc_inn': '',
                'tc_title': '',
                'result': rec.result,
                'program': rec.program_title,
                'program_id': rec.program_id,
                'date': rec.exam_date,
                'protocol': rec.protocol,
                'base_no': rec.base_no}
            records.append(record)
        return records
