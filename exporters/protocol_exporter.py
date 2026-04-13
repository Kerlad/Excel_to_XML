"""
Экспорт протокола проверки знаний
Заполнение шаблона Protokol_proverki_znanii_OT.xlsx данными комиссии и работников
"""
import os
import shutil
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class ProtocolExporter:
    """Экспорт протокола проверки знаний из данных комиссии и записей работников."""

    @staticmethod
    def generate_from_commission(commission_data: dict, protocol_number: str,
                                  worker_records: list, programs_manager,
                                  output_path: str, template_path: str,
                                  data_dir: str) -> tuple[bool, str]:
        """
        Генерация протокола с данными комиссии и работников.

        commission_data — данные комиссии (org_name, order_number, order_date,
                          exam_date, chairman_fio, chairman_position,
                          member1_fio, member2_fio, member3_fio, union_fio)
        protocol_number — номер протокола
        worker_records — список dict с ключами: last_name, first_name, middle_name,
                         snils, position, result, program, date, protocol
        programs_manager — менеджер программ (метод get_program(program_id))
        output_path — путь для сохранения
        template_path — путь к шаблону
        data_dir — директория data

        Возвращает (success: bool, message: str)
        """
        try:
            from openpyxl import load_workbook
        except ImportError:
            return False, "Установите openpyxl: pip install openpyxl"

        if not os.path.exists(template_path):
            return False, f"Шаблон протокола не найден:\n{template_path}"

        if not worker_records:
            return False, "Нет записей работников для формирования протокола"

        try:
            # Копируем шаблон
            shutil.copy2(template_path, output_path)

            # Открываем копию
            wb = load_workbook(output_path)
            ws = wb.active

            # Разъединяем все merged cells
            ProtocolExporter._unmerge_cells(ws)

            # Заполняем данные комиссии
            ProtocolExporter._fill_commission_data(ws, commission_data, protocol_number)

            # Группируем работников по полному имени
            grouped_workers = ProtocolExporter._group_workers_by_name(worker_records)

            # Заполняем таблицу работников (начиная со строки 28)
            ProtocolExporter._fill_worker_table(ws, grouped_workers, programs_manager)

            wb.save(output_path)
            return True, f"Протокол сформирован.\nФайл сохранён: {output_path}\nЗаписей: {len(grouped_workers)}"

        except Exception as e:
            logger.error(f"Ошибка генерации протокола: {e}", exc_info=True)
            return False, f"Ошибка формирования протокола: {e}"

    @staticmethod
    def _unmerge_cells(ws):
        """Разъединяет все merged cells на листе."""
        merged_ranges = list(ws.merged_cells.ranges)
        for merged_range in merged_ranges:
            ws.unmerge_cells(str(merged_range))

    @staticmethod
    def _fill_commission_data(ws, commission_data: dict, protocol_number: str):
        """Заполняет ячейки шаблона данными комиссии по точным адресам."""
        # Commission header data
        ws['F2'] = protocol_number
        ws['B5'] = commission_data.get('org_name', '')
        ws['G7'] = commission_data.get('exam_date', '')

        # Order: номер + " от " + дата
        order_number = commission_data.get('order_number', '')
        order_date = commission_data.get('order_date', '')
        if order_number and order_date:
            ws['B9'] = f"{order_number} от {order_date}"
        elif order_number:
            ws['B9'] = order_number

        # Commission members
        ws['D12'] = commission_data.get('chairman_fio', '')
        ws['D13'] = commission_data.get('chairman_position', '')
        ws['D14'] = commission_data.get('member1_fio', '')
        ws['D15'] = commission_data.get('member2_fio', '')
        ws['D16'] = commission_data.get('member3_fio', '')
        ws['D18'] = commission_data.get('union_fio', '')

        # Signatures (same as commission members)
        ws['D30'] = commission_data.get('chairman_fio', '')
        ws['D32'] = commission_data.get('member1_fio', '')
        ws['D33'] = commission_data.get('member2_fio', '')
        ws['D34'] = commission_data.get('member3_fio', '')
        ws['D37'] = commission_data.get('union_fio', '')

    @staticmethod
    def _group_workers_by_name(worker_records: list) -> list:
        """
        Группирует работников по полному имени (last_name + first_name + middle_name).
        Возвращает список уникальных работников с объединёнными программами.
        """
        grouped = OrderedDict()

        for rec in worker_records:
            full_name = f"{rec.get('last_name', '')} {rec.get('first_name', '')} {rec.get('middle_name', '')}".strip()
            key = full_name.lower()

            if key not in grouped:
                grouped[key] = {
                    'last_name': rec.get('last_name', ''),
                    'first_name': rec.get('first_name', ''),
                    'middle_name': rec.get('middle_name', ''),
                    'full_name': full_name,
                    'snils': rec.get('snils', ''),
                    'position': rec.get('position', ''),
                    'result': rec.get('result', ''),
                    'programs': []
                }

            # Добавляем программу, если ещё не добавлена
            program = rec.get('program', '').strip()
            if program and program not in grouped[key]['programs']:
                grouped[key]['programs'].append(program)

        return list(grouped.values())

    @staticmethod
    def _fill_worker_table(ws, grouped_workers: list, programs_manager):
        """
        Заполняет таблицу работников начиная со строки 28.
        A28+ = порядковый номер
        B28+ = ФИО (last_name + first_name + middle_name)
        C28+ = должность
        D28+, E28+, G28+, H28+ = пустые
        F28+ = результат
        B20-B24 = объёмы программ
        """
        # Собираем все уникальные программы across всех работников
        all_program_ids = set()
        for worker in grouped_workers:
            for prog_id in worker['programs']:
                all_program_ids.add(prog_id)

        # Формируем строки программ для B20-B24
        program_strings = []
        for prog_id in sorted(all_program_ids, key=lambda x: int(x) if x.isdigit() else 0):
            prog_data = programs_manager.get_program(prog_id) if programs_manager else {}
            name = prog_data.get('name', '') if isinstance(prog_data, dict) else ''
            doc = prog_data.get('doc', '') if isinstance(prog_data, dict) else ''
            hours = prog_data.get('hours', '') if isinstance(prog_data, dict) else ''

            parts = []
            if name:
                parts.append(name)
            if doc:
                parts.append(doc)
            if hours:
                parts.append(f"в объеме {hours} часов")

            program_strings.append(", ".join(parts))

        # Заполняем B20-B24 (максимум 5 программ)
        volume_cells = ['B20', 'B21', 'B22', 'B23', 'B24']
        for i, prog_str in enumerate(program_strings[:5]):
            ws[volume_cells[i]] = prog_str

        # Заполняем таблицу работников (начиная со строки 28)
        start_row = 28
        for idx, worker in enumerate(grouped_workers):
            row = start_row + idx

            # A = порядковый номер
            ws.cell(row=row, column=1).value = idx + 1
            # B = ФИО полностью
            ws.cell(row=row, column=2).value = worker['full_name']
            # C = должность
            ws.cell(row=row, column=3).value = worker['position']
            # D, E = пустые
            ws.cell(row=row, column=4).value = None
            ws.cell(row=row, column=5).value = None
            # F = результат
            ws.cell(row=row, column=6).value = worker['result']
            # G, H = пустые
            ws.cell(row=row, column=7).value = None
            ws.cell(row=row, column=8).value = None
