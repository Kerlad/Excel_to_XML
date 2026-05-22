# Спецификация Mock-тестов API Минтруда РФ

## 1. Цель

Формализация структур outgoing/incoming файлов, безопасный parsing, strict validation,
реалистичные mock payloads и regression-тесты для форматов API Минтруда.

**Критическое требование:** реализация не должна ломать текущую рабочую логику приложения.

---

## 2. Структура outgoing файлов

### 2.1. ZIP-архивы

Для endpoints `worker/*`, `test/*`, `protocol/*` используется multipart/form-data с ZIP-архивом.

#### 2.1.1. Worker/Test API (`worker/*`, `test/*`)
- `Request.xml` — обязателен
- `Request.xml.sig` — обязателен

#### 2.1.2. Protocol Send API (`protocol.rosmintrud.ru`)
- `Request.xml` — обязателен
- `Request.xml.sig` — обязателен
- `Data.xml` — опционально
- `Data.xml.sig` — опционально

Проверки:
- Точные имена файлов (case-sensitive)
- Отсутствие дубликатов
- Отсутствие вложенных папок
- **Path traversal** — не допускается
- Пустые архивы — reject
- Превышение размера — reject

**Бизнес-логика (Protocol send):**
```
IF IsSend=true  → Data.xml.sig MUST exist
IF IsSend=false → Data.xml.sig MUST NOT exist
```

### 2.2. OLOT-архивы

Для `edu.rosmintrud.ru/api/set/push`:
- `*.olot` — архив (ZIP), содержит `Data.xml` и опционально `Data.xml.sig`
- `*.xml` — Request.xml (`<Request><ApiKey/><NeedSend/></Request>`)

Проверки:
- Некорректное расширение
- Malformed olot
- Отсутствующий XML внутри olot
- Отсутствующий sig
- **NeedSend mismatch**: `NeedSend=true` без `Data.xml.sig` → reject; `NeedSend=false` с `Data.xml.sig` → reject

---

## 3. Структура Request.xml

### 3.1. Общий корень

```xml
<Request>
    <ApiKey>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</ApiKey>
    ...
</Request>
```

Проверки:
- ApiKey exists; length == 32; invalid chars; whitespace; unicode; empty

### 3.2. Worker Create

```xml
<Request>
    <ApiKey/>
    <Workers>
        <Worker outerId="">
            <LastName/><FirstName/><MiddleName/>
            <Phone/><Email/>
            <Snils/><IsForeignSnils/><ForeignSnils/><Citizenship/>
            <Position/><EmployerTitle/><EmployerInn/><OrganizationUnitId/>
        </Worker>
    </Workers>
</Request>
```

Проверки: required fields, optional fields, empty tags, duplicate workers, invalid SNILS/INN/phone/email.

### 3.3. Worker Edit

```xml
<Request>
    <ApiKey/>
    <Worker><Id/>...</Worker>
</Request>
```

Проверки: missing/invalid Id, partial update behavior.

### 3.4. Worker Delete

```xml
<Request>
    <ApiKey/><Id/>
</Request>
```

### 3.5. Test Create

```xml
<Request>
    <ApiKey/>
    <Tests>
        <Test outerId="">
            <WorkerId/><ContingentId/><IndustryId/>
            <LearnProgramId/><DateOpen/><Location/><OrganizationUnitId/>
        </Test>
    </Tests>
</Request>
```

Проверки: invalid WorkerId, invalid dates, timezone, future dates, duplicate tests.

### 3.6. Test Edit

```xml
<Request>
    <ApiKey/>
    <Test Id=""><DateOpen/><OrganizationUnitId/></Test>
</Request>
```

### 3.7. Filter Requests

Для get endpoints:

```xml
<EducatedPersonFilter>
    <ApiKey/><PageNo/><PageSize/>
    <SetId/><Snils/><LastName/><FirstName/>...
</EducatedPersonFilter>
```

Проверки: pagination bounds, max PageSize (5000), negative values, invalid filters, invalid date ranges.

---

## 4. Структура ответов API

### 4.1. Success — Push XML

```xml
<Response>
    <SetId>4282613</SetId>
    <SendEducatedPerson>False</SendEducatedPerson>
    <Message>Набор был создан</Message>
</Response>
```

### 4.2. Success — GetEducatedPersonXML

```xml
<EducatedPersons>
    <RegistryRecord setId="" internalExamination="" baseNo="" baseDateCreated="" outerId="">
        <Worker>...</Worker>
        <EmployerOrganization><Inn/><Title/></EmployerOrganization>
        <Test isPassed="" learnProgramId="">
            <Date/><ProtocolNumber/><LearnProgramTitle/>
        </Test>
    </RegistryRecord>
</EducatedPersons>
```

### 4.3. Error (все endpoints)

```xml
<Response>
    <Error>
        <StatusCode>400</StatusCode>
        <Message>Описание ошибки</Message>
        <DateTime>2024-12-12T12:00:00</DateTime>
        <RequestId>UUID</RequestId>
    </Error>
</Response>
```

**Критично:**
- Парсер не должен падать на неизвестных тегах
- Парсер не должен терять RequestId
- Парсер не должен логировать весь XML

---

## 5. Parse requirements

### 5.1. Из success responses

| Поле | Описание |
|------|----------|
| Worker IDs, Test IDs | Идентификаторы созданных объектов |
| SetId | Номер набора |
| SendEducatedPerson | Флаг отправки в РОЛ |
| pagination | PageNo, PageSize |
| VerificationList | Список верификаций |
| MessageStatus | Статус сообщения |
| ProtocolNumber | Номер протокола |
| RegistryRecord | Запись реестра |
| ResultId | Результат проверки |
| LearnProgramId/WokrplaceNumber/OrganizationUnitId | Доп. атрибуты |

### 5.2. Из Error

| Поле | Описание |
|------|----------|
| StatusCode | Код статуса |
| Message | Текст ошибки |
| DateTime | Дата/время запроса |
| RequestId | UUID для обращения в поддержку |

RequestId должен сохраняться в audit logs и не содержать ПДн.

---

## 6. Safe XML Parsing

Использовать `defusedxml.ElementTree` (через `utils.xml_safe`):
- `safe_parse_xml()` — файловый парсинг
- `safe_fromstring_xml()` — строковый парсинг
- `LimitedXMLParser` — лимиты: 50000 elements, depth 20, size 100MB

Проверки:
- XXE
- Billion Laughs
- Recursive entities
- External DTD
- Malformed XML
- Huge XML

---

## 7. Strict Validation (pre-parse)

| Проверка | Описание |
|----------|----------|
| content-type | multipart/form-data |
| file extension | .xml, .zip, .olot |
| filename | Request.xml, Request.xml.sig |
| ZIP structure | Валидный ZIP, без path traversal |
| XML root | <Request>, <EducatedPersonFilter> |
| required nodes | ApiKey, etc. |
| node count | Лимиты |
| XML size | Max 100MB |
| archive size | Лимиты |

---

## 8. Mock Payload Generator

Генератор тестовых данных:
- Valid XML
- Invalid XML (malformed, wrong root, missing tags)
- Malformed ZIP (corrupted, empty, nested folders)
- Corrupted signature
- Oversized payload
- Invalid encoding

---

## 9. Regression Tests

Покрытие:
- XML parser не стал insecure
- ZIP structure не сломалась
- Parser не начал логировать XML
- Parser не начал падать на новых полях API
- Multipart structure осталась совместимой

---

## 10. Business Logic Compatibility

После внедрения mock/tests приложение обязано:
- Продолжать работать с реальным API
- Отправлять реальные multipart/form-data
- Создавать реальные ZIP/OLOT
- Генерировать валидный XML
- Корректно обрабатывать реальные Response/Error

**Запрещено:**
- Менять production format
- Упрощать XML ради тестов
- Менять field names
- Менять ZIP structure
- Менять multipart naming

---

## 11. Генерируемые артефакты

- `API_FORMATS.md` — схемы outgoing/incoming форматов
- `XML_STRUCTURE.md` — детальная структура XML
- `RESPONSE_PARSING.md` — логика парсинга ответов
- `MOCK_PAYLOADS.md` — примеры mock-данных
- `SECURITY_VALIDATION.md` — правила security-валидации

---

## 12. .gitignore

Добавить в `.gitignore`:
- `tests/mock_payloads/`
- `tests/generated/`
- `*.generated.xml`
- `*.mock.*`
