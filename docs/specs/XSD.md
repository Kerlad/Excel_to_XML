# XSD Валидация — Спецификация

## Обзор

Система валидирует XML по XSD-схеме Минтруда перед:
1. Экспортом в XML
2. Отправкой на сервер (дополнительная проверка)

**Расположение схемы:** `data/educated_person_import_v1.0.9.xsd`

---

## Структура XSD

### Корневой элемент
```xml
<xs:element name="EducatedPersonsArchive">
    <xs:complexType>
        <xs:sequence>
            <xs:element ref="EducationInfo" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
</xs:element>
```

### EducationInfo
```xml
<xs:element name="EducationInfo">
    <xs:complexType>
        <xs:sequence>
            <xs:element ref="TrainingCenter" minOccurs="0"/>
            <xs:element ref="Employer" minOccurs="0"/>
            <xs:element ref="EducatedPersons" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
</xs:element>
```

### TrainingCenter
| Поле | Тип | Обязательно | Ограничения |
|------|-----|------------|----------|
| INN | xs:string | Да | 10 или 12 цифр |
| Name | xs:string | Да | Макс 500 символов |

### Employer
| Поле | Тип | Обязательно | Ограничения |
|------|-----|------------|----------|
| INN | xs:string | Да | 10 или 12 цифр |
| Name | xs:string | Да | Макс 500 символов |

### EducatedPerson
| Поле | Тип | Обязательно | Ограничения |
|------|-----|------------|----------|
| SNILS | xs:string | Да | Формат XXX-XXX-XXX XX |
| LastName | xs:string | Да | Макс 100 символов |
| FirstName | xs:string | Да | Макс 100 символов |
| MiddleName | xs:string | Нет | Макс 100 символов |
| Position | xs:string | Да | Макс 255 символов |

### Examination (внутри EducatedPerson)
| Поле | Тип | Обязательно | Ограничения |
|------|-----|------------|----------|
| Number | xs:string | Да | 1-29, кроме 5 |
| ProgramName | xs:string | Нет | Макс 500 символов |
| Result | xs:boolean | Да | true/false |
| ExamDate | xs:date | Да | YYYY-MM-DD |
| ProtocolNumber | xs:string | Да | Макс 50 символов |

---

## Правила валидации

### 1. СНИЛС
- Должен содержать 11 цифр
- Формат для отображения: `123-456-789 00`
- При валидации удаляются `-` и `пробел`

### 2. ИНН
- Юридическое лицо: 10 цифр
- Индивидуальный предприниматель: 12 цифр

### 3. Номер программы
- Допустимые значения: 1,2,3,4,6-29
- Исключён: 5
- Разделитель запятая для нескольких

### 4. Дата
- Формат: YYYY-MM-DD
- Не должна быть в будущем

### 5. Результат
| XML | Интерфейс |
|-----|----------|
| true | Удовлетворительно |
| false | Неудовлетворительно |

---

## Валидация при экспорте

```go
func ValidateXML(xmlData string, xsdPath string) error {
    // 1. Парсинг XML
    // 2. Применение XSD
    // 3. Проверка обязательных полей
    // 4. Проверка форматов
}
```

---

## Ошибки валидации

| Код | Сообщение |
|-----|----------|
| XSD-001 | Ошибка парсинга XML |
| XSD-002 | Обязательное поле отсутствует: {field} |
| XSD-003 | Неверный формат СНИЛС |
| XSD-004 | Неверный ИНН |
| XSD-005 | Неверный номер программы: {num} |
| XSD-006 | Дата не может быть в будущем |
| XSD-007 | Значение Result должно быть true или false |

---

## Кэширование схемы

- Схема загружается при первом использовании
- Кэшируется в памяти до перезапуска
- Путь к схеме хранится в `data/xsd_path.txt`

---

## Ссылки

- XSD-схема: https://akot.rosmintrud.ru/sout/info