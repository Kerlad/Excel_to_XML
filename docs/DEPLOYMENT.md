# Руководство по развёртыванию ИСПДн

**Проект:** Норма ОТ: Реестр обучения
**Версия:** 3.1.0
**Дата:** 22.05.2026

---

## 1. Требования к рабочему месту

### 1.1. Минимальные требования

| Компонент | Требование |
|-----------|------------|
| ОС | Windows 10/11 Professional (для BitLocker) |
| CPU | x64, 2+ ядра |
| RAM | 4 GB+ |
| Диск | 500 MB свободного места |
| Экран | 1280×720+ |
| Интернет | Доступ к edu.rosmintrud.ru (TCP/443) |

### 1.2. Программное обеспечение

| Компонент | Требование | Примечание |
|-----------|------------|------------|
| ОС | Windows 10/11 | Home edition без BitLocker |
| BitLocker | Включён | Защита ПДн на диске |
| Антивирус | Microsoft Defender / Kaspersky | Real-time protection |
| Браузер | Не требуется | Для администрирования API-ключа |
| Office | Опционально | Для просмотра XLSX-экспортов |

### 1.3. Сетевые требования

| Направление | Протокол | Порт | Назначение |
|-------------|----------|------|------------|
| edu.rosmintrud.ru | HTTPS | 443 | API Минтруда |
| DNS | UDP/TCP | 53 | Разрешение имён |
| NTP | UDP | 123 | Синхронизация времени |

---

## 2. Установка

### 2.1. Из EXE (Portable)

```powershell
# 1. Скачать архив
# 2. Распаковать в C:\Program Files\NormaOT_Reestr\
# 3. Запустить NormaOT_Reestr.exe
```

### 2.2. Из исходников

```powershell
# 1. Клонировать репозиторий
git clone https://github.com/Kerlad/Excel_to_XML.git
cd Excel_to_XML

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Установить EXCEL_XML_PROD (обязательно для production)
[Environment]::SetEnvironmentVariable("EXCEL_XML_PROD", "1", "Machine")

# 4. Запустить
python main.py
```

### 2.3. Сборка EXE

```powershell
# Удалить предыдущую сборку
Remove-Item -Recurse -Force dist\NormaOT_Reestr

# Собрать
py -m PyInstaller NormaOT_Reestr.spec

# Результат: dist\NormaOT_Reestr\NormaOT_Reestr.exe
```

---

## 3. Конфигурация безопасности

### 3.1. Переменные окружения

```powershell
# Production mode (блокирует plaintext master key)
[Environment]::SetEnvironmentVariable("EXCEL_XML_PROD", "1", "Machine")

# Проверить
[Environment]::GetEnvironmentVariable("EXCEL_XML_PROD", "Machine")
```

### 3.2. Production mode обеспечивает

- Запрет создания/использования plaintext мастер-ключа
- Блокировка insecure fallback при шифровании
- Установка минимального уровня логирования INFO (не DEBUG)
- Принудительная проверка безопасности ключа при запуске

### 3.3. Настройка приложения

1. **Запустить приложение** — будет создан мастер-ключ (DPAPI)
2. **Установить passphrase** — Настройки → Установить пароль
3. **Ввести API-ключ** — вкладка "Передача данных"
4. **Настроить авто-блокировку** — Настройки → Настроить блокировку
5. **Настроить прокси** (если требуется) — Настройки → Прокси

---

## 4. Файловая система

### 4.1. Структура данных

```
%APPDATA%/Excel_to_XML/
├── data/
│   └── app_data.db          # SQLite БД (зашифрованные ПДн)
├── backups/
│   ├── app_data.db.backup.1 # Резервные копии БД
│   ├── app_data.db.backup.2
│   └── ...
├── log/
│   ├── app.log              # Основной лог
│   ├── error.log            # Ошибки
│   ├── audit.log            # Аудит-лог (HMAC integrity)
│   └── audit.log.1          # Ротация
├── corrupted_keys/          # Повреждённые ключи (forensic copy)
├── master.key               # Мастер-ключ (DPAPI)
├── master.key.json          # Метаданные ключа (HMAC)
├── passphrase_wrapped.key   # Passphrase-обёртка (опционально)
├── api_key.json             # API-ключ (Fernet)
├── proxy_settings.json      # Настройки прокси (Fernet)
└── org_settings.json        # Настройки организации (Fernet)
```

### 4.2. Права доступа

| Файл/Директория | Права (Windows ACL) | Примечание |
|-----------------|---------------------|------------|
| %APPDATA%/Excel_to_XML/ | Только текущий пользователь | Creator Owner |
| master.key | Только текущий пользователь | DPAPI-зашифрован |
| app_data.db | Только текущий пользователь | Полевое шифрование |
| log/ | Только текущий пользователь | Может содержать ПДн |

---

## 5. Резервное копирование

### 5.1. Автоматическое (БД)

```python
# Выполняется при каждом запуске
# Хранится: %APPDATA%/Excel_to_XML/backups/
# Ротация: до 5 копий (удаление старых)
# Шифрование: полевое (данные уже зашифрованы)
```

### 5.2. Ручное (ключи)

```powershell
# Через UI: Меню → Backup → Создать backup ключей
# ZIP-архив с PBKDF2-паролем
# Содержит: master.key, master.key.json, passphrase_wrapped.key
```

### 5.3. Политика резервного копирования

| Объект | Периодичность | Хранение | Шифрование |
|--------|---------------|----------|------------|
| БД (авто) | При запуске | 5 копий | Полевое |
| Ключи (ручное) | Еженедельно | Внешний носитель | PKWARE ZipCrypto |
| Полная копия | Ежемесячно | Отдельный ПК | BitLocker |

---

## 6. Проверки после деплоя

```powershell
# 1. Проверка production mode
$env:EXCEL_XML_PROD -eq "1"

# 2. Проверка BitLocker
Get-BitLockerVolume -MountPoint "C:" | fl ProtectionStatus

# 3. Проверка антивируса
Get-MpComputerStatus | fl RealTimeProtectionEnabled

# 4. Проверка обновлений
Get-WindowsUpdate

# 5. Сетевой доступ
Test-NetConnection edu.rosmintrud.ru -Port 443
```

### UI проверки

- [ ] Приложение запускается без предупреждений
- [ ] Passphrase установлен и работает
- [ ] Тест API-ключа проходит успешно
- [ ] Логи не содержат ПДн в открытом виде (grep в app.log + error.log)
- [ ] Авто-блокировка активируется по таймауту
- [ ] Резервное копирование создаётся успешно
- [ ] TLS verify=True (отсутствует TLS_WARNING в audit.log)

---

## 7. Обновление

### 7.1. Из EXE

```powershell
# 1. Создать backup (Меню → Backup)
# 2. Скачать новую версию
# 3. Распаковать поверх старой
# 4. Запустить новую версию
# 5. Проверить: данные читаются, API работает
```

### 7.2. Из исходников

```powershell
# 1. Создать backup
git pull origin main
pip install -r requirements.txt --upgrade
# 2. Запустить
```

### 7.3. Проверка обновлений

В настоящее время **нет встроенного механизма обновлений**. Обновления выполняются вручную.

---

## 8. Устранение неполадок

### 8.1. Приложение не запускается

```powershell
# Проверить логи
Get-Content "$env:APPDATA/Excel_to_XML/log/error.log"

# Проверить версию Python
python --version  # Должно быть 3.12+

# Проверить зависимости
pip list | Select-String "cryptography|PySide6|openpyxl|lxml"
```

### 8.2. API не работает

```powershell
# Проверить сеть
Test-NetConnection edu.rosmintrud.ru -Port 443

# Проверить TLS
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Проверить прокси (если используется)
[System.Net.WebRequest]::GetSystemWebProxy()
```

### 8.3. Потерян passphrase

Восстановление невозможно без backup ключей.
Если backup существует: Меню → Восстановить ключи из backup.

### 8.4. Повреждена БД

```python
# SQLite integrity check (вручную)
import sqlite3
conn = sqlite3.connect(app_data.db)
conn.execute("PRAGMA integrity_check").fetchall()
# Если не OK: восстановить из backup
```

---

## 9. Корпоративные прокси с SSL Inspection

### 9.1. Проблема

В корпоративных сетях (РЖД, Сбер и др.) используется Deep SSL Inspection:
прокси-сервер подменяет TLS-сертификат `edu.rosmintrud.ru` своим, что вызывает
ошибку Schannel 10013 ("Не удалось создать защищенный канал SSL/TLS").

### 9.2. Диагностика

```powershell
# Проверить прокси
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer

# Проверить Schannel ошибки
Get-EventLog -LogName System -Source Schannel -Newest 5 | Format-List TimeGenerated, Message

# Тест через прокси (PowerShell)
Invoke-WebRequest -Uri "https://edu.rosmintrud.ru" -Proxy "http://ваш-прокси:3128" -ProxyUseDefaultCredentials -UseBasicParsing
```

На вкладке "Передача данных" → **Тест подключения** выводит:
- SSL-инспекция: Да/Нет
- Корпоративная среда: Да/Нет
- Рекомендации по настройке

### 9.3. Решение A: Отключить проверку TLS (быстрое)

1. Настройки прокси → **Авто (системные)**
2. Снимите галочку **TLS верификация (рекомендуется)**
3. Подтвердите предупреждение безопасности (аудит зафиксирует событие `TLS_WARNING`)
4. Сохраните настройки

Приложение автоматически предложит отключить TLS при обнаружении SSL-инспекции.

### 9.4. Решение B: Установить корпоративный CA-сертификат (безопасное)

Запросите у администратора корпоративный корневой сертификат
(для РЖД — `RzdCA` или `AD-CA-01`) и установите в:

```
Доверенные корневые центры сертификации → Локальный компьютер
```

После этого TLS verify может оставаться включённым.

### 9.5. Решение C: WinHTTP proxy (если авто не работает)

```powershell
netsh winhttp set proxy msk-proxy-03.msk.oao.rzd:3128
```

Приложение автоматически определяет корпоративную среду (.rzd, .corp, .oao)
и предпочитает WinINET backend (лучшая поддержка Negotiate/Kerberos).

### 9.6. Transport backends

| Backend | Приоритет | Корп. среда | Особенности |
|---------|-----------|-------------|-------------|
| WinINET | 1 (в корп. среде) | Предпочтительный | Negotiate/Kerberos, системный прокси |
| urllib | 2 | Запасной | Встроенный SSL context |
| requests | 3 | Запасной | Полный контроль verify |

При SSL-ошибке выполняется автоматический fallback между backends.
Если все backends не работают с TLS verify=True — возвращается
`ssl_error_detected=True` и UI предлагает отключить проверку.

### 9.7. Аудит

| Событие | Условие |
|---------|---------|
| `TLS_WARNING` | TLS verification выключена |
| `TLS_ERROR` | SSL handshake ошибка |
| `BACKEND_CHANGE` | Смена транспорта |
| `PROXY_CHANGE` | Изменение настроек прокси |

---

## 10. Security disclaimers

### Приложение НЕ

- Не является сертифицированным СКЗИ
- Не использует ГОСТ-криптографию
- Не заменяет политики и организационные меры
- Не гарантирует безопасность при скомпрометированной ОС

### Зависимость от ОС

- BitLocker: критически важен для защиты ПДн в покое
- Антивирус: обязателен для защиты от malware
- Windows Update: обязателен для закрытия уязвимостей
- Учётная запись: надёжный пароль обязателен
- Компрометация Windows-аккаунта = компрометация DPAPI = компрометация мастер-ключа

---

*Документ обновлён: 26.05.2026*
*Версия приложения: 3.2.0*
