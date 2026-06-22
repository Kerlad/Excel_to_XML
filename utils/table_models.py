"""
PERFORMANCE: QAbstractTableModel для виртуализации больших таблиц.
Заменяет QTableWidget + setItem() на Model/View архитектуру.
"""
import logging
from typing import List, Optional, Any, Dict, Callable
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QTimer
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)


def deferred_model_reset(model: QAbstractTableModel, reset_fn: Callable[[], None]) -> None:
    """PERFORMANCE: deferred beginResetModel/endResetModel via QTimer to avoid UI freeze."""
    QTimer.singleShot(0, lambda: (
        model.beginResetModel(),
        reset_fn(),
        model.endResetModel(),
    ))


FIELD_KEYS = ['last_name', 'first_name', 'middle_name', 'snils', 'position',
              'employer_inn', 'employer_title', 'tc_inn', 'tc_title',
              'result', 'program', 'date', 'protocol']

COLUMN_LABELS = [
    "Фамилия", "Имя", "Отчество", "СНИЛС", "Должность",
    "ИНН\nзаказчика", "Наименование\nзаказчика", "ИНН\nУЦ",
    "Наименование\nУЦ", "Результат", "№ программы", "Дата", "№ протокола"
]

JOURNAL_FIELD_NAMES = [
    "№ протокола", "Дата экзамена", "Фамилия", "Имя", "Отчество", "СНИЛС",
    "Рег. номер", "№ программы", "Название программы", "Должность",
    "Результат", "SetId", "Дата отправки", "Статус"
]


class MultiColumnFilterProxyModel(QSortFilterProxyModel):
    """PERFORMANCE: фильтрация по всем колонкам одновременно."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        filter_text = self.filterRegularExpression().pattern()
        if not filter_text:
            return True
        model = self.sourceModel()
        for col in range(model.columnCount()):
            idx = model.index(source_row, col, source_parent)
            data = model.data(idx, Qt.ItemDataRole.DisplayRole)
            if data and filter_text.lower() in str(data).lower():
                return True
        return False


class DataViewTableModel(QAbstractTableModel):
    """PERFORMANCE: модель для вкладки 'Просмотр данных' (до 5000+ записей)."""

    def __init__(self, field_keys: List[str] = None, headers: List[str] = None, parent=None):
        super().__init__(parent)
        from .table_models import FIELD_KEYS as _FK, COLUMN_LABELS as _CL
        self._field_keys = field_keys or _FK
        self._headers = headers or _CL
        self._data: List[List[str]] = []
        self._raw_records: List[dict] = []
        self._highlight_col: int = -1
        self._highlight_colors: Dict[int, QColor] = {}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self._data) or col >= len(self._headers):
            return None

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._data[row][col]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter.value
        if role == Qt.ItemDataRole.BackgroundRole:
            if col in self._highlight_colors:
                return self._highlight_colors[col]
            if col == self._highlight_col:
                return QColor("#FFF0F0")
        if role == Qt.ItemDataRole.ForegroundRole:
            if col in self._highlight_colors or col == self._highlight_col:
                return QColor("#212529")
        if role == Qt.ItemDataRole.UserRole:
            return self._raw_records[row].get('id') if row < len(self._raw_records) else None
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section] if section < len(self._headers) else ""
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.EditRole and index.isValid():
            self._data[index.row()][index.column()] = str(value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def load_records(self, records: List[dict]) -> None:
        """PERFORMANCE: быстрая загрузка данных через beginResetModel/endResetModel."""
        self.beginResetModel()
        self._raw_records = records
        self._data = []
        for rec in records:
            row = [str(rec.get(k, '')) for k in self._field_keys]
            self._data.append(row)
        self.endResetModel()

    def get_record_at(self, row: int) -> Optional[dict]:
        if 0 <= row < len(self._raw_records):
            return self._raw_records[row]
        return None

    def get_all_raw_records(self) -> List[dict]:
        return self._raw_records

    def set_highlight_column(self, col: int) -> None:
        self._highlight_col = col

    def set_cell_color(self, col: int, color: QColor) -> None:
        self._highlight_colors[col] = color

    def get_row_data(self, source_row: int) -> dict:
        data = {}
        if source_row < len(self._raw_records):
            data = dict(self._raw_records[source_row])
        for i, k in enumerate(self._field_keys):
            if k not in data:
                data[k] = self._data[source_row][i] if source_row < len(self._data) else ''
        return data

    def set_cell_value(self, source_row: int, col: int, value: str) -> None:
        if 0 <= source_row < len(self._data) and 0 <= col < len(self._headers):
            self._data[source_row][col] = value
            idx = self.index(source_row, col)
            self.dataChanged.emit(idx, idx)

    def get_record_id(self, source_row: int) -> Optional[int]:
        if 0 <= source_row < len(self._raw_records):
            return self._raw_records[source_row].get('id')
        return None


class ExamJournalTableModel(QAbstractTableModel):
    """PERFORMANCE: модель для журнала проверки знаний."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records: List = []
        self._headers = JOURNAL_FIELD_NAMES

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self._records) or col >= len(self._headers):
            return None
        rec = self._records[row]
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_col_value(rec, col)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter.value
        if role == Qt.ItemDataRole.ForegroundRole and col == 13:
            from PySide6.QtGui import QColor
            return QColor("#28A745") if rec.status == "received" else QColor("#E67E22")
        if role in (Qt.ItemDataRole.ForegroundRole, Qt.ItemDataRole.BackgroundRole) and col < 13:
            from utils.tahoe_style import get_journal_status_colors
            bg, fg = get_journal_status_colors(rec.status)
            return fg if role == Qt.ItemDataRole.ForegroundRole else bg
        if role == Qt.ItemDataRole.FontRole and col == 13:
            f = self._bold_font()
            return f
        if role == Qt.ItemDataRole.UserRole:
            return rec.uuid
        return None

    def _bold_font(self):
        from PySide6.QtGui import QFont
        f = QFont()
        f.setBold(True)
        return f

    def _get_col_value(self, rec, col: int) -> str:
        mapping = [
            rec.protocol,
            rec.exam_date.split()[0] if rec.exam_date else "",
            rec.last_name, rec.first_name, rec.middle_name,
            rec.snils, rec.base_no, rec.program_id,
            rec.program_title, rec.position, rec.result,
            rec.set_id,
            rec.send_date.split()[0] if rec.send_date else "",
            "получен" if rec.status == "received" else "ожидает",
        ]
        return str(mapping[col]) if col < len(mapping) else ""

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section] if section < len(self._headers) else ""
        return None

    def load_records(self, records: List) -> None:
        self.beginResetModel()
        self._records = records
        self.endResetModel()

    def get_record(self, row: int):
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def get_records(self) -> List:
        return self._records

    def refresh_colors(self) -> None:
        """Перерисовывает ячейки при смене темы (без перезагрузки данных)."""
        if not self._records:
            return
        top = self.index(0, 0)
        bottom = self.index(len(self._records) - 1, self.columnCount() - 1)
        self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole])


class EmployeeSummaryTableModel(QAbstractTableModel):
    """PERFORMANCE: модель для вкладки 'Сводка по сотрудникам'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._headers: List[str] = []
        self._data: List[List[str]] = []
        self._employee_ids: List[int] = []
        self._sort_column: int = -1
        self._sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self._data) or col >= len(self._headers):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self._data[row][col]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter.value
        if role == Qt.ItemDataRole.UserRole:
            return self._employee_ids[row] if row < len(self._employee_ids) else None
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section] if section < len(self._headers) else ""
        return None

    def set_headers(self, headers: List[str]) -> None:
        self._headers = headers

    def load_data(self, rows: List[List[str]], emp_ids: List[int]) -> None:
        """PERFORMANCE: загрузка данных с beginResetModel."""
        self.beginResetModel()
        self._data = rows
        self._employee_ids = emp_ids
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """PERFORMANCE: сортировка на уровне модели."""
        self.layoutAboutToBeChanged.emit()
        indices = list(range(len(self._data)))
        indices.sort(key=lambda i: self._data[i][column] if column < len(self._data[i]) else "",
                     reverse=(order == Qt.SortOrder.DescendingOrder))
        self._data = [self._data[i] for i in indices]
        self._employee_ids = [self._employee_ids[i] for i in indices]
        self._sort_column = column
        self._sort_order = order
        self.layoutChanged.emit()
