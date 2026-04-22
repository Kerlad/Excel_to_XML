package importer

import (
	"excel-xml-mintrud/internal/models"
	"github.com/xuri/excelize/v2"
	"strconv"
	"strings"
	"time"
)

type Importer struct{}

func NewImporter() *Importer {
	return &Importer{}
}

type ImportResult struct {
	Workers     []models.Worker
	Errors      []ImportError
	ErrorCount  int
}

type ImportError struct {
	Row      int    `json:"row"`
	Type    string `json:"type"`
	Field   string `json:"field"`
	Message string `json:"message"`
}

func (imp *Importer) LoadXLSX(filePath string, defaultOrg *models.Organization) (*ImportResult, error) {
	f, err := excelize.OpenFile(filePath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	rows, err := f.GetRows(f.GetSheetName(0))
	if err != nil {
		return nil, err
	}

	result := &ImportResult{
		Workers: []models.Worker{},
		Errors:  []ImportError{},
	}

	if len(rows) < 2 {
		result.Errors = append(result.Errors, ImportError{
			Row:      1,
			Type:    "Ошибка",
			Field:   "",
			Message: "Файл не содержит данных",
		})
		result.ErrorCount = 1
		return result, nil
	}

	headers := normalizeHeaders(rows[0])
	required := []string{"Фамилия", "Имя", "Отчество", "СНИЛС", "Должность", "Результат", "№ программы", "Дата", "№ протокола"}
	for _, req := range required {
		if !contains(headers, req) {
			result.Errors = append(result.Errors, ImportError{
				Row:      1,
				Type:    "Ошибка",
				Field:   req,
				Message: "Отсутствует обязательный столбец",
			})
			result.ErrorCount++
		}
	}

	for rowNum := 2; rowNum <= len(rows); rowNum++ {
		row := rows[rowNum-1]
		if len(row) < len(headers) {
			continue
		}

		rowData := map[string]string{}
		for i, h := range headers {
			if i < len(row) {
				rowData[h] = getCellValue(row, i)
			}
		}

		isEmpty := true
		for _, v := range rowData {
			if v != "" {
				isEmpty = false
				break
			}
		}
		if isEmpty {
			continue
		}

		errs := imp.validateRow(rowData, rowNum, defaultOrg)
		if len(errs) > 0 {
			result.Errors = append(result.Errors, errs...)
			result.ErrorCount += len(errs)
			continue
		}

		workers := imp.parseRow(rowData, defaultOrg, rowNum)
		result.Workers = append(result.Workers, workers...)
	}

	return result, nil
}

func (imp *Importer) validateRow(row map[string]string, rowNum int, defaultOrg *models.Organization) []ImportError {
	var errs []ImportError

	required := []string{"Фамилия", "Имя", "Отчество", "СНИЛС", "Должность", "Результат", "№ программы", "Дата", "№ протокола"}
	for _, field := range required {
		if val := row[field]; val == "" {
			errs = append(errs, ImportError{
				Row:      rowNum,
				Type:    "Ошибка",
				Field:   field,
				Message: "Пустое обязательное поле",
			})
		}
	}

	if snils := row["СНИЛС"]; snils != "" {
		if formatted := formatSNILS(snils); formatted == "" {
			errs = append(errs, ImportError{
				Row:      rowNum,
				Type:    "Ошибка",
				Field:   "СНИЛС",
				Message: "СНИЛС должен содержать 11 цифр",
			})
		}
	}

	programStr := row["№ программы"]
	programs := strings.Split(strings.Trim(programStr, ","), ",")
	for _, p := range programs {
		p = strings.TrimSpace(p)
		if p != "" && !isValidProgram(p) {
			errs = append(errs, ImportError{
				Row:      rowNum,
				Type:    "Ошибка",
				Field:   "№ программы",
				Message: "Некорректный номер программы: " + p,
			})
		}
	}

	result := row["Результат"]
	if result != "Удовлетворительно" && result != "Неудовлетворительно" {
		errs = append(errs, ImportError{
			Row:      rowNum,
			Type:    "Ошибка",
			Field:   "Результат",
			Message: "Результат должен быть 'Удовлетворительно' или 'Неудовлетворительно'",
		})
	}

	return errs
}

func (imp *Importer) parseRow(row map[string]string, defaultOrg *models.Organization, rowNum int) []models.Worker {
	snils := formatSNILS(row["СНИЛС"])
	programStr := row["№ программы"]
	programs := strings.Split(strings.Trim(programStr, ","), ",")
	
	employerINN := row["ИНН Заказчика"]
	employerTitle := row["Наименование ЮЛ Заказчика"]
	tcINN := row["ИНН УЦ"]
	tcTitle := row["Наименование УЦ"]
	
	if defaultOrg != nil {
		if employerINN == "" {
			employerINN = defaultOrg.EmployerINN
		}
		if employerTitle == "" {
			employerTitle = defaultOrg.EmployerTitle
		}
		if tcINN == "" {
			tcINN = defaultOrg.TCINN
		}
		if tcTitle == "" {
			tcTitle = defaultOrg.TCTitle
		}
	}
	
	var workers []models.Worker
	for _, prog := range programs {
		prog = strings.TrimSpace(prog)
		if prog == "" {
			continue
		}
		
		w := models.Worker{
			ID:             generateID(),
			LastName:       row["Фамилия"],
			FirstName:      row["Имя"],
			MiddleName:     row["Отчество"],
			SNILS:         snils,
			Position:      row["Должность"],
			EmployerINN:   employerINN,
			EmployerTitle: employerTitle,
			TCINN:        tcINN,
			TCTitle:      tcTitle,
			Result:        row["Результат"],
			Program:      prog,
			Date:         row["Дата"],
			Protocol:     row["№ протокола"],
			CreatedAt:    time.Now(),
			UpdatedAt:    time.Now(),
		}
		workers = append(workers, w)
	}
	
	return workers
}

func normalizeHeaders(headers []string) []string {
	var normalized []string
	for _, h := range headers {
		normalized = append(normalized, strings.TrimSpace(h))
	}
	return normalized
}

func getCellValue(row []string, idx int) string {
	if idx >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[idx])
}

func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

func formatSNILS(raw string) string {
	clean := strings.ReplaceAll(raw, "-", "")
	clean = strings.ReplaceAll(clean, " ", "")
	clean = strings.TrimSpace(clean)
	
	if len(clean) != 11 {
		return ""
	}
	
	for _, c := range clean {
		if c < '0' || c > '9' {
			return ""
		}
	}
	
	return clean[0:3] + "-" + clean[3:6] + "-" + clean[6:9] + " " + clean[9:11]
}

func isValidProgram(p string) bool {
	valid := map[string]bool{
		"1": true, "2": true, "3": true, "4": true,
		"6": true, "7": true, "8": true, "9": true,
		"10": true, "11": true, "12": true, "13": true,
		"14": true, "15": true, "16": true, "17": true,
		"18": true, "19": true, "20": true, "21": true,
		"22": true, "23": true, "24": true, "25": true,
		"26": true, "27": true, "28": true, "29": true,
	}
	return valid[p]
}

func generateID() string {
	return strconv.FormatInt(time.Now().UnixNano(), 10)
}