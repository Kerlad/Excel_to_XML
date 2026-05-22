# API Реестра обученных по охране труда лиц

Рекомендации по программному взаимодействию с Реестром обученных по охране труда лиц
через API портала edu.rosmintrud.ru.

---

## 1. Отправка набора записей (push)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/set/push
Content-Type: multipart/form-data
```

### Формат запроса

Два файла в multipart/form-data:

1. **`*.xml`** — Request.xml, корневой элемент `<Request>`:
   - `<ApiKey>` (обязательный, 32 символа) — ключ из личного кабинета
   - `<NeedSend>` (опциональный, boolean) — флаг отправки в РОЛ.
     - По умолчанию `false`
     - Если в `.olot` есть `.sig` → значение автоматически устанавливается в `true`
     - Если `NeedSend=false`, но `.sig` присутствует → набор НЕ будет отправлен в РОЛ

2. **`*.olot`** — ZIP-архив, содержащий:
   - `Data.xml` (обязательно)
   - `Data.xml.sig` (опционально, только если `NeedSend=true`)

### Успешный ответ

```xml
<Response>
    <SetId>4282613</SetId>
    <SendEducatedPerson>False</SendEducatedPerson>
    <Message>Набор был создан</Message>
</Response>
```

| Элемент | Описание |
|---------|----------|
| `SetId` | Номер созданного набора |
| `SendEducatedPerson` | `true` — набор отправлен в РОЛ; `false` — не отправлен |
| `Message` | Дополнительная информация |

### Ошибка

```xml
<Response>
    <Error>
        <StatusCode>400</StatusCode>
        <Message>Описание ошибки</Message>
    </Error>
</Response>
```

| Элемент | Описание |
|---------|----------|
| `StatusCode` | Код ошибки |
| `Message` | Детализированное сообщение |

---

## 2. Получение записей из реестра (GetEducatedPersonXML)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/GetEducatedPersonXML
Content-Type: multipart/form-data
```

### Формат запроса

Один файл `*.xml` с корневым элементом `<EducatedPersonFilter>`:

```xml
<EducatedPersonFilter>
    <ApiKey>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</ApiKey>
    <PageNo>1</PageNo>
    <PageSize>100</PageSize>
    <!-- опциональные фильтры -->
</EducatedPersonFilter>
```

#### Обязательные элементы
- `<ApiKey>` — 32 символа

#### Опциональные элементы (фильтры)

| Элемент | Описание |
|---------|----------|
| `No` | Реестровый номер |
| `PageNo` | Номер страницы (по умолч. 1) |
| `PageSize` | Размер страницы (по умолч. 100, макс. 5000) |
| `LastName` | Фамилия |
| `FirstName` | Имя |
| `MiddleName` | Отчество |
| `OuterId` | Идентификатор из другой системы |
| `Snils` | СНИЛС |
| `SetId` | Номер набора |
| `Position` | Должность |
| `DateCreatedFrom` | Дата создания (от) |
| `DateCreatedBefore` | Дата создания (до) |
| `TestDateFrom` | Дата тестирования (от) |
| `TestDateBefore` | Дата тестирования (до) |
| `LearnProgramId` | Идентификатор программы обучения |
| `ProtocolNumber` | Номер протокола |

### Успешный ответ

```xml
<EducatedPersons>
    <RegistryRecord setId="" internalExamination="" baseNo="" baseDateCreated="" outerId="">
        <Worker>
            <LastName></LastName>
            <FirstName></FirstName>
            <MiddleName></MiddleName>
            <Snils></Snils>
            <ForeignSnils></ForeignSnils>
            <IsForeignSnils></IsForeignSnils>
            <Citizenship></Citizenship>
            <Position></Position>
            <EmployerInn></EmployerInn>
            <EmployerTitle></EmployerTitle>
        </Worker>
        <EmployerOrganization>
            <Inn></Inn>
            <Title></Title>
        </EmployerOrganization>
        <Test isPassed="" learnProgramId="">
            <Date></Date>
            <ProtocolNumber></ProtocolNumber>
            <LearnProgramTitle></LearnProgramTitle>
        </Test>
    </RegistryRecord>
</EducatedPersons>
```

#### Атрибуты RegistryRecord

| Атрибут | Описание |
|---------|----------|
| `setId` | Номер набора |
| `internalExamination` | Флаг внутреннего экзамена |
| `baseNo` | Реестровый номер |
| `baseDateCreated` | Дата создания записи |
| `outerId` | Внешний идентификатор |

#### Атрибуты Test

| Атрибут | Описание |
|---------|----------|
| `isPassed` | Статус прохождения |
| `learnProgramId` | Идентификатор программы |

### Ошибка

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

| Элемент | Описание |
|---------|----------|
| `StatusCode` | Код ошибки |
| `Message` | Текст ошибки |
| `DateTime` | Дата и время запроса |
| `RequestId` | UUID для обращения в поддержку |

---

## 3. Получение записей о работнике (worker/get)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/worker/get
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив с двумя файлами:
- `Request.xml` — корневой элемент `<Request>`:
  - `<ApiKey>` — обязательный, 32 символа
  - `<WorkersFilter>` — обязательный, содержит поля фильтрации
- `Request.xml.sig` — подпись

#### Поля фильтрации WorkersFilter

| Элемент | Описание |
|---------|----------|
| `Id` | Номер работника |
| `OuterId` | Внешний идентификатор |
| `PageNo` | Номер страницы |
| `PageSize` | Размер страницы |
| `Login` | Логин работника |
| `LastName` | Фамилия |
| `FirstName` | Имя |
| `MiddleName` | Отчество |
| `Phone` | Телефон |
| `Email` | Email |
| `Snils` | СНИЛС |
| `Citizenship` | Гражданство |
| `Position` | Должность |
| `EmployerTitle` | Наименование работодателя |
| `EmployerInn` | ИНН работодателя |
| `OrganizationUnitId` | Подразделение |

### Успешный ответ

```xml
<Response>
    <Workers>
        <Worker>
            <Id></Id>
            <OuterId></OuterId>
            <AccessKey></AccessKey>
            <Login></Login>
            <PasswordTemp></PasswordTemp>
            <LastName></LastName>
            <FirstName></FirstName>
            <MiddleName></MiddleName>
            <Snils></Snils>
            <ForeignSnils></ForeignSnils>
            <IsForeignSnils></IsForeignSnils>
            <Citizenship></Citizenship>
            <Position></Position>
            <EmployerInn></EmployerInn>
            <OrganizationUnitId></OrganizationUnitId>
            <EmployerTitle></EmployerTitle>
        </Worker>
    </Workers>
</Response>
```

### Ошибка — стандартный `<Error>` с `StatusCode`, `Message`, `DateTime`, `RequestId`.

---

## 4. Создание работника (worker/create)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/worker/create
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив: `Request.xml` + `Request.xml.sig`.

`Request.xml`:
```xml
<Request>
    <ApiKey/>
    <Workers>
        <Worker outerId="">
            <LastName/>   <!-- обязательный -->
            <FirstName/>  <!-- обязательный -->
            <MiddleName/>
            <Phone/>      <!-- обязательный -->
            <Email/>      <!-- обязательный -->
            <Snils/>
            <IsForeignSnils/>
            <ForeignSnils/>
            <Citizenship/>
            <Position/>   <!-- обязательный -->
            <EmployerTitle/>  <!-- обязательный -->
            <EmployerInn/>    <!-- обязательный -->
            <OrganizationUnitId/>
        </Worker>
    </Workers>
</Request>
```

### Успешный ответ

```xml
<Response>
    <Worker id="" outerId=""></Worker>
</Response>
```

Атрибут `id` — присвоенный идентификатор работника.

### Ошибка — стандартный `<Error>`.

---

## 5. Редактирование работника (worker/edit)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/worker/edit
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив: `Request.xml` + `Request.xml.sig`.

`Request.xml`:
```xml
<Request>
    <ApiKey/>
    <Worker>
        <Id/>            <!-- обязательный -->
        <LastName/>      <!-- обязательный -->
        <FirstName/>     <!-- обязательный -->
        <MiddleName/>
        <Phone/>         <!-- обязательный -->
        <Email/>         <!-- обязательный -->
        <Snils/>
        <IsForeignSnils/>
        <ForeignSnils/>
        <Citizenship/>
        <Position/>      <!-- обязательный -->
        <EmployerTitle/> <!-- обязательный -->
        <EmployerInn/>   <!-- обязательный -->
        <OrganizationUnitId/>
    </Worker>
</Request>
```

### Успешный ответ

HTTP 200 с `<Error>` внутри:
```xml
<Response>
    <Error>
        <StatusCode>200</StatusCode>
        <Message>Успешно</Message>
    </Error>
</Response>
```

### Ошибка — стандартный `<Error>`.

---

## 6. Удаление работника (worker/delete)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/worker/delete
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив: `Request.xml` + `Request.xml.sig`.

`Request.xml`:
```xml
<Request>
    <ApiKey/>
    <Id/>   <!-- обязательный: идентификатор работника -->
</Request>
```

### Успешный ответ — HTTP 200, `<StatusCode>200</StatusCode><Message>Успешно</Message>`.

### Ошибка — стандартный `<Error>`.

---

## 7. Получение записей о тестовых попытках (test/get)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/test/get
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив: `Request.xml` + `Request.xml.sig`.

`Request.xml`:
```xml
<Request>
    <ApiKey/>
    <Test>
        <!-- опциональные поля фильтрации -->
        <WorkerId/>
        <ResultId/>
        <ContingentId/>
        <IndustryId/>
        <LearnProgramId/>
        <DateStart/>
        <DateEnd/>
        <PageNo/>
        <PageSize/>
        <OrganizationUnitId/>
    </Test>
</Request>
```

#### Значения ResultId

| Значение | Статус |
|----------|--------|
| 1 | Неизвестно |
| 2 | Удовлетворительно |
| 3 | Неудовлетворительно |

### Успешный ответ

```xml
<Response>
    <Tests>
        <Test>
            <Id></Id>
            <DateCreated></DateCreated>
            <ContingentId></ContingentId>
            <IndustryId></IndustryId>
            <LearnProgramId></LearnProgramId>
            <Location></Location>
            <DateOpen></DateOpen>
            <ResultId></ResultId>
            <IsAddedToReestrPerson></IsAddedToReestrPerson>
            <OrganizationUnitId></OrganizationUnitId>
        </Test>
    </Tests>
</Response>
```

### Ошибка — стандартный `<Error>`.

---

## 8. Создание тестовых попыток (test/create)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/test/create
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив: `Request.xml` + `Request.xml.sig`.

`Request.xml`:
```xml
<Request>
    <ApiKey/>
    <Tests>
        <Test outerId="">
            <WorkerId/>
            <ContingentId/>
            <IndustryId/>
            <LearnProgramId/>
            <DateOpen/>
            <Location/>
            <OrganizationUnitId/>  <!-- опционально, только для работодателей -->
        </Test>
    </Tests>
</Request>
```

### Успешный ответ

```xml
<Response>
    <Tests>
        <Test testId="" outerId=""></Test>
    </Tests>
</Response>
```

Атрибут `testId` — присвоенный идентификатор попытки.

### Ошибка — стандартный `<Error>`.

---

## 9. Редактирование тестовых попыток (test/edit)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/test/edit
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив: `Request.xml` + `Request.xml.sig`.

`Request.xml`:
```xml
<Request>
    <ApiKey/>
    <Test Id="">
        <DateOpen/>
        <OrganizationUnitId/>  <!-- опционально -->
    </Test>
</Request>
```

### Успешный ответ — HTTP 200, `<StatusCode>200</StatusCode><Message>Успешно</Message>`.

### Ошибка — стандартный `<Error>`.

---

## 10. Удаление тестовых попыток (test/delete)

### Endpoint
```
POST https://edu.rosmintrud.ru/api/test/delete
Content-Type: multipart/form-data
```

### Формат запроса

ZIP-архив: `Request.xml` + `Request.xml.sig`.

`Request.xml`:
```xml
<Request>
    <ApiKey/>
    <Test id=""/>   <!-- обязательный атрибут: идентификатор тестирования -->
</Request>
```

### Успешный ответ — HTTP 200, `<StatusCode>200</StatusCode><Message>Успешно</Message>`.

### Ошибка — стандартный `<Error>`.

---

## 11. Ошибки валидации и формата данных

| Ошибка | Пояснение |
|--------|-----------|
| Неверное количество файлов | Передано больше одного файла (для методов, ожидающих 1 файл) |
| Некорректная структура файла импорта. Ожидался тип файла .zip | Не передан .zip |
| Один файл должен быть .olot, а другой .xml | Неверное расширение для push |
| Некорректное расширение файла запроса (допустимы только *.xml) | Для методов, ожидающих .xml |
| Не найден файл Request.xml | В .zip отсутствует Request.xml |
| Не найден файл Request.xml.sig | В .zip отсутствует подпись |
| Документ не соответствует схеме XSD | `messages: {ErrorMessages}` — массив ошибок валидации |
| NeedSend=true, но не найден Data.xml.sig | Флаг отправки в РОЛ без подписи данных |
| NeedSend=false, но добавлен файл Data.xml.sig | Флаг без отправки, но подпись присутствует |
| Некорректное значение параметра ApiKey | Длина != 32 символа |
| Не найдена информация по ключу `{apiKey}` | Ключ не зарегистрирован в системе |
| Не найден тип ключа | Не удалось определить тип организации |

---

## 12. Примечания

- Все запросы — **POST**, Content-Type: **multipart/form-data**
- Валидация выполняется на стороне сервера (XSD, структура ZIP, обязательные поля)
- `RequestId` из ответов об ошибках следует сохранять для обращения в поддержку
- Формат дат: `YYYY-MM-DD` или `DD.MM.YYYY` в зависимости от поля
- Максимальный `PageSize` для `GetEducatedPersonXML`: **5000**
