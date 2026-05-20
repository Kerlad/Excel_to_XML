# 🔌 API Минтруда

## Настройка API-ключа

1. Зарегистрируйтесь на [edu.rosmintrud.ru](https://edu.rosmintrud.ru)
2. Перейдите в личный кабинет, сгенерируйте API-ключ (32 символа)
3. Вставьте ключ в приложение на вкладке **«Передача данных»**

## Transport Backends

Приложение поддерживает несколько HTTP-транспортов:

| Backend | Описание | Преимущества |
|---------|----------|--------------|
| Auto | Автоматический выбор лучшего | Fallback между requests и WinINET |
| Requests | Библиотека requests | Windows Integrated Authentication (Negotiate/Kerberos) |
| WinINET | Windows Internet API | Лучшая поддержка корпоративных прокси |

## Эндпоинты

### Отправка XML
```
POST https://edu.rosmintrud.ru/api/set/push
Content-Type: multipart/form-data
```
Формирует multipart-запрос с двумя файлами:
- `Request.xml` — содержит `<ApiKey>` и метаданные
- `Data.olot` — ZIP-архив с `Data.xml`

**Ответ:** SetId — уникальный идентификатор набора.

### Запрос регистрационных номеров
```
POST https://edu.rosmintrud.ru/api/GetEducatedPersonXML
Content-Type: application/xml
```

**Формат запроса (SetId):**
```xml
<EducatedPersonFilter>
    <ApiKey>32-символьный-ключ</ApiKey>
    <PageNo>1</PageNo>
    <PageSize>5000</PageSize>
    <SetId>идентификатор-набора</SetId>
</EducatedPersonFilter>
```

**Формат запроса (СНИЛС):**
```xml
<EducatedPersonFilter>
    <ApiKey>32-символьный-ключ</ApiKey>
    <PageNo>1</PageNo>
    <PageSize>5000</PageSize>
    <Snils>XXX-XXX-XXX XX</Snils>
</EducatedPersonFilter>
```

**Особенности:**
- СНИЛС передаётся в формате `XXX-XXX-XXX XX` (с дефисами и пробелом)
- `<ApiKey>` обязателен во всех запросах
- XML без пространства имён на `EducatedPersonFilter`
- Пагинация: break при `len(records) < page_size`

**Формат ответа:**
```xml
<ArrayOfRegistryRecord>
    <RegistryRecord>
        <Worker>
            <Snils>XXX-XXX-XXX XX</Snils>
            <LastName>Иванов</LastName>
            <FirstName>Иван</FirstName>
            <MiddleName>Иванович</MiddleName>
            <Position>Инженер</Position>
            <EmployerInn>1234567890</EmployerInn>
            <EmployerTitle>ООО Пример</EmployerTitle>
        </Worker>
        <Test>
            <learnProgramId>1</learnProgramId>
            <LearnProgramTitle>Оказание первой помощи</LearnProgramTitle>
            <ProtocolNumber>П-2024-001</ProtocolNumber>
            <Date>2025-09-26T00:00:00</Date>
            <isPassed>true</isPassed>
        </Test>
        <baseNo>REG-2025-00001</baseNo>
    </RegistryRecord>
</ArrayOfRegistryRecord>
```

**Нормализация дат:** ISO даты (`2025-09-26T00:00:00`) автоматически конвертируются в `DD.MM.YYYY`.

## Обработка ошибок

При ошибке отправки XML полный ответ сервера сохраняется в `log/error_response.txt` (UTF-8 BOM) для диагностики.

## Корпоративные прокси

- **Авто:** системные настройки Windows (реестр, WPAD)
- **Ручные:** `http://user:pass@host:port` с Basic-аутентификацией
- **NTLM/Kerberos:** через WinINET или Requests с pywin32
- **TLS:** включён по умолчанию, отключается через UI для SSL-инспекций
