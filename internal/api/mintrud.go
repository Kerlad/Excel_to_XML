package api

import (
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type MintrudAPI struct {
	BaseURL    string
	APIKey    string
	Proxy     ProxyConfig
	TLSVerify bool
}

type ProxyConfig struct {
	Type     string
	URL      string
	Username string
	Password string
}

type PushResponse struct {
	SetID    string `json:"setId"`
	Message string `json:"message"`
	Error   string `json:"error,omitempty"`
}

type GetBySetIDResponse struct {
	SetID              string       `json:"setId"`
	TotalCount         int          `json:"totalCount"`
	EducatedPersons []PersonInfo `json:"educatedPersons"`
}

type PersonInfo struct {
	SNILS    string `json:"snils"`
	BaseNo   string `json:"baseNo"`
	Status  string `json:"status"`
	Message string `json:"message"`
}

func NewMintrudAPI() *MintrudAPI {
	return &MintrudAPI{
		BaseURL:    "https://edu.rosmintrud.ru",
		TLSVerify: false,
	}
}

func (api *MintrudAPI) PushXML(xmlData []byte, apiKey string) (*PushResponse, error) {
	api.APIKey = apiKey

	encoded := base64.StdEncoding.EncodeToString(xmlData)

	data := url.Values{}
	data.Set("file", encoded)

	req, err := api.newRequest("POST", "/api/set/push", strings.NewReader(data.Encode()))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := api.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ошибка сервера: %d - %s", resp.StatusCode, string(body))
	}

	var result PushResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("ошибка парсинга ответа: %s", string(body))
	}

	if result.Error != "" {
		return nil, fmt.Errorf("ошибка API: %s", result.Error)
	}

	return &result, nil
}

func (api *MintrudAPI) GetBySetID(setID, apiKey string) (*GetBySetIDResponse, error) {
	api.APIKey = apiKey

	data := url.Values{}
	data.Set("setId", setID)

	req, err := api.newRequest("POST", "/api/GetEducatedPersonXML", strings.NewReader(data.Encode()))
	if err != nil {
		return nil, err
	}

	resp, err := api.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ошибка сервера: %d - %s", resp.StatusCode, string(body))
	}

	var result GetBySetIDResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("ошибка парсинга ответа: %s", string(body))
	}

	return &result, nil
}

func (api *MintrudAPI) GetBySNILS(snils, apiKey string) (*PersonInfo, error) {
	snils = strings.ReplaceAll(snils, "-", "")
	snils = strings.ReplaceAll(snils, " ", "")
	snils = strings.TrimSpace(snils)

	api.APIKey = apiKey

	data := url.Values{}
	data.Set("SNILS", snils)

	req, err := api.newRequest("POST", "/api/GetEducatedPersonXML", strings.NewReader(data.Encode()))
	if err != nil {
		return nil, err
	}

	resp, err := api.doRequest(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ошибка сервера: %d - %s", resp.StatusCode, string(body))
	}

	var result GetBySetIDResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("ошибка парсинга ответа: %s", string(body))
	}

	if len(result.EducatedPersons) == 0 {
		return nil, fmt.Errorf("работник не найден")
	}

	return &result.EducatedPersons[0], nil
}

func (api *MintrudAPI) newRequest(method, path string, body *strings.Reader) (*http.Request, error) {
	u, err := url.Parse(api.BaseURL + path)
	if err != nil {
		return nil, err
	}

	httpReq, err := http.NewRequest(method, u.String(), body)
	if err != nil {
		return nil, err
	}

	httpReq.Header.Set("User-Agent", "Excel-XML-Mintrud/1.23")
	httpReq.Header.Set("Accept", "application/json")

	if api.APIKey != "" {
		httpReq.Header.Set("X-API-Key", api.APIKey)
	}

	return httpReq, nil
}

func (api *MintrudAPI) doRequest(req *http.Request) (*http.Response, error) {
	client := &http.Client{
		Timeout: 60 * time.Second,
	}

	transport := &http.Transport{}

	if api.Proxy.Type == "manual" && api.Proxy.URL != "" {
		if proxyURL, err := url.Parse(api.Proxy.URL); err == nil {
			transport.Proxy = http.ProxyURL(proxyURL)
		}
	}

	if !api.TLSVerify {
		transport.TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
	}

	client.Transport = transport

	return client.Do(req)
}