package main

import (
	"excel-xml-mintrud/internal/api"
	"excel-xml-mintrud/internal/config"
	"excel-xml-mintrud/internal/exporter"
	"excel-xml-mintrud/internal/importer"
	"excel-xml-mintrud/internal/models"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

var (
	baseDir   string
	cfg       *config.Config
	imp       *importer.Importer
	exp       *exporter.Exporter
	mintrudAPI *api.MintrudAPI
	workers   []models.Worker
)

func main() {
	log.Println("=== Excel-XML для передачи данных в Минтруд ===")

	baseDir = getBaseDir()
	cfg, _ = config.Load(baseDir)

	imp = importer.NewImporter()
	exp = exporter.NewExporter()
	mintrudAPI = api.NewMintrudAPI()

	workers = loadData()

	fmt.Printf("Директория: %s\n", baseDir)
	fmt.Printf("Загружено работников: %d\n", len(workers))
	fmt.Println("\nЗапуск веб-интерфейса на http://localhost:8080")
	fmt.Println("Нажмите Ctrl+C для выхода")

	http.HandleFunc("/", handleIndex)
	http.HandleFunc("/api/org", handleOrg)
	http.HandleFunc("/api/workers", handleWorkers)
	http.HandleFunc("/api/worker/add", handleWorkerAdd)
	http.HandleFunc("/api/excel/load", handleExcelLoad)
	http.HandleFunc("/api/xml/export", handleXMLExport)
	http.HandleFunc("/api/xml/push", handleXMLPush)
	http.HandleFunc("/api/setid/query", handleSetIdQuery)
	http.HandleFunc("/api/snils/query", handleSnilsQuery)
	http.HandleFunc("/api/proxy/save", handleProxySave)

	err := http.ListenAndServe(":8080", nil)
	if err != nil {
		log.Fatal(err)
	}
}

func getBaseDir() string {
	exePath, _ := os.Executable()
	dir := filepath.Dir(exePath)
	if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
		return dir
	}
	if _, err := os.Stat(filepath.Join(".", "go.mod")); err == nil {
		return "."
	}
	return dir
}

func loadData() []models.Worker {
	file := filepath.Join(baseDir, "data", "workers.json")
	data, err := os.ReadFile(file)
	if err != nil {
		return nil
	}
	var w []models.Worker
	json.Unmarshal(data, &w)
	return w
}

func saveWorkersData() {
	dataDir := filepath.Join(baseDir, "data")
	os.MkdirAll(dataDir, 0755)
	data, _ := json.MarshalIndent(workers, "", "  ")
	file := filepath.Join(dataDir, "workers.json")
	os.WriteFile(file, data, 0644)
}

func handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}

	htmlPath := filepath.Join(baseDir, "frontend", "index.html")
	data, err := os.ReadFile(htmlPath)
	if err != nil {
		http.Error(w, "GUI not found", 500)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(data)
}

func handleOrg(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	if r.Method == "POST" {
		var org models.Organization
		json.NewDecoder(r.Body).Decode(&org)

		cfg.TCINN = org.TCINN
		cfg.TCTitle = org.TCTitle
		cfg.EmployerINN = org.EmployerINN
		cfg.EmployerTitle = org.EmployerTitle
		cfg.Save(baseDir)

		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		return
	}

	json.NewEncoder(w).Encode(cfg)
}

func handleWorkers(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(workers)
}

func handleWorkerAdd(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	var worker models.Worker
	json.NewDecoder(r.Body).Decode(&worker)

	workers = append(workers, worker)
	saveWorkersData()

	json.NewEncoder(w).Encode(map[string]int{"count": len(workers)})
}

func handleExcelLoad(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	body, _ := io.ReadAll(r.Body)
	var req struct{ Path string }
	json.Unmarshal(body, &req)

	org := &models.Organization{
		TCINN:         cfg.TCINN,
		TCTitle:       cfg.TCTitle,
		EmployerINN:   cfg.EmployerINN,
		EmployerTitle: cfg.EmployerTitle,
	}

	result, err := imp.LoadXLSX(req.Path, org)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{"error": err.Error()})
		return
	}

	workers = append(workers, result.Workers...)
	saveWorkersData()

	json.NewEncoder(w).Encode(map[string]interface{}{
		"count":     len(result.Workers),
		"errors":    result.ErrorCount,
		"total":    len(workers),
	})
}

func handleXMLExport(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	body, _ := io.ReadAll(r.Body)
	var req struct{ Path string }
	json.Unmarshal(body, &req)

	org := &models.Organization{
		TCINN:         cfg.TCINN,
		TCTitle:       cfg.TCTitle,
		EmployerINN:   cfg.EmployerINN,
		EmployerTitle: cfg.EmployerTitle,
	}

	data, err := exp.ExportXML(workers, org, "")
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{"error": err.Error()})
		return
	}

	exp.SaveXML(data, req.Path)

	json.NewEncoder(w).Encode(map[string]string{"path": req.Path})
}

func handleXMLPush(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	body, _ := io.ReadAll(r.Body)
	var req struct {
		Path  string
		APIKey string
	}
	json.Unmarshal(body, &req)

	xmlData, err := os.ReadFile(req.Path)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{"error": err.Error()})
		return
	}

	resp, err := mintrudAPI.PushXML(xmlData, req.APIKey)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{"error": err.Error()})
		return
	}

	json.NewEncoder(w).Encode(resp)
}

func handleSetIdQuery(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	body, _ := io.ReadAll(r.Body)
	var req struct {
		SetID  string
		APIKey string
	}
	json.Unmarshal(body, &req)

	result, err := mintrudAPI.GetBySetID(req.SetID, req.APIKey)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{"error": err.Error()})
		return
	}

	json.NewEncoder(w).Encode(result)
}

func handleSnilsQuery(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	body, _ := io.ReadAll(r.Body)
	var req struct {
		SNILS  string
		APIKey string
	}
	json.Unmarshal(body, &req)

	snils := strings.ReplaceAll(req.SNILS, "-", "")
	snils = strings.ReplaceAll(snils, " ", "")

	result, err := mintrudAPI.GetBySNILS(snils, req.APIKey)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{"error": err.Error()})
		return
	}

	json.NewEncoder(w).Encode(result)
}

func handleProxySave(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	var proxy struct {
		ProxyType string
		ProxyURL string
		TLSVerify bool
	}
	json.NewDecoder(r.Body).Decode(&proxy)

	cfg.ProxyType = proxy.ProxyType
	cfg.ProxyURL = proxy.ProxyURL
	cfg.TLSVerify = proxy.TLSVerify
	cfg.Save(baseDir)

	mintrudAPI.Proxy.Type = proxy.ProxyType
	mintrudAPI.Proxy.URL = proxy.ProxyURL
	mintrudAPI.TLSVerify = proxy.TLSVerify

	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}