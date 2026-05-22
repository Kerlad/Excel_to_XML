1. Ты — senior Python backend engineer, XML architect, QA engineer и AppSec engineer.

   Нужно провести аудит и реализовать ПРАВИЛЬНОЕ mock/testing представление файлового и XML API Минтруда РФ.

   КРИТИЧНО:
   Нельзя ломать текущую рабочую логику приложения.

   Главная задача:
   - формализовать структуру отправляемых файлов;
   - формализовать структуру принимаемых файлов;
   - реализовать безопасный parsing;
   - реализовать strict validation;
   - реализовать realistic mock payloads;
   - реализовать regression tests для форматов.

   ==================================================
   1. ОПИСАТЬ И РЕАЛИЗОВАТЬ СТРУКТУРУ ИСХОДЯЩИХ ФАЙЛОВ
   ==================================================

   Нужно создать formal specification для всех outgoing payloads.

   ==================================================
   ZIP STRUCTURE
   ==================================================

   Для API worker/test/protocol endpoints:

   В multipart/form-data должен отправляться:
   - ZIP архив;
   - либо .olot + .xml;
   - строго по endpoint-specific правилам.

   ==================================================
   ZIP ДЛЯ worker/test/protocol API
   ==================================================

   Архив ОБЯЗАТЕЛЬНО должен содержать:

   - Request.xml
   - Request.xml.sig

   Иногда дополнительно:
   - data.xml
   - data.xml.sig

   Проверить:
   - exact filenames;
   - case sensitivity;
   - duplicate filenames;
   - nested folders;
   - path traversal;
   - empty archives;
   - oversized archives.

   ==================================================
   PROTOСOL SEND STRUCTURE
   ==================================================

   Для:
   https://protocol.rosmintrud.ru/api/createSendProtocol

   ZIP должен содержать:

   - Request.xml
   - Request.xml.sig
   - data.xml
   - data.xml.sig

   Проверить логику:

   IF:
       IsSend=true
   THEN:
       data.xml.sig MUST exist

   IF:
       IsSend=false
   THEN:
       data.xml.sig MUST NOT exist

   Создать tests:
   - missing sig;
   - extra sig;
   - corrupted sig;
   - mismatched sig;
   - invalid zip structure.

   ==================================================
   OLOT STRUCTURE
   ==================================================

   Для:
   https://edu.rosmintrud.ru/api/set/push

   multipart/form-data должен содержать:

   - *.olot
   - *.xml

   Файл .olot:
   - является архивом;
   - содержит XML;
   - optionally содержит .sig.

   Проверить:
   - invalid extensions;
   - malformed olot;
   - missing xml;
   - missing sig;
   - NeedSend mismatch.

   ==================================================
   2. СТРУКТУРА Request.xml
   ==================================================

   Нужно formalize XML schemas.

   ==================================================
   COMMON ROOT
   ==================================================

   Большинство запросов:

   <Request>
       <ApiKey>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</ApiKey>
       ...
   </Request>

   Проверить:
   - ApiKey exists;
   - length == 32;
   - invalid chars;
   - whitespace;
   - unicode handling;
   - empty key.

   ==================================================
   WORKER CREATE
   ==================================================

   Структура:

   <Request>
       <ApiKey/>
       <Workers>
           <Worker outerId="">
               <LastName/>
               <FirstName/>
               <MiddleName/>
               <Phone/>
               <Email/>
               <Snils/>
               <IsForeignSnils/>
               <ForeignSnils/>
               <Citizenship/>
               <Position/>
               <EmployerTitle/>
               <EmployerInn/>
               <OrganizationUnitId/>
           </Worker>
       </Workers>
   </Request>

   Проверить:
   - required fields;
   - optional fields;
   - empty tags;
   - duplicated workers;
   - invalid SNILS;
   - invalid INN;
   - invalid phone;
   - invalid email.

   ==================================================
   WORKER EDIT
   ==================================================

   <Request>
       <ApiKey/>
       <Worker>
           <Id/>
           ...
       </Worker>
   </Request>

   Проверить:
   - missing Id;
   - invalid Id;
   - partial update behavior.

   ==================================================
   WORKER DELETE
   ==================================================

   <Request>
       <ApiKey/>
       <Id/>
   </Request>

   ==================================================
   TEST CREATE
   ==================================================

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
               <OrganizationUnitId/>
           </Test>
       </Tests>
   </Request>

   Проверить:
   - invalid WorkerId;
   - invalid dates;
   - timezone handling;
   - future dates;
   - duplicated tests.

   ==================================================
   TEST EDIT
   ==================================================

   <Request>
       <ApiKey/>
       <Test Id="">
           <DateOpen/>
           <OrganizationUnitId/>
       </Test>
   </Request>

   ==================================================
   FILTER REQUESTS
   ==================================================

   Для get endpoints:

   <EducatedPersonFilter>
       <ApiKey/>
       <PageNo/>
       <PageSize/>
       ...
   </EducatedPersonFilter>

   или:

   <Request>
       <ApiKey/>
       <WorkersFilter/>
   </Request>

   или:

   <Request>
       <ApiKey/>
       <Test/>
   </Request>

   Проверить:
   - pagination;
   - max PageSize;
   - negative values;
   - invalid filters;
   - invalid date ranges.

   ==================================================
   3. СТРУКТУРА ОТВЕТОВ API
   ==================================================

   Нужно реализовать strict response parsing.

   ==================================================
   SUCCESS RESPONSES
   ==================================================

   Поддерживать parsing:

   <Response>
       ...
   </Response>

   ИЛИ:

   <EducatedPersons>
       ...
   </EducatedPersons>

   ==================================================
   ERROR RESPONSES
   ==================================================

   Поддерживать parsing:

   <Response>
       <Error>
           <StatusCode/>
           <Message/>
           <DateTime/>
           <RequestId/>
       </Error>
   </Response>

   КРИТИЧНО:
   - parser НЕ ДОЛЖЕН падать на неизвестных тегах;
   - parser НЕ ДОЛЖЕН терять RequestId;
   - parser НЕ ДОЛЖЕН логировать весь XML.

   ==================================================
   4. ЧТО ДОЛЖНО ПАРСИТЬСЯ
   ==================================================

   Нужно реализовать strict-safe parsing.

   ==================================================
   PARSE REQUIRED
   ==================================================

   Из success responses:

   - Worker IDs;
   - Test IDs;
   - SetId;
   - SendEducatedPerson;
   - pagination;
   - VerificationList;
   - MessageStatus;
   - ProtocolNumber;
   - RegistryRecord;
   - ResultId;
   - LearnProgramId;
   - WorkplaceNumber;
   - OrganizationUnitId.

   ==================================================
   PARSE REQUIRED FROM ERRORS
   ==================================================

   Из Error:

   - StatusCode;
   - Message;
   - DateTime;
   - RequestId.

   RequestId MUST:
   - сохраняться;
   - попадать в audit logs;
   - не содержать ПДн.

   ==================================================
   5. SAFE XML PARSING
   ==================================================

   Использовать:
   - defusedxml;
   - secure parser;
   - disabled entities;
   - disabled network access.

   Проверить:
   - XXE;
   - Billion Laughs;
   - recursive entities;
   - external DTD;
   - malformed XML;
   - huge XML.

   ==================================================
   6. STRICT VALIDATION
   ==================================================

   Нужно реализовать validation BEFORE parsing.

   Проверять:
   - content-type;
   - file extension;
   - filename;
   - ZIP structure;
   - XML root;
   - required nodes;
   - node count;
   - XML size;
   - archive size.

   ==================================================
   7. MOCK PAYLOAD GENERATOR
   ==================================================

   Создать генератор:
   - valid XML;
   - invalid XML;
   - malformed ZIP;
   - corrupted signature;
   - oversized payload;
   - invalid encoding.

   ==================================================
   8. REGRESSION TESTS
   ==================================================

   Создать tests чтобы:
   - XML parser не стал insecure;
   - структура ZIP не сломалась;
   - parser не начал логировать XML;
   - parser не начал падать на новых полях API;
   - multipart structure осталась совместимой.

   ==================================================
   9. BUSINESS LOGIC COMPATIBILITY
   ==================================================

   КРИТИЧНО:
   После внедрения mock/tests приложение обязано:

   - продолжать работать с реальным API;
   - отправлять реальные multipart/form-data;
   - создавать реальные ZIP;
   - генерировать валидный XML;
   - корректно обрабатывать реальные Response/Error.

   Нельзя:
   - изменять production format;
   - упрощать XML ради тестов;
   - менять field names;
   - менять ZIP structure;
   - менять multipart naming.

   ==================================================
   10. В КОНЦЕ
   ==================================================

   Сгенерировать:

   - API_FORMATS.md
   - XML_STRUCTURE.md
   - RESPONSE_PARSING.md
   - MOCK_PAYLOADS.md
   - SECURITY_VALIDATION.md

   Включить:
   - схемы;
   - примеры;
   - edge-cases;
   - validation rules;
   - compatibility notes.

2. внести правки в gitignore по файлам теста