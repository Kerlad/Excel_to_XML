"""
PERFORMANCE: Worker-классы для длительных операций в фоновых QThread.
"""
import os
import logging
import traceback
from typing import List, Dict, Any, Optional, Callable
from PySide6.QtCore import QThread, Signal, QObject

logger = logging.getLogger(__name__)


class ExcelImportWorker(QObject):
    """Фоновый импорт Excel-файла с поддержкой прогресса и отмены."""
    progress = Signal(int, int)      # current, total (total=0 если неизвестно)
    status_message = Signal(str)     # текстовый статус
    finished = Signal(list, int, list, str)  # records, error_count, errors, error_msg
    error = Signal(str)

    def __init__(self, file_path: str, password: str = ""):
        super().__init__()
        self.file_path = file_path
        self.password = password
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            from importers.xlsx_importer import load_xlsx

            self.status_message.emit("Открытие файла...")
            self.progress.emit(0, 0)

            if self._cancelled:
                return

            def on_progress(current, total):
                self.progress.emit(current, total)
                if current % 1000 == 0:
                    self.status_message.emit(f"Обработано строк: {current}")

            def on_cancel():
                return self._cancelled

            records, error_details, error_rows_set, error_msg = load_xlsx(
                self.file_path, self.password,
                progress_callback=on_progress,
                cancel_check=on_cancel
            )

            if self._cancelled:
                self.status_message.emit("Импорт отменён")
                return

            error_count = len(error_details)
            self.status_message.emit("Импорт завершён")
            self.finished.emit(records, error_count, error_details, error_msg)

        except Exception as e:
            logger.exception("Excel import failed")
            self.error.emit(f"Ошибка импорта: {e}\n{traceback.format_exc()}")


class XmlGenerationWorker(QObject):
    """Фоновое построение XML для экспорта."""
    progress = Signal(int, int)
    finished = Signal(bytes)
    error = Signal(str)

    def __init__(self, records: List[dict], org_settings: Optional[dict] = None):
        super().__init__()
        self.records = records
        self.org_settings = org_settings
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            from exporters.xml_exporter import build_xml
            total = len(self.records)
            CHUNK = 500
            xml_parts = []
            for i in range(0, total, CHUNK):
                if self._cancelled:
                    return
                chunk = self.records[i:i + CHUNK]
                chunk_xml = build_xml(chunk, self.org_settings)
                xml_parts.append(chunk_xml)
                self.progress.emit(min(i + CHUNK, total), total)

            full_xml = b'\n'.join(xml_parts) if len(xml_parts) > 1 else xml_parts[0]
            self.finished.emit(full_xml)
        except Exception as e:
            logger.exception("XML generation failed")
            self.error.emit(f"Ошибка генерации XML: {e}")


class ApiBulkQueryWorker(QObject):
    """Фоновый массовый запрос по СНИЛС к API Минтруда."""
    progress = Signal(int, int)
    employee_done = Signal(int, dict)  # employee_id, result
    finished = Signal(int, int)  # success_count, error_count
    error = Signal(str)

    def __init__(self, employees: List[dict], api_key: str, proxy_settings: Optional[dict] = None):
        super().__init__()
        self.employees = employees
        self.api_key = api_key
        self.proxy_settings = proxy_settings
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        from api.mintrud_api import MintrudClient, validate_api_key
        from utils.cache import api_throttle, invalidate_summary_cache

        ok, err = validate_api_key(self.api_key)
        if not ok:
            self.error.emit(err)
            return

        client = MintrudClient(backend="auto", proxy_settings=self.proxy_settings)
        success_count = 0
        error_count = 0
        total = len(self.employees)

        for idx, emp in enumerate(self.employees):
            if self._cancelled:
                return

            snils = emp.get('snils', '').strip()
            if not snils:
                error_count += 1
                self.progress.emit(idx + 1, total)
                continue

            api_throttle.wait()
            try:
                result = client.query_by_snils(self.api_key, snils)
                if result.get("success"):
                    records = result.get("records", [])
                    if records:
                        best = records[0]
                        exam_date = best.get('Date', '') or best.get('date', '')
                        protocol = best.get('ProtocolNumber', '') or best.get('protocol', '')
                        base_no = best.get('baseNo', '') or best.get('RegNumber', '')
                        is_passed = best.get('isPassed', '')
                        from db.employee_programs_repo import EmployeeProgramsRepo
                        _process_emp_result = {
                            'emp_id': emp['id'],
                            'exam_date': exam_date,
                            'protocol': protocol,
                            'base_no': base_no,
                            'is_passed': is_passed,
                        }
                        self.employee_done.emit(emp['id'], _process_emp_result)
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.exception("API query failed for employee %s", emp.get('id'))
                error_count += 1

            self.progress.emit(idx + 1, total)

        invalidate_summary_cache()
        self.finished.emit(success_count, error_count)


class PlanGenerationWorker(QObject):
    """Фоновое формирование плана обучения."""
    progress = Signal(int, int)
    finished = Signal(list, str)  # plan_data, plan_title
    error = Signal(str)

    def __init__(self, employees: list, year: int, include_not_trained: bool,
                 include_expired: bool, include_expiring: bool, period_3years: bool):
        super().__init__()
        self.employees_data = employees
        self.year = year
        self.include_not_trained = include_not_trained
        self.include_expired = include_expired
        self.include_expiring = include_expiring
        self.period_3years = period_3years
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            from tabs.employee_summary_tab import _get_employee_status
            plan_data = []
            total = len(self.employees_data)
            for idx, (emp_id, edata) in enumerate(self.employees_data.items()):
                if self._cancelled:
                    return
                emp = edata['emp']
                progs = edata['programs']
                status, reason, priority, last_exam_date, expiry_date, prog = \
                    _get_employee_status(emp, progs, self.period_3years)

                include = False
                if status == 'not_trained' and self.include_not_trained:
                    include = True
                elif status == 'expired' and self.include_expired:
                    include = True
                elif status == 'trained' and self.include_expiring and expiry_date:
                    try:
                        from datetime import datetime
                        ey = int(expiry_date.split('.')[-1]) if expiry_date else 0
                        if ey == self.year:
                            include = True
                    except (ValueError, IndexError):
                        pass

                if include:
                    plan_data.append({
                        'last_name': emp['last_name'],
                        'first_name': emp['first_name'],
                        'middle_name': emp['middle_name'],
                        'snils': emp['snils'],
                        'position': emp['position'],
                        'program': prog,
                        'last_exam_date': last_exam_date,
                        'expiry_date': expiry_date,
                        'reason': reason,
                        'priority': priority,
                    })

                self.progress.emit(idx + 1, total)

            self.finished.emit(plan_data, f"План обучения на {self.year} год")
        except Exception as e:
            logger.exception("Plan generation failed")
            self.error.emit(f"Ошибка формирования плана: {e}\n{traceback.format_exc()}")
