# Шифрование — Спецификация

## Обзор

Система использует шифрование для защиты конфиденциальных данных:
- API ключ
- Журнал проверки знаний
- Настройки прокси
- Данные комиссии

**Алгоритм:** AES-GCM (Galois/Counter Mode)  
**Реализация:** Go `crypto/aes` + `crypto/cipher`

---

## Ключи шифрования

### Главный ключ (Master Key)

Формируется из имени пользователя системы:

```go
func deriveKey(password string) []byte {
    salt := "ExcelToXML_Salt_2026"
    hash := sha256.Sum256([]byte(password + salt))
    return hash[:32]  // 256-bit ключ
}
```

| Компонент | Значение |
|----------|---------|
| Salt | `ExcelToXML_Salt_2026` |
| Функция | SHA256 |
| Длина ключа | 32 байта (256 бит) |

### Получение пароля

```go
func GetEncryptionPassword() string {
    user, _ := user.Current()
    hash := sha256.Sum256([]byte(user.Username + "_ExcelToXML_2026"))
    return fmt.Sprintf("%x", hash)[:32]
}
```

---

## Шифрование данных

### AES-GCM

```go
func encrypt(plaintext []byte, key []byte) ([]byte, error) {
    block, _ := aes.NewCipher(key)
    gcm, _ := cipher.NewGCM(block)
    
    nonce := make([]byte, gcm.NonceSize())
    rand.Read(nonce)
    
    // nonce + ciphertext + tag
    return gcm.Seal(nonce, nonce, plaintext, nil), nil
}
```

| Компонент | Размер |
|----------|-------|
| Nonce | 12 байт |
| Tag | 16 байт |
| Min ciphertext | 28 байт |

### Дешифрование

```go
func decrypt(ciphertext []byte, key []byte) ([]byte, error) {
    block, _ := aes.NewCipher(key)
    gcm, _ := cipher.NewGCM(block)
    
    nonceSize := gcm.NonceSize()
    nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]
    
    return gcm.Open(nil, nonce, ciphertext, nil)
}
```

---

## Файлы данных

| Файл | Шифрование | Описание |
|------|------------|---------|
| `data/settings.json` | AES-GCM | Настройки УЦ и работодателя |
| `data/workers.json` | AES-GCM | Данные работников |
| `data/journal.json` | AES-GCM | Журнал проверки знаний |
| `data/commission.dat` | AES-GCM | Данные комиссии |
| `data/api_key.json` | Не используется (base64) | API ключ (только кодирование) |
| `data/proxy_settings.json` | Не используется (base64) | Настройки прокси |

### Формат settings.json
```json
{
    "tc_inn": "1234567890",
    "tc_title": "УЦ Профессионал",
    "employer_inn": "0987654321",
    "employer_title": "ООО Компания",
    "xsd_path": "data/educated_person_import_v1.0.9.xsd",
    "word_path": "data/Protokol.docx",
    "api_key": "encoded_base64_string",
    "salt": "ExcelToXML_Salt_2026"
}
```

---

## API ключ

**Кодирование:** Base64 (не шифрование)

```go
func SaveAPIKey(key string) error {
    encoded := base64.StdEncoding.EncodeToString([]byte(key))
    return writeFile("data/api_key.json", encoded)
}
```

**Причина:** API ключ можно восстановить при утере, поэтому достаточно кодирования.

---

## Настройки прокси

**Кодирование:** Base64 (только для username/password)

```json
{
    "mode": "manual",
    "url": "http://proxy.example.com:3128",
    "username_encrypted": "dXNlcm5hbWU=",
    "password_encrypted": "cGFzc3dvcmQ=",
    "tls_verify": false
}
```

---

## Включение/выключение шифрования

### Включение
```go
func SetEncryptionPassword(password string) {
    if password == "" {
        cryptoKey = nil  // Отключить
    } else {
        cryptoKey = deriveKey(password)
    }
}
```

### Статус
```go
func GetEncryptionStatus() bool {
    return cryptoKey != nil
}
```

---

## Ошибки

| Код | Сообщение |
|-----|----------|
| CRYPTO-001 | Ошибка создания ключа |
| CRYPTO-002 | Ошибка шифрования |
| CRYPTO-003 | Ошибка дешифрования |
| CRYPTO-004 | Неверный пароль |
| CRYPTO-005 | Данные повреждены |

---

## Безопасность

- Ключ привязан к имени пользователя Windows
- На другой машине данные не расшифровать
- Пароли не хранятся в открытом виде
- Salt предотвращает rainbow table атаки

---

## Управление пользователем

| Действие | Описание |
|----------|---------|
| Ввод пароля | Включить шифрование |
| Пустой пароль | Отключить шифрование |
| Запуск приложения | Автоматическое определение ключа |