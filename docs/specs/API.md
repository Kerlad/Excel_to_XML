# API Минтруда — Спецификация

## Обзор

API Минтруда используется для:
1. Отправки XML с данными обученных работников
2. Получения регистрационных номеров по SetId или СНИЛС

**Базовый URL:** `https://edu.rosmintrud.ru`

---

## Аутентификация

| Элемент | Значение | Notes |
|--------|---------|-------|
| Header | `X-API-Key` | 32-символьный ключ |
| Header | `Content-Type` | `application/xml` или `multipart/form-data` |

---

## Эндпоинты

### 1. Отправка XML

**POST** `/api/set/push`

| Параметр | Тип | Описание |
|---------|-----|---------|
| Request | multipart/form-data | Request.xml + Data.olot |

**Request.xml:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>{32-символьный ключ}</ApiKey>
    <NeedSend>false</NeedSend>
</Request>
```

**Data.olot:** ZIP-архив, содержащий Data.xml (с заглавной D)

| Код ответа | Описание |
|------------|----------|
| 200 | Успешно. В теле ответа: `{ "setId": "XXXX" }` |
| 400 | Ошибка валидации |
| 401 | Неверный API ключ |
| 500 | Ошибка сервера |

---

### 2. Запрос регистрационных номеров

**GET** `/api/GetEducatedPersonXML?setId={SetId}`

**GET** `/api/GetEducatedPersonXML?snils={СНИЛС}`

| Header | Значение |
|--------|---------|
| X-API-Key | 32-символьный ключ |

**Ответ (XML):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<EducatedPersons>
    <EducatedPerson>
        <SNILS>123-456-789 00</SNILS>
        <LastName>Иванов</LastName>
        <FirstName>Иван</FirstName>
        <MiddleName>Иванович</MiddleName>
        <Program>1</Program>
        <LearnProgramTitle>Оказание первой помощи пострадавшим</LearnProgramTitle>
        <ProtocolNumber>001</ProtocolNumber>
        <Date>2026-04-15</Date>
        <RegisterNumber>123456789012345</RegisterNumber>
    </EducatedPerson>
</EducatedPersons>
```

---

## Форматы данных

### СНИЛС
- Формат: `123-456-789 00` (с дефисами и пробелом)
- При отправке: передаётся как есть

### Дата
- Формат XML: `YYYY-MM-DD` (xs:date)
- Пример: `2026-04-15`

### Результат
| XML значение | Описание |
|------------|---------|
| true | Удовлетворительно |
| false | Неудовлетворительно |

---

## Коды ошибок API

| Код | Сообщение | Причина |
|-----|----------|--------|
| 401 | Unauthorized | Неверный API ключ |
| 404 | Not Found | SetId не найден |
| 500 | Internal Server Error | Ошибка сервера Минтруда |

---

## Ограничения

- maxRecords: 5000 на один SetId
- maxFileSize: 10 MB

---

## Ссылки

- Документация: https://akot.rosmintrud.ru/sout/info
- Личный кабинет: https://edu.rosmintrud.ru