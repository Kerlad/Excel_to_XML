--- utils/mintrud_api.py (原始)


+++ utils/mintrud_api.py (修改后)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API для взаимодействия с сервером Минтруда
"""

import requests
import urllib3
import zipfile
import io
import os
from typing import Tuple

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MinTrudAPI:
    """Класс для работы с API Минтруда"""

    SEND_URL = "https://edu.rosmintrud.ru/api/set/push"
    REQUEST_URL = "https://edu.rosmintrud.ru/api/GetEducatedPersonXML"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def send_xml(self, xml_filepath: str) -> Tuple[bool, str]:
        """
        Отправка XML файла на сервер Минтруда
        Возвращает кортеж (успех, результат/SetId или ошибка)
        """
        try:
            # Создаем архив .olot с XML файлом
            olot_buffer = io.BytesIO()
            with zipfile.ZipFile(olot_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(xml_filepath, os.path.basename(xml_filepath))
            olot_buffer.seek(0)

            # Создаем Request XML
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<Request>
    <ApiKey>{self.api_key}</ApiKey>
    <NeedSend>false</NeedSend>
</Request>"""

            # Подготовка файлов для отправки
            files = [
                ('file', ('request.xml', request_xml, 'text/xml')),
                ('file', ('data.olot', olot_buffer.read(), 'application/zip'))
            ]

            response = requests.post(
                self.SEND_URL,
                files=files,
                headers=self.headers,
                verify=False,
                timeout=60
            )

            if response.status_code != 200:
                return False, f"Ошибка HTTP {response.status_code}: {response.text[:200]}"

            # Парсим ответ
            response_text = response.text

            if "<Error>" in response_text:
                # Извлекаем сообщение об ошибке
                error_start = response_text.find("<Error>") + len("<Error>")
                error_end = response_text.find("</Error>")
                error_msg = response_text[error_start:error_end] if error_end > error_start else "Неизвестная ошибка"
                return False, f"Ошибка сервера: {error_msg}"

            # Извлекаем SetId
            setid_start = response_text.find("<SetId>")
            if setid_start == -1:
                return False, "Не удалось получить SetId из ответа"

            setid_end = response_text.find("</SetId>")
            setid = response_text[setid_start + len("<SetId>"):setid_end].strip()

            # Проверяем SendEducatedPerson
            send_success = "true" in response_text.lower() or "True" in response_text

            return True, setid

        except requests.RequestException as e:
            return False, f"Ошибка сети: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

    def request_by_setid(self, setid: str, output_xlsx_path: str) -> Tuple[bool, str]:
        """
        Запрос данных по SetId и сохранение в Excel
        Возвращает кортеж (успех, сообщение)
        """
        try:
            # Создаем XML запрос
            request_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{self.api_key}</ApiKey>
    <SetId>{setid}</SetId>
</EducatedPersonFilter>"""

            files = {'file': ('request.xml', request_xml, 'text/xml')}

            response = requests.post(
                self.REQUEST_URL,
                files=files,
                headers=self.headers,
                verify=False,
                timeout=60
            )

            if response.status_code != 200:
                return False, f"Ошибка HTTP {response.status_code}: {response.text[:200]}"

            response_text = response.text

            if "<Error>" in response_text:
                error_start = response_text.find("<Error>") + len("<Error>")
                error_end = response_text.find("</Error>")
                error_msg = response_text[error_start:error_end] if error_end > error_start else "Неизвестная ошибка"
                return False, f"Ошибка сервера: {error_msg}"

            # Парсим XML ответ и конвертируем в Excel
            from utils.response_parser import ResponseParser
            parser = ResponseParser()
            success, message = parser.parse_to_excel(response_text, output_xlsx_path)

            return success, message

        except requests.RequestException as e:
            return False, f"Ошибка сети: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"