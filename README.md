<div align="center">
<img src="resources/icon.png" width="80" alt="Excel-XML for Mintrud"/>
</div>

# Excel-XML для передачи данных в Минтруд

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green)](https://wiki.qt.io/PySide6_Getting_Started)
[![License](https://img.shields.io/badge/License-MIT-yellow)](#лицензия)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)](https://www.microsoft.com/windows)
[![Build](https://img.shields.io/badge/Build-PyInstaller-purple)](#сборка)

**Автоматизация контроля и передачи данных об обученных работниках в Минтруд России**

\[[Возможности](#-возможности)\] \[[Установка](#-установка)\] \[[Документация](#-документация)\] \[[Разработка](#-разработка)\] \[[Скачать](#-скачать-portable)\]

---

## 📋 Описание

Десктопное приложение (PySide6) для учёта и контроля обучения сотрудников по охране труда (Постановление №2464). Обеспечивает полный цикл: внесение данных → формирование XML → отправка в реестр Минтруда → получение рег. номеров → формирование протоколов → сводный анализ статусов.

---

## 🚀 Возможности

### Внесение и просмотр данных
- Ручной ввод ФИО, СНИЛС (автоформатирование `XXX-XXX-XXX XX`), должности, программ обучения
- Импорт `.xlsx` (стриминг, до 10 МБ / 100 000 строк) / `.xml` (с XSD-валидацией)
- Редактирование и удаление записей через контекстное меню

### Экспорт и передача данных
- Конвертация в XML по XSD-схеме Минтруда
- Отправка на сервер `edu.rosmintrud.ru` (multipart/form-data)
- Отправка с электронной подписью (`.sig`) в РОЛ (архив `.olot`)
- Запрос рег. номеров по SetId или СНИЛС

### Журнал проверки знаний
- Автосохранение истории отправок, цветовая индикация статусов
- Фильтрация по ФИО/СНИЛС, SetId, статусу, протоколу, датам
- Автообновление рег. номеров по SetId

### Формирование протоколов
- Заполнение шаблона DOCX
- Состав комиссии, программы обучения, данные организации
- Быстрый протокол для одного работника с ручным вводом

### Сводка по сотрудникам
- Справочник, импорт XLSX, запрос из реестра Минтруда по СНИЛС
- Статус сотрудника (агрегированный по всем программам): Не обучен / Просрочено / Обучен
- План обучения, отчёт по обученным, «Текущая ситуация»
- Настройка периода обучения для программ типа В (№6-29): 1 или 3 года

### Производительность
- QAbstractTableModel (5000+ записей без лагов), пакетные SQL-запросы
- Фоновые QThread для импорта/API/планов, стриминг openpyxl read_only
- LRU-кэш ciphertext, кэши API-ответов с TTL

---

## 📥 Скачать (Portable)

Готовая сборка EXE без необходимости установки Python:

[⬇️ **Скачать ExcelXML-Mintrud.zip**](https://github.com/Kerlad/Excel_to_XML/blob/main/dist/ExcelXML-Mintrud-v3.0.0-win64.zip)

Portable-версия не требует установки Python и зависимостей.

## 📦 Установка (из исходников)

### Требования
- **Python** 3.12+
- **ОС** Windows 10/11

```bash
git clone https://github.com/Kerlad/Excel_to_XML.git
cd Excel_to_XML
pip install -r requirements.txt
python main.py
```

### Сборка EXE
```bash
py -m PyInstaller ExcelXML-Mintrud.spec
```

Готовый EXE: `dist/ExcelXML-Mintrud/ExcelXML-Mintrud.exe`

---

## 💻 Быстрый старт

| Шаг | Действие | Вкладка |
|:---:|----------|---------|
| 1 | Заполните данные УЦ и Заказчика (ИНН, название) | Внесение данных |
| 2 | Загрузите XLSX/XML или введите данные вручную | Внесение данных |
| 3 | Проверьте данные и нажмите «Конвертировать» | Просмотр данных |
| 4 | Выберите XML и отправьте на сервер (нужен API-ключ) | Передача данных |
| 5 | Получите SetId → запросите рег. номера | Передача данных |
| 6 | Сформируйте протокол проверки знаний (DOCX) | Журнал проверки знаний |
| 7 | Проверяйте статусы сотрудников через сводку | Справка о работниках |

---

## 📑 Документация

### Архитектура безопасности (ИСПДн)

Приложение является **ИСПДн (УЗ-3)**. Обработка ПДн осуществляется без согласия — на основании 152-ФЗ ст.6 ч.2.

**Ключевые меры защиты:**

| Уровень | Технология |
|---------|-----------|
| Шифрование в покое | Fernet (AES-128-CBC) — ФИО, СНИЛС в БД |
| Защита ключа | Windows DPAPI + entropy + passphrase (PBKDF2, 600K итераций) |
| XML-безопасность | defusedxml + LimitedXMLParser (XXE, XEE) |
| Сеть | TLS 1.2+ verify=True |
| Логи | SensitiveDataFilter (27+ паттернов) |
| Аудит | 34 события с HMAC-SHA256 integrity |
| Production mode | `EXCEL_XML_PROD=1` блокирует insecure fallback |
| Сессии | Auto-lock с passphrase |

[📘 Полная архитектура безопасности →](docs/SECURITY.md)
[🛡️ Hardening рабочего места →](docs/HARDENING.md)
[🔧 Руководство по эксплуатации →](docs/OPSEC_GUIDE.md)

### API Минтруда

`POST /api/set/push` — отправка XML, `POST /api/GetEducatedPersonXML` — запрос по SetId / СНИЛС.

[📘 API Минтруда →](docs/API_MINTTRUD.md)

### Отчёты аудита безопасности (v3.1.0)

| Документ | Описание |
|----------|----------|
| [compliance_audit.md](Reports/compliance_audit.md) | Юридико-технический аудит (152-ФЗ, ПП 1119) |
| [threat_model.md](Reports/threat_model.md) | STRIDE-модель угроз (48 пар угроза/защита) |
| [risk_register.md](Reports/risk_register.md) | Реестр рисков (24 риска) |
| [data_flow.md](Reports/data_flow.md) | Описание 11 потоков ПДн |
| [security_checklist.md](Reports/security_checklist.md) | Чеклисты deployment, IR, disposal |
| [dpia.md](Reports/dpia.md) | ОВЗД (Data Protection Impact Assessment) |
| [hardening_report.md](Reports/hardening_report.md) | 18 уязвимостей устранено (3 CRITICAL) |
| [SECURITY_AUDIT_REPORT.md](Reports/SECURITY_AUDIT_REPORT.md) | Полный аудит (v3.1.0) — 1 CRITICAL, 17 HIGH, 39 MEDIUM |
| [GAP_ANALYSIS.md](Reports/GAP_ANALYSIS.md) | Матрица расхождений по 48 требованиям |
| [COMPLIANCE.md](Reports/COMPLIANCE.md) | Соответствие 152-ФЗ, ПП 1119, ФСТЭК №21 |
| [FIX_TASKS.md](docs/FIX_TASKS.md) | ТЗ на устранение замечаний аудита |

### Политика обработки и развёртывание

| Документ | Описание |
|----------|----------|
| [PRIVACY.md](docs/PRIVACY.md) | Политика обработки ПДн (privacy-by-design) |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Руководство по развёртыванию (hardened) |

### Прочее
- [📄 Техническое задание](docs/Техническое_задание.md) — полное ТЗ с разделом 9 по ИБ
- [📋 AGENTS.md](AGENTS.md) — контекст проекта для AI-ассистента

---

## 📁 Структура проекта

```
Excel_to_XML/
├── main.py                    # Точка входа, главное окно
├── tabs/                      # Вкладки интерфейса (PySide6)
│   ├── data_entry_tab.py      ├── data_view_tab.py
│   ├── data_transfer_tab.py   ├── exam_journal_tab.py
│   ├── protocol_tab.py        ├── employee_summary_tab.py
│   └── single_worker_protocol_tab.py
├── api/                       # API клиент и транспорт
│   ├── mintrud_api.py         # Единая точка входа
│   ├── payload_builder.py     # Сборка запросов
│   ├── response_parser.py     # Парсинг ответов
│   └── backends/              # Requests / WinINET
├── db/                        # SQLite + репозитории
├── exporters/                 # XML / DOCX генерация
├── importers/                 # XLSX / XML импорт
├── protocol/                  # Комиссия / программы
├── journal/                   # Журнал отправок
├── network/                   # Диагностика сети
├── utils/                     # Крипто, логгинг, безопасность, UI
│   ├── crypto.py              ├── audit.py              ├── logger.py
│   ├── auto_lock.py           ├── xml_safe.py           ├── secure_temp.py
│   ├── error_utils.py         ├── proxy_manager.py      ├── app_paths.py
│   └── ... (dialog_base, about_dialog, help_dialog, passphrase_dialog и др.)
├── schema/                    # XSD-схемы
├── tests/                     # 389+ тестов
│   └── data/                  # Тестовые данные (XLSX, XML)
├── docs/                      # Документация
│   ├── SECURITY.md            # Архитектура безопасности
│   ├── HARDENING.md           # Hardening ОС
│   ├── OPSEC_GUIDE.md         # Эксплуатация, IR, ключи
│   ├── API_MINTTRUD.md        # API Минтруда
│   ├── PRIVACY.md             # Политика обработки ПДн
│   ├── DEPLOYMENT.md          # Развёртывание (hardened)
│   ├── FIX_TASKS.md           # ТЗ на устранение замечаний
│   ├── MOK.md                 # Mock-тесты (спецификация)
│   ├── ROL_API_Registry_Section.md  # API реестра РОЛ
│   └── archive/               # Архивные/черновики документов
├── Reports/                   # Отчёты аудита и compliance
│   ├── compliance_audit.md    ├── threat_model.md
│   ├── risk_register.md       ├── data_flow.md
│   ├── security_checklist.md  ├── dpia.md
│   ├── hardening_report.md    ├── SECURITY_AUDIT_REPORT.md
│   ├── GAP_ANALYSIS.md        └── COMPLIANCE.md
├── AGENTS.md                  # Инструкция для AI
├── CHANGELOG.md               # История версий
├── requirements.txt           # Зависимости
└── ExcelXML-Mintrud.spec      # PyInstaller
```

---

## 🛠 Разработка

### Запуск тестов
```bash
py -m pytest tests -v
```

### Сборка
```bash
py -m PyInstaller ExcelXML-Mintrud.spec
```

---

## ⚠️ Важно

- Приложение **НЕ** является сертифицированным СКЗИ (сертификация ФСТЭК/ФСБ не проводилась)
- Приложение **НЕ** использует ГОСТ-криптографию
- Безопасность данных зависит от защищённости ОС (BitLocker, антивирус, обновления)
- Организационные меры (политика ПДн, приказы, обучение) обязательны и **НЕ заменяются** техническими средствами приложения

Подробнее: [Security disclaimer →](docs/SECURITY.md#6-безопасное-развёртывание)

---

## 📄 Лицензия

MIT — подробнее в файле [LICENSE](LICENSE).

---

## 👥 Авторы

- **Кривоносов Д.А.** — разработка, архитектура, тестирование
- [denis.krv@yandex.ru](mailto:denis.krv@yandex.ru)
- Репозиторий: [github.com/Kerlad/Excel_to_XML](https://github.com/Kerlad/Excel_to_XML.git)

---

## ❤️ Поддержать проект

Excel-XML — полностью бесплатное приложение с открытым исходным кодом.

**Как помочь:**
- Откройте «Справка → О программе» или «Справка → Справка по работе с программой»
- Нажмите кнопку **«Поддержать разработчика ❤️»** или **«Поддержать проект ❤️»**
- Сканируйте QR-код через приложение любого банка (СБП)

Диалог показывается не чаще 1 раза в 45 дней. Вы можете отключить напоминания навсегда через чекбокс «Больше не показывать».
