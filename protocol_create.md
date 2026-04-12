<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# ЛОГИКА ФОРМИРОВАНИЯ ПРОТОКОЛА ПРОВЕРКИ ЗНАНИЙ

## (Маппинг Excel → XML согласно описанию пользователя)


***

## 1. СТРУКТУРА ВХОДНОГО EXCEL-ФАЙЛА

### Формат файла: `Protokol_proverki_znanii_OT.xlsx`

**Строка 1 (Заголовки колонок):**


| A | B | C | D | E | F | G | H | I |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Фамилия | Имя | Отчество | СНИЛС | Должность | Номер программы | Результат | Дата проверки | Номер протокола |

**Строки 2+ (Данные работников):**

Пример:

```
A2: Иванов
B2: Иван
C2: Иванович
D2: 123-456-789 00
E2: Слесарь-ремонтник
F2: 18
G2: Сдал
H2: 03.11.2025
I2: 45
```


***

## 2. МАППИНГ EXCEL → XML (ДЕТАЛЬНО)

### 2.1. Данные организации (НЕ из Excel, а из GUI)

**Источник:** Форма "Данные заказчика и обучающей организации" (вкладка "Конвертация" или "Протокол")

```
GUI поле → XML тег

ИНН Заказчика        → <customer><inn>1234567890</inn>
Наименование заказчика → <customer><name>ООО "Рога и Копыта"</name>
ИНН УЦ               → <uc><inn>9876543210</inn>
Наименование УЦ      → <uc><name>ЧОУ ДПО "Учебный центр"</name>
```


### 2.2. Состав комиссии (НЕ из Excel, а из GUI)

**Источник:** Форма "Состав комиссии" (вкладка "Протокол")

```
GUI поле → XML тег

Номер приказа        → <commission><order_number>45-к</order_number>
Дата приказа         → <commission><order_date>2025-11-01</order_date>
Председатель (ФИО)   → <commission><chairman><fio>Петров П.П.</fio>
Председатель (должн.) → <commission><chairman><position>Директор</position>
Члены комиссии       → <commission><members><member>...</member></members>
```


### 2.3. Программа обучения (ПРЕОБРАЗОВАНИЕ)

**Источник:** Excel колонка F (Номер программы) + Справочник `programs.py`

```python
# ШАГ 1: Прочитать из Excel
excel_value = "18"  # Колонка F

# ШАГ 2: Найти в справочнике
PROGRAMS = {
    "18": {
        "name": "Общие вопросы охраны труда и функционирования системы управления охраной труда",
        "hours": 40
    },
    "23": {
        "name": "Безопасные методы и приемы выполнения работ на высоте",
        "hours": 16
    }
}

program = PROGRAMS[excel_value]

# ШАГ 3: Записать в XML
xml_output = f"""
<program>
  <code>{excel_value}</code>
  <name>{program['name']}</name>
  <hours>{program['hours']}</hours>
</program>
"""
```


### 2.4. Данные работника (ПРЯМОЙ МАППИНГ)

**Excel → XML маппинг:**


| Excel колонка | Значение примера | XML тег | XML значение |
| :-- | :-- | :-- | :-- |
| **A** (Фамилия) | Иванов | `<worker><surname>` | Иванов |
| **B** (Имя) | Иван | `<worker><name>` | Иван |
| **C** (Отчество) | Иванович | `<worker><patronymic>` | Иванович |
| **D** (СНИЛС) | 123-456-789 00 | `<worker><snils>` | 123-456-789 00 |
| **E** (Должность) | Слесарь | `<worker><position>` | Слесарь |
| **F** (Программа) | 18 | `<worker><program_code>` | 18 |
| **G** (Результат) | Сдал | `<worker><result>` | Удовлетворительно* |
| **H** (Дата) | 03.11.2025 | `<worker><exam_date>` | 2025-11-03** |
| **I** (Протокол №) | 45 | `<protocol><number>` | 45 |

**Преобразования:**

- *Результат: "Сдал" → "Удовлетворительно", "Не сдал" → "Неудовлетворительно"
- **Дата: "03.11.2025" → "2025-11-03" (формат ISO 8601)

***

## 3. АЛГОРИТМ ОБРАБОТКИ (ПОШАГОВО)

```python
def process_excel_to_xml(excel_file, customer_data, uc_data, commission_data):
    """
    Обработка Excel → XML
    
    Args:
        excel_file: Путь к Excel файлу
        customer_data: dict с ИНН и названием заказчика
        uc_data: dict с ИНН и названием УЦ
        commission_data: dict с данными комиссии
    """
    
    # ===== ШАГ 1: ПРОЧИТАТЬ EXCEL =====
    df = pd.read_excel(excel_file)
    
    # Проверка обязательных колонок
    required_cols = ['Фамилия', 'Имя', 'СНИЛС', 'Должность', 
                     'Номер программы', 'Результат', 'Дата проверки', 'Номер протокола']
    
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Отсутствуют обязательные колонки")
    
    # ===== ШАГ 2: ВАЛИДАЦИЯ ДАННЫХ =====
    for idx, row in df.iterrows():
        # Проверка СНИЛС (формат XXX-XXX-XXX XX)
        snils = str(row['СНИЛС'])
        if not re.match(r'^\d{3}-\d{3}-\d{3} \d{2}$', snils):
            raise ValueError(f"Неверный формат СНИЛС в строке {idx+2}: {snils}")
        
        # Проверка номера программы
        program_code = str(row['Номер программы'])
        if program_code not in PROGRAMS:
            raise ValueError(f"Программа {program_code} не найдена в справочнике")
        
        # Проверка результата
        result = str(row['Результат'])
        if result not in ['Сдал', 'Не сдал']:
            raise ValueError(f"Неверный результат в строке {idx+2}: {result}")
    
    # ===== ШАГ 3: ПОЛУЧИТЬ НОМЕР ПРОТОКОЛА =====
    # Берём из первой строки (все строки должны иметь одинаковый номер протокола)
    protocol_number = str(df.iloc[0]['Номер протокола'])
    
    # ===== ШАГ 4: ПОЛУЧИТЬ ПРОГРАММУ =====
    # Берём из первой строки (предполагается одна программа на протокол)
    program_code = str(df.iloc[0]['Номер программы'])
    program_data = PROGRAMS[program_code]
    
    # ===== ШАГ 5: ПОСТРОИТЬ XML =====
    xml = ET.Element('protocol')
    
    # 5.1. Шапка протокола
    header = ET.SubElement(xml, 'header')
    ET.SubElement(header, 'number').text = protocol_number
    ET.SubElement(header, 'date').text = datetime.now().strftime('%Y-%m-%d')
    
    # 5.2. Данные организаций
    customer = ET.SubElement(xml, 'customer')
    ET.SubElement(customer, 'inn').text = customer_data['inn']
    ET.SubElement(customer, 'name').text = customer_data['name']
    
    uc = ET.SubElement(xml, 'uc')
    ET.SubElement(uc, 'inn').text = uc_data['inn']
    ET.SubElement(uc, 'name').text = uc_data['name']
    
    # 5.3. Комиссия
    commission = ET.SubElement(xml, 'commission')
    ET.SubElement(commission, 'order_number').text = commission_data['order_number']
    ET.SubElement(commission, 'order_date').text = commission_data['order_date']
    
    chairman = ET.SubElement(commission, 'chairman')
    ET.SubElement(chairman, 'fio').text = commission_data['chairman_fio']
    ET.SubElement(chairman, 'position').text = commission_data['chairman_position']
    
    members = ET.SubElement(commission, 'members')
    for member in commission_data['members']:
        m = ET.SubElement(members, 'member')
        ET.SubElement(m, 'fio').text = member['fio']
        ET.SubElement(m, 'position').text = member['position']
    
    # 5.4. Программа обучения
    program = ET.SubElement(xml, 'program')
    ET.SubElement(program, 'code').text = program_code
    ET.SubElement(program, 'name').text = program_data['name']
    ET.SubElement(program, 'hours').text = str(program_data['hours'])
    
    # 5.5. Работники
    workers = ET.SubElement(xml, 'workers')
    
    for idx, row in df.iterrows():
        worker = ET.SubElement(workers, 'worker')
        ET.SubElement(worker, 'number').text = str(idx + 1)  # Порядковый номер
        ET.SubElement(worker, 'surname').text = str(row['Фамилия'])
        ET.SubElement(worker, 'name').text = str(row['Имя'])
        ET.SubElement(worker, 'patronymic').text = str(row['Отчество']) if pd.notna(row['Отчество']) else ''
        ET.SubElement(worker, 'snils').text = str(row['СНИЛС'])
        ET.SubElement(worker, 'position').text = str(row['Должность'])
        
        # Преобразование результата
        result_raw = str(row['Результат'])
        result_xml = 'Удовлетворительно' if result_raw == 'Сдал' else 'Неудовлетворительно'
        ET.SubElement(worker, 'result').text = result_xml
        
        # Преобразование даты (ДД.ММ.ГГГГ → ГГГГ-ММ-ДД)
        date_raw = str(row['Дата проверки'])
        date_parts = date_raw.split('.')
        date_xml = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
        ET.SubElement(worker, 'exam_date').text = date_xml
        
        # Регистрационный номер (генерируется автоматически)
        registry_number = f"{datetime.now().year}-{idx+1:06d}"
        ET.SubElement(worker, 'registry_number').text = registry_number
    
    # ===== ШАГ 6: СОХРАНИТЬ XML =====
    tree = ET.ElementTree(xml)
    ET.indent(tree, space='  ')
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    
    return xml
```


***

## 4. ПРИМЕР ПОЛНОГО ПРЕОБРАЗОВАНИЯ

**Входной Excel:**


| A | B | C | D | E | F | G | H | I |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Фамилия | Имя | Отчество | СНИЛС | Должность | Номер программы | Результат | Дата проверки | Номер протокола |
| Иванов | Иван | Иванович | 123-456-789 00 | Слесарь | 18 | Сдал | 03.11.2025 | 45 |
| Петров | Петр |  | 987-654-321 11 | Токарь | 18 | Не сдал | 03.11.2025 | 45 |

**Выходной XML:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<protocol>
  <header>
    <number>45</number>
    <date>2025-11-06</date>
  </header>
  
  <customer>
    <inn>1234567890</inn>
    <name>ООО "Рога и Копыта"</name>
  </customer>
  
  <uc>
    <inn>9876543210</inn>
    <name>ЧОУ ДПО "Учебный центр "Безопасность"</name>
  </uc>
  
  <commission>
    <order_number>45-к</order_number>
    <order_date>2025-11-01</order_date>
    <chairman>
      <fio>Сидоров Сидор Сидорович</fio>
      <position>Директор</position>
    </chairman>
    <members>
      <member>
        <fio>Васильев Василий Васильевич</fio>
        <position>Инженер по ОТ</position>
      </member>
    </members>
  </commission>
  
  <program>
    <code>18</code>
    <name>Общие вопросы охраны труда и функционирования системы управления охраной труда</name>
    <hours>40</hours>
  </program>
  
  <workers>
    <worker>
      <number>1</number>
      <surname>Иванов</surname>
      <name>Иван</name>
      <patronymic>Иванович</patronymic>
      <snils>123-456-789 00</snils>
      <position>Слесарь</position>
      <result>Удовлетворительно</result>
      <exam_date>2025-11-03</exam_date>
      <registry_number>2025-000001</registry_number>
    </worker>
    
    <worker>
      <number>2</number>
      <surname>Петров</surname>
      <name>Петр</name>
      <patronymic></patronymic>
      <snils>987-654-321 11</snils>
      <position>Токарь</position>
      <result>Неудовлетворительно</result>
      <exam_date>2025-11-03</exam_date>
      <registry_number>2025-000002</registry_number>
    </worker>
  </workers>
</protocol>
```


***

**Это полное описание маппинга Excel → XML согласно логике программы.**

