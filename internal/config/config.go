package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type Config struct {
	Theme       string `json:"theme"` // "light" or "dark"
	TCINN       string `json:"tc_inn"`
	TCTitle     string `json:"tc_title"`
	EmployerINN string `json:"employer_inn"`
	EmployerTitle string `json:"employer_title"`
	ProxyType  string `json:"proxy_type"` // "none", "auto", "manual"
	ProxyURL   string `json:"proxy_url"`
	ProxyUser  string `json:"proxy_user"`
	ProxyPass  string `json:"proxy_pass"`
	TLSVerify  bool   `json:"tls_verify"`
	LastSavePath string `json:"last_save_path"`
}

func Load(baseDir string) (*Config, error) {
	configFile := filepath.Join(baseDir, "data", "config.json")
	
	data, err := os.ReadFile(configFile)
	if err != nil {
		if os.IsNotExist(err) {
			return &Config{Theme: "light"}, nil
		}
		return nil, err
	}
	
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	
	return &cfg, nil
}

func (c *Config) Save(baseDir string) error {
	dataDir := filepath.Join(baseDir, "data")
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return err
	}
	
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	
	configFile := filepath.Join(dataDir, "config.json")
	return os.WriteFile(configFile, data, 0644)
}