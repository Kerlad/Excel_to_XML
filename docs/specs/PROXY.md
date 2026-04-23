# Прокси — Спецификация

## Обзор

Система поддерживает подключение через прокси-сервер для корпоративных сетей.

**Режимы:**
1. Без прокси — прямое подключение
2. Авто (системные) — из настроек Windows
3. Вручную — указанные параметры

---

## Режимы подключения

### 1. Без прокси
```go
transport := &http.Transport{
    DisableProxy: true,
}
```

### 2. Авто (системные)
```go
// Чтение из реестра Windows
regKey := "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings"
proxyURL := readRegistry(regKey, "ProxyServer")
```

### 3. Вручную
```go
proxyURL := "http://user:pass@proxy.example.com:3128"
transport := &http.Transport{
    Proxy: ProxyURL(proxyURL),
}
```

---

## Настройки прокси

**Файл:** `data/proxy_settings.json`

```json
{
    "mode": "manual",
    "url": "http://proxy.example.com:3128",
    "username": "domain\\user",
    "password": "secret",
    "tls_verify": false
}
```

### Поля

| Поле | Тип | Описание |
|------|-----|---------|
| mode | string | "none" / "auto" / "manual" |
| url | string | URL прокси (только для manual) |
| username | string | Логин (опционально) |
| password | string | Пароль (опционально) |
| tls_verify | bool | Проверка SSL (по умолчанию false) |

---

## Аутентификация

### Basic Authentication
```go
proxyURL := fmt.Sprintf("http://%s:%s@%s", username, password, proxyHost)
// Используется в URL, не в заголовке
```

### NTLM Authentication
```go
// Определяется по наличию \ в логине
if strings.Contains(username, "\\") || strings.Contains(username, "@") {
    // Используется NTLM
    auth := ntlm.NTLMProxyAuth{
        Username: username,
        Password: password,
    }
}
```

---

## TLS верификация

| Режим | Описание | Использование |
|-------|---------|-------------|
| false | Не проверять SSL | Корпоративный прокси с SSL-инспекцией |
| true | Проверять SSL | Прямое безопасное соединение |

```go
transport := &http.Transport{
    TLSClientConfig: &tls.Config{
        InsecureSkipVerify: !tlsVerify,
    },
}
```

---

## Тест подключения

```go
func testConnection(proxySettings ProxySettings) error {
    client := createHTTPClient(proxySettings)
    
    resp, err := client.Get("https://edu.rosmintrud.ru")
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != 200 {
        return fmt.Errorf("Status: %d", resp.StatusCode)
    }
    return nil
}
```

---

## Ошибки прокси

| Код | Сообщение |
|-----|----------|
| PROXY-001 | Не удалось подключиться к прокси |
| PROXY-002 | Ошибка аутентификации на прокси |
| PROXY-003 | Таймаут подключения |
| PROXY-004 | Прокси недоступен |

---

## Использование в API

### Отправка XML (FR-020)
```go
func SendXMLToAPI(xmlPath string, proxy ProxySettings) error {
    client := createHTTPClient(proxy)
    // POST к edu.rosmintrud.ru/api/set/push
}
```

### Запрос по SetId (FR-021)
```go
func QueryBySetID(setID string, proxy ProxySettings) error {
    client := createHTTPClient(proxy)
    // GET к edu.rosmintrud.ru/api/GetEducatedPersonXML?setId=...
}
```

### Запрос по СНИЛС (FR-022)
```go
func QueryBySNILS(snils string, proxy ProxySettings) error {
    client := createHTTPClient(proxy)
    // GET к edu.rosmintrud.ru/api/GetEducatedPersonXML?snils=...
}
```

---

## Функция создания HTTP-клиента

```go
func createHTTPClient(settings ProxySettings) *http.Client {
    transport := &http.Transport{}
    
    switch settings.Mode {
    case "none":
        transport.DisableProxy = true
        
    case "auto":
        // Чтение из системы
        
    case "manual":
        proxyFunc := ProxyURL(settings.URL)
        transport.Proxy = ProxyURL(proxyFunc)
    }
    
    return &http.Client{
        Transport: transport,
        Timeout: 30 * time.Second,
    }
}
```

---

## Сохранение настроек

| Действие | Файл |
|----------|------|
| Сохранить | `data/proxy_settings.json` |
| Загрузить | При запуске приложения |
| Применить | При каждом API-запросе |