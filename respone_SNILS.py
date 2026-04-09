# Поиск по СНИЛС

import requests
import urllib3
import xml.dom.minidom
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_all_records_strict():
    url = "https://edu.rosmintrud.ru/api/GetEducatedPersonXML"
    api_key = "fffff"
    target_snils = "111-111-111 00" 
    
    # Важно: СНИЛС должен быть в том формате, который есть в базе. 
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    all_records_xml = [] 
    page_number = 1
    page_size = 100  # Для стабильности начнем с 100, если заработает — можно увеличить
    
    print(f"Запуск выгрузки. СНИЛС: {target_snils}")

    while True:
        print(f"Запрос страницы {page_number}...")
        
        # --- ВАЖНО: СТРОГИЙ ПОРЯДОК ТЕГОВ ---
        # 1. ApiKey
        # 2. PageNo
        # 3. PageSize
        # 4. Snils (и другие поля фильтрации идут ПОСЛЕ пагинации)
        
        xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{api_key}</ApiKey>
    <PageNo>{page_number}</PageNo>
    <PageSize>{page_size}</PageSize>
    <Snils>{target_snils}</Snils>
</EducatedPersonFilter>
"""
        files = {'file': ('request.xml', xml_content, 'text/xml')}

        try:
            response = requests.post(url, files=files, headers=headers, verify=False)
            response.encoding = 'utf-8'

            if response.status_code == 500:
                print("Ошибка 500. Возможные причины:")
                print("1. Нарушен порядок тегов (исправлено в этом скрипте).")
                print("2. Неверный формат СНИЛС (попробуйте убрать дефисы).")
                print("3. Сервер перегружен (попробуйте позже).")
                break
            
            if response.status_code != 200:
                print(f"Ошибка сервера: {response.status_code}")
                print(response.text[:500])
                break

            # Успешный ответ
            response_text = response.text
            
            # Проверка на тег <Error> внутри XML (бывает и при статусе 200)
            if "<Error>" in response_text:
                print("Сервер вернул логическую ошибку:")
                print(response_text)
                break

            # Проверка на наличие записей
            if "<RegistryRecord" not in response_text:
                print(f"Страница {page_number} пустая, выгрузка завершена.")
                break

            # Извлекаем контент
            start_tag = "<EducatedPersons>"
            end_tag = "</EducatedPersons>"
            start_idx = response_text.find(start_tag)
            end_idx = response_text.find(end_tag)
            
            if start_idx != -1 and end_idx != -1:
                content = response_text[start_idx + len(start_tag) : end_idx]
                if not content.strip():
                    print("Пустой контент.")
                    break
                
                all_records_xml.append(content)
                print(f"Страница {page_number} успешно загружена.")
                page_number += 1
                time.sleep(0.5) # Пауза
            else:
                print("Не удалось найти тег <EducatedPersons>.")
                print(response_text[:300])
                break

        except Exception as e:
            print(f"Критическая ошибка: {e}")
            break

    # Сохранение
    if all_records_xml:
        final_xml = f'<?xml version="1.0" encoding="utf-8"?>\n<EducatedPersons>\n{"".join(all_records_xml)}\n</EducatedPersons>'
        try:
            dom = xml.dom.minidom.parseString(final_xml)
            pretty_xml = dom.toprettyxml(indent="  ")
            with open("all_records_strict.xml", "w", encoding="utf-8") as f:
                f.write(pretty_xml)
            print(f"Готово! Сохранено в 'all_records_strict.xml'. Записей (примерно): {final_xml.count('<RegistryRecord ')}")
        except:
            with open("all_records_raw.xml", "w", encoding="utf-8") as f:
                f.write(final_xml)
    else:
        print("Результатов нет.")

if __name__ == "__main__":
    get_all_records_strict()
