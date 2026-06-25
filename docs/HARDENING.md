# Руководство по Hardening рабочего места ИСПДн

**Проект:** Норма ОТ: Реестр обучения
**Версия:** 3.1.0
**Дата:** 21.05.2026

## 1. Общие принципы

- Защита ИСПДн — это combination технических и организационных мер
- Приложение НЕ может защитить данные при скомпрометированной ОС
- Все рекомендации обязательны для production эксплуатации

## 2. Windows Hardening

### 2.1. Версия ОС
- Windows 10/11 Professional (для BitLocker)
- Windows 10/11 Enterprise (если доступна)
- **НЕ рекомендуется:** Windows Home (нет BitLocker, нет групповых политик)

### 2.2. BitLocker
- Включить на системном диске (C:)
- Включить на диске с данными (если отдельный)
- Recovery key: распечатать и хранить в сейфе
- Рекомендация: BitLocker + TPM + PIN

```powershell
# Проверка статуса
Get-BitLockerVolume -MountPoint "C:"

# Включение с TPM + PIN
Enable-BitLocker -MountPoint "C:" -TpmProtector -Pin "1234"
```

### 2.3. Антивирус
- Microsoft Defender (встроенный, бесплатный) — минимальный уровень
- Kaspersky Endpoint Security — рекомендовано для корпоративного использования
- **Требования:**
  - Real-time protection включён
  - Automatic updates включены
  - Scheduled scans: ежедневно
  - Exclusion: директория `%APPDATA%/Excel_to_XML/` (для производительности)

### 2.4. Firewall
- Windows Defender Firewall включён
- Правило: разрешить `python.exe` (или `NormaOT_Reestr.exe`) только на `edu.rosmintrud.ru`
- Блокировать все входящие соединения

```powershell
# Блокировать входящие
Set-NetFirewallProfile -Profile Domain,Public,Private -DefaultInboundAction Block

# Разрешить приложению исходящие на Минтруд
New-NetFirewallRule -DisplayName "NormaOT_Reestr" -Direction Outbound -Program "%ProgramFiles%\NormaOT_Reestr\NormaOT_Reestr.exe" -RemoteAddress "edu.rosmintrud.ru" -Action Allow
```

### 2.5. User Account Control (UAC)
- Уровень: Always notify (top, default)
- НЕ отключать UAC
- НЕ запускать приложение от имени администратора (если не требуется для установки)

```powershell
# Проверка уровня UAC
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "ConsentPromptBehaviorAdmin"
# Значение 2 = Always notify
```

### 2.6. Ограниченная учётная запись
- Оператор должен работать под **обычной** учётной записью (не Administrator)
- Отдельная учётная запись для оператора ИСПДн (не для日常工作)
- Пароль: минимум 14 символов, смена каждые 90 дней

```powershell
# Создание учётной записи оператора
New-LocalUser -Name "ISPDnOperator" -Password (Read-Host -AsSecureString) -PasswordNeverExpires $false
Add-LocalGroupMember -Group "Пользователи" -Member "ISPDnOperator"
```

### 2.7. Windows Update
- Автоматические обновления включены
- Не откладывать обновления безопасности
- Режим: Semi-Annual Channel (не Insider)

```powershell
# Настройка автоматических обновлений
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update" -Name "AUOptions" -Value 4
# 4 = Auto download and schedule install
```

### 2.8. Screen Lock
- Screen saver: включён, пароль при пробуждении
- Timeout: не более 5 минут
- Win+L: обучение оператора блокировать ПК при уходе

```powershell
# Настройка блокировки экрана через 5 минут
powercfg /change standby-timeout-ac 5
powercfg /change hibernate-timeout-ac 0
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveTimeOut" -Value "300"
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaverIsSecure" -Value "1"
```

## 3. Application-Specific Hardening

### 3.1. Passphrase Policy
- Минимум 12 символов
- Обязательно: заглавные + строчные + цифры + спецсимволы
- Смена каждые 90 дней
- Запрещено: запись на бумаге, хранение в файле, одинаковые passphrase на разных ПК

### 3.2. Auto-Lock Configuration
- Таймаут: 5-10 минут (рекомендация: 5)
- Включить через меню: Настройки → Настроить блокировку
- Проверить: LockDialog требует passphrase для разблокировки

### 3.3. TLS Verification
- verify=True (по умолчанию) — НЕ отключать
- Отключение только при письменном разрешении руководителя
- Каждое отключение логируется как TLS_WARNING

### 3.4. Backup Encryption
- Автоматический backup БД — данные уже зашифрованы полевым шифрованием
- Manual backup ключей — ZIP с PBKDF2-паролем
- Хранить backup на отдельном зашифрованном носителе
- Не хранить backup рядом с рабочей БД

## 4. Network Security

### 4.1. DNS
- Использовать корпоративный DNS-сервер
- Рекомендуется: DNS-over-HTTPS (DoH) в Windows
- Блокировать известные C2-домены (опционально)

### 4.2. Proxy
- Корпоративный прокси: NTLM/Kerberos аутентификация
- Требование: прокси не должен выполнять SSL-инспекцию для edu.rosmintrud.ru
- Если SSL-инспекция неизбежна: получить корневой сертификат прокси и установить в доверенные

### 4.3. Network Isolation (опционально)
- Выделенная VLAN для ИСПДн
- Доступ только к: edu.rosmintrud.ru (TCP/443), DNS, корпоративному прокси
- Блокировка: P2P, торренты, социальные сети, неизвестные порты

## 5. Physical Security

- ПК оператора: в запираемом помещении
- Доступ к ПК: только у оператора ИСПДн и руководителя
- USB-порты: отключить (Group Policy или BIOS)
- Веб-камера/микрофон: отключить (не нужны для приложения)
- Принтер: если нужен — отдельный защищённый канал

```powershell
# Отключение USB-накопителей (только чтение)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\USBSTOR" -Name "Start" -Value 4
# 4 = Disabled
```

## 6. Software Restrictions

- На ПК оператора установлено ТОЛЬКО: ОС, антивирус, NormaOT_Reestr
- Запрещено: сторонние браузеры, мессенджеры, торренты, игры
- Запрещено: установка ПО без разрешения администратора
- Разрешено: Microsoft Office (для просмотра XLSX-экспортов)

## 7. Monitoring

### 7.1. Что мониторить
- Event Viewer: Security (лог-он/лог-офф, неудачные логины)
- Аудит-лог приложения: необычная активность
- Windows Defender: обнаруженные угрозы
- Размер логов приложения (не должны превышать 5MB)

### 7.2. Аудит Windows
```powershell
# Включить аудит входа в систему
auditpol /set /subcategory:"Logon" /success:enable /failure:enable

# Включить аудит доступа к файлам
auditpol /set /subcategory:"File System" /success:enable /failure:enable
```

## 8. Update Policy

### 8.1. Application Updates
- Manual via git clone / PyInstaller build
- Check for updates: monthly or when security advisory published
- Verify integrity: compare git tags, review CHANGELOG

### 8.2. Dependency Updates
```powershell
# Monthly: check for outdated packages
pip list --outdated

# Check for known CVEs
pip-audit

# Update with version pin
pip install cryptography==42.0.5 lxml==5.2.0
```

### 8.3. OS Updates
- Windows Update: автоматические
- Reboot policy: не откладывать перезагрузку более 7 дней
- .NET framework: актуальная версия (для WinINET backend)

## 9. Audit Log Review

### 9.1. Daily (quick)
- Проверить audit.log на TLS_WARNING
- Проверить error.log на ошибки БД

### 9.2. Weekly
- Просмотр аудита через LogViewerDialog
- Проверить: нет ли необычных KEY_ACCESS
- Проверить: размер логов

### 9.3. Monthly
- Полная проверка HMAC целостности аудит-лога
- Проверка master.key.json integrity
- Проверка backup (ротация, читаемость)
- Анализ: сколько событий каждого типа
