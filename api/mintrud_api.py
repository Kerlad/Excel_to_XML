"""
Модуль работы с API Минтруда
Отправка наборов записей и получение регистрационных номеров
"""
import os
import io
import time
import base64
import json
import zipfile
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(filename='api_requests.log', level=logging.INFO, encoding='utf-8')
error_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
os.makedirs(error_log_path, exist_ok=True)
error_log_file = os.path.join(error_log_path, "error_response.txt")

API_URL = "https://edu.rosmintrud.ru/api/set/push"
GET_URL = "https://edu.rosmintrud.ru/api/GetEducatedPersonXML"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


# ============ Сохранение API-ключа ============

def _get_derive_key():
    """Получение ключа шифрования на основе имени пользователя системы."""
    import hashlib
    username = os.environ.get('USERNAME', 'default_user').encode('utf-8')
    return hashlib.sha256(username).digest()


def save_api_key(api_key, data_dir):
    """Сохранение API-ключа в зашифрованном виде (AES через Fernet)."""
    try:
        from cryptography.fernet import Fernet

        key = _get_derive_key()
        fernet_key = base64.urlsafe_b64encode(key)
        fernet = Fernet(fernet_key)

        encrypted = fernet.encrypt(api_key.encode('utf-8'))

        key_file = os.path.join(data_dir, "api_key.json")
        with open(key_file, 'w', encoding='utf-8') as f:
            json.dump({
                "key": encrypted.decode('utf-8'),
                "created": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        return True, "Ключ сохранён"
    except ImportError:
        # Если cryptography нет — используем базовое XOR-шифрование
        return _save_api_key_xor(api_key, data_dir)
    except Exception as e:
        return False, f"Ошибка сохранения: {e}"


def load_api_key(data_dir):
    """Загрузка API-ключа из файла."""
    key_file = os.path.join(data_dir, "api_key.json")
    if not os.path.exists(key_file):
        return None
    try:
        with open(key_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        encrypted = data.get('key', '')

        # Пробуем Fernet
        try:
            from cryptography.fernet import Fernet
            import base64
            key = _get_derive_key()
            fernet_key = base64.urlsafe_b64encode(key)
            fernet = Fernet(fernet_key)
            return fernet.decrypt(encrypted.encode('utf-8')).decode('utf-8')
        except ImportError:
            return _load_api_key_xor(data_dir)
        except Exception:
            return None
    except Exception:
        return None


def _save_api_key_xor(api_key, data_dir):
    """Резервный метод шифрования — XOR с хешем."""
    key = hashlib.sha256(os.environ.get('USERNAME', 'default_user').encode()).digest()
    key_bytes = api_key.encode('utf-8')
    encrypted = bytes([key_bytes[i] ^ key[i % len(key)] for i in range(len(key_bytes))])
    encoded = base64.b64encode(encrypted).decode('utf-8')
    key_file = os.path.join(data_dir, "api_key.json")
    with open(key_file, 'w', encoding='utf-8') as f:
        json.dump({"key": encoded, "created": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    return True, "Ключ сохранён"


def _load_api_key_xor(data_dir):
    """Расшифровка XOR."""
    key_file = os.path.join(data_dir, "api_key.json")
    with open(key_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    encoded = data.get('key', '')
    encrypted = base64.b64decode(encoded)
    key = hashlib.sha256(os.environ.get('USERNAME', 'default_user').encode()).digest()
    decrypted = bytes([encrypted[i] ^ key[i % len(key)] for i in range(len(encrypted))])
    return decrypted.decode('utf-8')


def validate_api_key(api_key):
    """Проверка корректности API-ключа (32 символа)."""
    if not api_key:
        return False, "API ключ не введён"
    if len(api_key) != 32:
        return False, f"Длина ключа: {len(api_key)} (требуется 32 символа)"
    return True, ""


# ============ Отправка XML на сервер ============

def push_xml(api_key, xml_file_path, xsd_path=None):
    """
    Отправка XML файла на сервер Минтруда.

    Алгоритм (BR-2):
    1. Создаётся Request.xml с ApiKey и NeedSend=false
    2. Файл данных упаковывается в .olot архив
    3. Отправляются два файла: Request.xml и .olot через multipart/form-data

    Возвращает dict:
        success: bool
        set_id: str (при успехе)
        message: str
        error: str (при ошибке)
    """
    # Валидация ключа
    ok, err = validate_api_key(api_key)
    if not ok:
        return {"success": False, "error": err}

    if not os.path.exists(xml_file_path):
        return {"success": False, "error": "Файл XML не найден"}

    try:
        # Читаем XML данных
        with open(xml_file_path, 'rb') as f:
            data_xml_content = f.read()

        # Формируем Request.xml
        request_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>{api_key}</ApiKey>
    <NeedSend>false</NeedSend>
</Request>'''

        # Создаём .olot архив (ZIP с Data.xml внутри — сервер требует именно Data.xml с заглавной D)
        olot_buffer = io.BytesIO()
        with zipfile.ZipFile(olot_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('Data.xml', data_xml_content)
        olot_data = olot_buffer.getvalue()

        # Формируем multipart/form-data с двумя файлами
        # Вариант: разные имена полей — xml и olot
        logging.info(f"Отправка XML на {API_URL}")
        response = requests.post(
            API_URL,
            files={
                'xml': ('Request.xml', request_xml.encode('utf-8'), 'text/xml'),
                'olot': ('data.olot', olot_data, 'application/octet-stream'),
            },
            headers=HEADERS,
            verify=False,
            timeout=30
        )

        response_text = response.text
        # Если response.text содержит кракозябры — декодируем вручную
        try:
            response_bytes = response.content
            response_text = response_bytes.decode('utf-8')
        except Exception:
            pass

        logging.info(f"Ответ сервера: HTTP {response.status_code}")
        logging.info(f"Полный ответ: {response_text}")
        logging.info(f"Response headers: {dict(response.headers)}")

        # Парсим ответ
        try:
            root = ET.fromstring(response_text)
        except ET.ParseError:
            if response.status_code == 200:
                return {"success": True, "set_id": "unknown", "message": response_text[:200]}
            _save_error_log(response_text)
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: Не удалось разобрать ответ",
                "raw_response": response_text[:1000]
            }

        if root.tag == "Response":
            set_id_elem = root.find("SetId")
            send_elem = root.find("SendEducatedPerson")
            msg_elem = root.find("Message")

            set_id = set_id_elem.text if set_id_elem is not None else ""
            send_edu = send_elem.text if send_elem is not None else "false"
            msg = msg_elem.text if msg_elem is not None else ""

            logging.info(f"Успех: SetId={set_id}, SendEducatedPerson={send_edu}")

            return {
                "success": True,
                "set_id": set_id,
                "send_educated_person": send_edu.lower() == "true",
                "message": msg
            }

        elif root.tag == "Error":
            status_code_elem = root.find("StatusCode")
            msg_elem = root.find("Message")

            status_code = status_code_elem.text if status_code_elem is not None else "unknown"
            msg = msg_elem.text if msg_elem is not None else ""

            error_msg = _format_error(status_code, msg)
            logging.error(f"Ошибка: {status_code} - {msg}")
            _save_error_log(response_text)

            return {"success": False, "error": error_msg, "raw_response": response_text[:1000]}

        else:
            _save_error_log(response_text)
            return {"success": False, "error": f"Неизвестный формат ответа: {root.tag}", "raw_response": response_text[:500]}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Таймаут соединения. Повторите попытку."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Нет соединения с сервером Минтруда"}
    except Exception as e:
        logging.error(f"Критическая ошибка отправки: {e}")
        return {"success": False, "error": f"Ошибка: {e}"}


def _save_error_log(text):
    """Сохранение полного ответа сервера в файл лога."""
    try:
        with open(error_log_file, 'w', encoding='utf-8-sig') as f:
            f.write(text)
    except Exception as e:
        logging.error(f"Ошибка записи лога: {e}")


def _format_error(status_code, message):
    """Форматирование сообщения об ошибке."""
    error_map = {
        "400": "Ошибка валидации XML. Проверьте соответствие схеме XSD",
        "401": "Ошибка авторизации. Проверьте API ключ",
        "403": "Доступ запрещён",
        "500": "Ошибка сервера Минтруда. Повторите попытку позже",
        "502": "Шлюз недоступен",
        "503": "Сервис временно недоступен",
    }
    user_msg = error_map.get(str(status_code), message)
    return f"[{status_code}] {user_msg}"


# ============ Запрос данных по SetId ============

def get_by_set_id(api_key, set_id, page_size=5000):
    """
    Запрос регистрационных номеров по SetId.
    
    POST на GET_URL с фильтром SetId.
    Поддерживает пагинацию — собирает все страницы.
    
    Возвращает:
        {"success": bool, "records": list, "error": str}
    """
    ok, err = validate_api_key(api_key)
    if not ok:
        return {"success": False, "error": err}

    if not set_id:
        return {"success": False, "error": "SetId не введён"}

    all_records = []
    page_no = 1

    while True:
        # Строгий порядок тегов: ApiKey, PageNo, PageSize, SetId
        xml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{api_key}</ApiKey>
    <PageNo>{page_no}</PageNo>
    <PageSize>{page_size}</PageSize>
    <SetId>{set_id}</SetId>
</EducatedPersonFilter>'''

        result = _fetch_page(xml_content, f"стр. {page_no}", page_size)
        if result is None:
            break

        records = result.get("records", [])
        all_records.extend(records)

        if not result.get("has_more", False):
            break

        page_no += 1
        time.sleep(0.5)

    return {"success": True, "records": all_records}


# ============ Запрос данных по СНИЛС ============

def get_by_snils(api_key, snils, page_size=100):
    """
    Запрос регистрационных номеров по СНИЛС.

    POST на GET_URL с фильтром Snils.
    Поддерживает пагинацию.

    Возвращает:
        {"success": bool, "records": list, "error": str}
    """
    ok, err = validate_api_key(api_key)
    if not ok:
        return {"success": False, "error": err}

    if not snils:
        return {"success": False, "error": "СНИЛС не введён"}

    all_records = []
    page_no = 1

    while True:
        xml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{api_key}</ApiKey>
    <PageNo>{page_no}</PageNo>
    <PageSize>{page_size}</PageSize>
    <Snils>{snils}</Snils>
</EducatedPersonFilter>'''

        result = _fetch_page(xml_content, f"стр. {page_no}", page_size)
        if result is None:
            break

        records = result.get("records", [])
        all_records.extend(records)

        if not result.get("has_more", False):
            break

        page_no += 1
        time.sleep(0.5)

    return {"success": True, "records": all_records}


def _fetch_page(xml_content, page_label="", page_size=100):
    """
    Выполнение одного POST-запроса к GetEducatedPersonXML.
    Возвращает {"records": [...], "has_more": bool} или None при ошибке.
    """
    files = {'file': ('request.xml', xml_content, 'text/xml')}

    try:
        response = requests.post(GET_URL, files=files, headers=HEADERS, verify=False, timeout=30)
        response.encoding = 'utf-8'
        response_text = response.text

        if response.status_code == 500:
            logging.error(f"Ошибка 500 при запросе {page_label}: {response_text[:300]}")
            return None

        if response.status_code != 200:
            logging.error(f"Ошибка HTTP {response.status_code} при запросе {page_label}")
            return None

        # Проверка на <Error> в теле
        if "<Error>" in response_text:
            try:
                root = ET.fromstring(response_text)
                if root.tag == "Error":
                    sc = root.find("StatusCode")
                    msg = root.find("Message")
                    sc_text = sc.text if sc is not None else ""
                    msg_text = msg.text if msg is not None else ""
                    logging.error(f"Логическая ошибка: {sc_text} - {msg_text}")
                    return None
            except ET.ParseError:
                pass

        # Проверка на наличие записей
        if "<RegistryRecord" not in response_text:
            return {"records": [], "has_more": False}

        # Парсинг записей
        records = _parse_registry_records(response_text)

        return {"records": records, "has_more": len(records) == page_size}

    except Exception as e:
        logging.error(f"Критическая ошибка запроса {page_label}: {e}")
        return None


def _parse_registry_records(response_text):
    """Парсинг RegistryRecord из ответа."""
    records = []
    try:
        root = ET.fromstring(response_text)
        for record in root.findall('.//RegistryRecord'):
            rec = {}
            # Атрибуты RegistryRecord
            rec['baseNo'] = record.get('baseNo', '')
            rec['internalExamination'] = record.get('internalExamination', '')
            rec['setId'] = record.get('setId', '')
            rec['baseDateCreated'] = record.get('baseDateCreated', '')
            rec['outerId'] = record.get('outerId', '')

            # Worker
            worker = record.find('Worker')
            if worker is not None:
                rec['LastName'] = _tag_text(worker, 'LastName')
                rec['FirstName'] = _tag_text(worker, 'FirstName')
                rec['MiddleName'] = _tag_text(worker, 'MiddleName')
                rec['Snils'] = _tag_text(worker, 'Snils')
                rec['Position'] = _tag_text(worker, 'Position')

            # Test
            test = record.find('Test')
            if test is not None:
                rec['learnProgramId'] = test.get('learnProgramId', '')
                rec['isPassed'] = test.get('isPassed', '')
                rec['Date'] = _tag_text(test, 'Date')
                rec['ProtocolNumber'] = _tag_text(test, 'ProtocolNumber')
                rec['LearnProgramTitle'] = _tag_text(test, 'LearnProgramTitle')

            records.append(rec)
    except ET.ParseError as e:
        logging.error(f"Ошибка парсинга записей: {e}")

    return records


def _tag_text(parent, tag_name):
    """Получение текста дочернего элемента."""
    elem = parent.find(tag_name)
    return elem.text.strip() if elem is not None and elem.text else ''


# ============ Экспорт результатов в XLSX ============

def export_records_to_xlsx(records, file_path):
    """
    Экспорт записей из API в XLSX файл.
    
    Столбцы: Номер записи в реестре (baseNo), Фамилия, Имя, Отчество,
             СНИЛС, Номер программы, Название программы, Номер протокола, Дата
    """
    try:
        from openpyxl import Workbook
    except ImportError:
        return False, "Установите openpyxl: pip install openpyxl"

    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Регистрационные номера"

        headers = [
            "Номер записи в реестре", "Фамилия", "Имя", "Отчество",
            "СНИЛС", "Номер программы", "Название программы",
            "Номер протокола", "Дата"
        ]
        ws.append(headers)

        # Стилизация заголовков
        from openpyxl.styles import Font, PatternFill, Alignment
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4169E1", end_color="4169E1", fill_type="solid")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for rec in records:
            row = [
                rec.get('baseNo', ''),
                rec.get('LastName', ''),
                rec.get('FirstName', ''),
                rec.get('MiddleName', ''),
                rec.get('Snils', ''),
                rec.get('learnProgramId', ''),
                rec.get('LearnProgramTitle', ''),
                rec.get('ProtocolNumber', ''),
                rec.get('Date', '')
            ]
            ws.append(row)

        # Автоширина столбцов
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

        wb.save(file_path)
        return True, f"Файл сохранён: {file_path}"

    except Exception as e:
        logging.error(f"Ошибка экспорта XLSX: {e}")
        return False, f"Ошибка экспорта: {e}"
