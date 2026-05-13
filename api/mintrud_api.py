"""
Модуль работы с API Минтруда
Отправка наборов записей и получение регистрационных номеров
"""
# ============================================================================
# TLS VERIFICATION SETTINGS
# ============================================================================
# Импортируем из proxy_manager - значение переопределяется чекбоксом в интерфейсе
from utils.proxy_manager import ENABLE_TLS_VERIFY
# ============================================================================

import os
import io
import time
import base64
import json
import zipfile
import logging
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
import urllib3

# Suppress InsecureRequestWarning only when TLS verification is disabled
if not ENABLE_TLS_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

error_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
os.makedirs(error_log_path, exist_ok=True)
error_log_file = os.path.join(error_log_path, "error_response.txt")

API_URL = "https://edu.rosmintrud.ru/api/set/push"
GET_URL = "https://edu.rosmintrud.ru/api/GetEducatedPersonXML"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Импортируем функцию прокси из utils.proxy_manager
from utils.proxy_manager import (
    build_proxies_for_requests,
    build_proxy_headers,
    create_proxy_session,
    diagnose_407_error,
    try_fallback_connection,
    NTLM_AVAILABLE,
    KERBEROS_AVAILABLE
)

# Импортируем network модуль для Windows Integrated Authentication
from network.client import (
    create_negotiate_session,
    get_network_diagnostics,
    test_external_access,
    NetworkStatus,
    get_windows_proxy
)


# ============ Сохранение API-ключа ============

try:
    from cryptography.fernet import Fernet
except ImportError:
    raise ImportError(
        "Библиотека 'cryptography' не установлена. "
        "Установите её: pip install cryptography"
    )


def _get_derive_key():
    """Получение ключа шифрования на основе имени пользователя системы."""
    username = os.environ.get('USERNAME', 'default_user').encode('utf-8')
    return hashlib.sha256(username).digest()


def _fernet():
    """Создание объекта Fernet с ключом из имени пользователя."""
    key = _get_derive_key()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def save_api_key(api_key, data_dir):
    """Сохранение API-ключа в зашифрованном виде (AES/Fernet)."""
    try:
        encrypted = _fernet().encrypt(api_key.encode('utf-8'))

        key_file = os.path.join(data_dir, "api_key.json")
        with open(key_file, 'w', encoding='utf-8') as f:
            json.dump({
                "key": encrypted.decode('utf-8'),
                "created": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        return True, "Ключ сохранён"
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
        return _fernet().decrypt(encrypted.encode('utf-8')).decode('utf-8')
    except Exception:
        return None


def validate_api_key(api_key):
    """Проверка корректности API-ключа (32 символа)."""
    if not api_key:
        return False, "API ключ не введён"
    if len(api_key) != 32:
        return False, f"Длина ключа: {len(api_key)} (требуется 32 символа)"
    return True, ""


# ============ Отправка XML на сервер ============

def push_xml(api_key, xml_file_path, xsd_path=None, proxy_settings=None):
    """
    Отправка XML файла на сервер Минтруда.

    Алгоритм (BR-2):
    1. Создаётся Request.xml с ApiKey и NeedSend=false
    2. Файл данных упаковывается в .olot архив
    3. Отправляются два файла: Request.xml и .olot через multipart/form-data

    proxy_settings — dict с полями: enabled, url, username, password

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

    proxies = build_proxies_for_requests(proxy_settings)
    proxy_headers = build_proxy_headers(proxy_settings)

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
        # Используем create_proxy_session для корректной proxy-аутентификации
        logger.info(f"Отправка XML на {API_URL}")
        if proxies:
            logger.info(f"Используется прокси: {proxies.get('https', 'N/A')}")

        # Создаем сессию через create_proxy_session для корректной работы с прокси
        session, auth_method = create_proxy_session(proxy_settings, prefer_auth="auto")
        if not session:
            error_msg = "Не удалось создать сессию с прокси"
            if proxy_settings and proxy_settings.get("mode") != "off":
                error_msg += f"\n\nПопробуйте: pip install requests-ntlm requests-negotiate-sspi"
            return {"success": False, "error": error_msg}

        logger.info(f"Используется метод авторизации прокси: {auth_method}")

        try:
            response = session.post(
                API_URL,
                files={
                    'xml': ('Request.xml', request_xml.encode('utf-8'), 'text/xml'),
                    'olot': ('data.olot', olot_data, 'application/octet-stream'),
                },
                headers=HEADERS,
                # TLS verification - set to True for production, False for dev/testing with self-signed certs
                # WARNING: Disabling verification exposes you to MITM attacks!
                # To quickly disable: set verify=False
                verify=ENABLE_TLS_VERIFY,
                timeout=60
            )
        finally:
            session.close()

        response_text = response.text
        # Если response.text содержит кракозябры — декодируем вручную
        try:
            response_bytes = response.content
            response_text = response_bytes.decode('utf-8')
        except Exception:
            pass

        logger.info(f"Ответ сервера: HTTP {response.status_code}")
        logger.info(f"Полный ответ: {response_text}")
        logger.info(f"Response headers: {dict(response.headers)}")

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

            logger.info(f"Успех: SetId={set_id}, SendEducatedPerson={send_edu}")

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
            logger.error(f"Ошибка: {status_code} - {msg}")
            _save_error_log(response_text)

            return {"success": False, "error": error_msg, "raw_response": response_text[:1000]}

        else:
            _save_error_log(response_text)
            return {"success": False, "error": f"Неизвестный формат ответа: {root.tag}", "raw_response": response_text[:500]}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Таймаут соединения. Повторите попытку."}
    except requests.exceptions.ConnectionError as e:
        # Пробуем fallback при ошибке подключения
        logger.warning(f"Ошибка подключения, пробуем fallback: {e}")
        session, method = try_fallback_connection(proxy_settings, str(e))
        if session:
            logger.info(f"Fallback успешен: {method}")
            try:
                response = session.post(
                    API_URL,
                    files={
                        'xml': ('Request.xml', request_xml.encode('utf-8'), 'text/xml'),
                        'olot': ('data.olot', olot_data, 'application/octet-stream'),
                    },
                    headers=HEADERS,
                    verify=ENABLE_TLS_VERIFY,
                    timeout=60
                )

                response_text = response.text
                try:
                    response_bytes = response.content
                    response_text = response_bytes.decode('utf-8')
                except Exception:
                    pass

                logger.info(f"Fallback ответ сервера: HTTP {response.status_code}")

                # Парсим ответ после fallback
                try:
                    root = ET.fromstring(response_text)
                except ET.ParseError:
                    if response.status_code == 200:
                        return {"success": True, "set_id": "unknown", "message": response_text[:200]}
                    _save_error_log(response_text)
                    return {"success": False, "error": f"Fallback HTTP {response.status_code}: Не удалось разобрать ответ", "raw_response": response_text[:1000]}

                if root.tag == "Response":
                    set_id_elem = root.find("SetId")
                    send_elem = root.find("SendEducatedPerson")
                    msg_elem = root.find("Message")
                    set_id = set_id_elem.text if set_id_elem is not None else ""
                    send_edu = send_elem.text if send_elem is not None else "false"
                    msg = msg_elem.text if msg_elem is not None else ""
                    return {"success": True, "set_id": set_id, "send_educated_person": send_edu.lower() == "true", "message": msg}
                elif root.tag == "Error":
                    status_code_elem = root.find("StatusCode")
                    msg_elem = root.find("Message")
                    status_code = status_code_elem.text if status_code_elem is not None else "unknown"
                    msg = msg_elem.text if msg_elem is not None else ""
                    error_msg = _format_error(status_code, msg)
                    return {"success": False, "error": error_msg, "raw_response": response_text[:1000]}
                else:
                    return {"success": False, "error": f"Неизвестный формат ответа: {root.tag}", "raw_response": response_text[:500]}

            except Exception as fallback_error:
                logger.error(f"Fallback не удался: {fallback_error}")
                return {"success": False, "error": f"Ошибка подключения: {e}\n\nПопробуйте установить: pip install requests-ntlm requests-negotiate-sspi"}
        else:
            return {"success": False, "error": "Нет соединения с сервером Минтруда\n\nПопробуйте: pip install requests-ntlm requests-negotiate-sspi"}
    except Exception as e:
        logger.error(f"Критическая ошибка отправки: {e}")
        return {"success": False, "error": f"Ошибка: {e}"}


def _save_error_log(text):
    """Сохранение полного ответа сервера в файл лога."""
    try:
        with open(error_log_file, 'w', encoding='utf-8-sig') as f:
            f.write(text)
    except Exception as e:
        logger.error(f"Ошибка записи лога: {e}")


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

def get_by_set_id(api_key, set_id, page_size=5000, proxy_settings=None):
    """
    Запрос регистрационных номеров по SetId.

    POST на GET_URL с фильтром SetId.
    Поддерживает пагинацию — собирает все страницы.

    proxy_settings — dict с полями: enabled, url, username, password

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

        result = _fetch_page(xml_content, f"стр. {page_no}", page_size, proxy_settings)
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

def get_by_snils(api_key, snils, page_size=100, proxy_settings=None):
    """
    Запрос регистрационных номеров по СНИЛС.

    POST на GET_URL с фильтром Snils.
    Поддерживает пагинацию.

    proxy_settings — dict с полями: enabled, url, username, password

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

        result = _fetch_page(xml_content, f"стр. {page_no}", page_size, proxy_settings)
        if result is None:
            break

        records = result.get("records", [])
        all_records.extend(records)

        if not result.get("has_more", False):
            break

        page_no += 1
        time.sleep(0.5)

    return {"success": True, "records": all_records}


def _fetch_page(xml_content, page_label="", page_size=100, proxy_settings=None):
    """
    Выполнение одного POST-запроса к GetEducatedPersonXML.
    Возвращает {"records": [...], "has_more": bool} или None при ошибке.
    """
    files = {'file': ('request.xml', xml_content, 'text/xml')}
    proxies = build_proxies_for_requests(proxy_settings)
    proxy_headers = build_proxy_headers(proxy_settings)

    try:
        if proxies:
            logger.info(f"Запрос {page_label} через прокси: {proxies.get('https', 'N/A')}")

        # Используем create_proxy_session для корректной proxy-аутентификации
        session, auth_method = create_proxy_session(proxy_settings, prefer_auth="auto")
        if not session:
            logger.error(f"Не удалось создать сессию с прокси для {page_label}")
            return None

        logger.info(f"Метод авторизации для {page_label}: {auth_method}")

        try:
            response = session.post(
                GET_URL,
                files=files,
                headers=HEADERS,
                verify=ENABLE_TLS_VERIFY,
                timeout=60
            )
        finally:
            session.close()
        
        response.encoding = 'utf-8'
        response_text = response.text

        if response.status_code == 500:
            logger.error(f"Ошибка 500 при запросе {page_label}: {response_text[:300]}")
            return None

        if response.status_code != 200:
            logger.error(f"Ошибка HTTP {response.status_code} при запросе {page_label}")
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
                    logger.error(f"Логическая ошибка: {sc_text} - {msg_text}")
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
        logger.error(f"Критическая ошибка запроса {page_label}: {e}")
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
        logger.error(f"Ошибка парсинга записей: {e}")

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

        def _format_date(date_val):
            """Конвертация даты из YYYY-MM-DD или YYYY-MM-DDTHH:MM:SS в ДД.ММ.ГГГГ."""
            if not date_val:
                return ''
            try:
                from datetime import datetime
                if 'T' in date_val:
                    dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
                return dt.strftime("%d.%m.%Y")
            except (ValueError, TypeError):
                return date_val

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
                _format_date(rec.get('Date', ''))
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
        logger.error(f"Ошибка экспорта XLSX: {e}")
        return False, f"Ошибка экспорта: {e}"


# ============ Запрос данных по OrgId (НСПР) ============

def get_by_org_id(api_key, org_id, page_size=5000, proxy_settings=None, limit=0):
    """
    Запрос всех обученных лиц по ID организации (для НСПР - реестр обученных лиц).
    
    POST на GET_URL с фильтром OrgId.
    Поддерживает пагинацию — собирает все страницы.
    
    proxy_settings — dict с полями: mode, url, username, password
    
    limit — ограничение количества записей (0 = без ограничения)
    
    Возвращает:
        {"success": bool, "records": list, "error": str}
    """
    ok, err = validate_api_key(api_key)
    if not ok:
        return {"success": False, "error": err}

    if not org_id:
        return {"success": False, "error": "OrgId не введён"}

    all_records = []
    page_no = 1

    while True:
        # Проверка лимита
        if limit > 0 and len(all_records) >= limit:
            break
        
        # Вычисляем размер страницы с учётом лимита
        current_page_size = page_size
        if limit > 0 and len(all_records) + current_page_size > limit:
            current_page_size = limit - len(all_records)
        
        # Строгий порядок тегов: ApiKey, PageNo, PageSize, OrgId
        xml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{api_key}</ApiKey>
    <PageNo>{page_no}</PageNo>
    <PageSize>{current_page_size}</PageSize>
    <OrgId>{org_id}</OrgId>
</EducatedPersonFilter>'''

        result = _fetch_page(xml_content, f"стр. {page_no}", current_page_size, proxy_settings)
        if result is None:
            break

        records = result.get("records", [])
        all_records.extend(records)

        if not result.get("has_more", False):
            break

        page_no += 1
        time.sleep(0.5)

    return {"success": True, "records": all_records}
