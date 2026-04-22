package exporter

import (
	"bytes"
	"encoding/xml"
	"excel-xml-mintrud/internal/models"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type Exporter struct{}

func NewExporter() *Exporter {
	return &Exporter{}
}

func (e *Exporter) ExportXML(workers []models.Worker, org *models.Organization, xsdPath string) ([]byte, error) {
	doc := e.buildDocument(workers, org)

	if xsdPath != "" {
		if err := e.validateXSD(doc, xsdPath); err != nil {
			return nil, fmt.Errorf("валидация по XSD: %w", err)
		}
	}

	var buf bytes.Buffer
	enc := xml.NewEncoder(&buf)
	enc.Indent("  ", "  ")

	if err := enc.Encode(doc); err != nil {
		return nil, err
	}

	xmlData := buf.Bytes()
	header := []byte(xmlHeader)
	xmlData = append(header, xmlData...)
	return xmlData, nil
}

func (e *Exporter) buildDocument(workers []models.Worker, org *models.Organization) *XMLDocument {
	doc := &XMLDocument{
		XMLNs:        "http://mintrud.gov.ru/sout/import",
		Version:     "1.0",
		SendDate:    time.Now().Format("02.01.2006"),
		EducationInfo: &EducationInfo{},
	}

	if org != nil {
		doc.EducationInfo.TrainingCenter = &OrgInfo{
			INN:  org.TCINN,
			Name: org.TCTitle,
		}
		doc.EducationInfo.Employer = &OrgInfo{
			INN:  org.EmployerINN,
			Name: org.EmployerTitle,
		}
	}

	doc.EducationInfo.EducatedPersons = &EducatedPersons{}

	grouped := groupBySNILS(workers)
	for snils, workerList := range grouped {
		w := workerList[0]

		ep := &EducatedPerson{
			SNILS:        snils,
			LastName:    w.LastName,
			FirstName:   w.FirstName,
			MiddleName:  w.MiddleName,
			Position:    w.Position,
			Employer:   &OrgInfo{INN: w.EmployerINN, Name: w.EmployerTitle},
		}

		for _, worker := range workerList {
			exam := &Examination{
				Number:    worker.Program,
				Result:   worker.Result,
				ExamDate: worker.Date,
				Protocol: worker.Protocol,
				DocDate:  worker.Date,
			}
			if title, ok := models.ValidPrograms[worker.Program]; ok {
				exam.ProgramName = title
			}
			ep.Examinations = append(ep.Examinations, exam)
		}

		doc.EducationInfo.EducatedPersons.EducatedPerson = append(
			doc.EducationInfo.EducatedPersons.EducatedPerson, ep,
		)
	}

	return doc
}

func groupBySNILS(workers []models.Worker) map[string][]models.Worker {
	groups := make(map[string][]models.Worker)
	for _, w := range workers {
		groups[w.SNILS] = append(groups[w.SNILS], w)
	}
	return groups
}

func (e *Exporter) SaveXML(data []byte, filePath string) error {
	dir := filepath.Dir(filePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	return os.WriteFile(filePath, data, 0644)
}

func (e *Exporter) CreateTemplate(filePath string) error {
	f, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer f.Close()
	return nil
}

func (e *Exporter) validateXSD(doc *XMLDocument, xsdPath string) error {
	return nil
}

const xmlHeader = `<?xml version="1.0" encoding="UTF-8"?>
`

type XMLDocument struct {
	XMLName       xml.Name       `xml:"EducatedPersonsArchive"`
	XMLNs        string        `xml:"xmlns,attr"`
	Version     string        `xml:"Version"`
	SendDate    string        `xml:"SendDate"`
	EducationInfo *EducationInfo `xml:"EducationInfo"`
}

type EducationInfo struct {
	TrainingCenter   *OrgInfo            `xml:"TrainingCenter"`
	Employer       *OrgInfo            `xml:"Employer"`
	EducatedPersons *EducatedPersons    `xml:"EducatedPersons"`
}

type OrgInfo struct {
	INN  string `xml:"INN"`
	Name string `xml:"Name"`
}

type EducatedPersons struct {
	EducatedPerson []*EducatedPerson `xml:"EducatedPerson"`
}

type EducatedPerson struct {
	XMLName      xml.Name       `xml:"EducatedPerson"`
	SNILS        string        `xml:"SNILS"`
	LastName    string        `xml:"LastName"`
	FirstName   string        `xml:"FirstName"`
	MiddleName  string        `xml:"MiddleName"`
	Position    string        `xml:"Position"`
	Employer   *OrgInfo       `xml:"Employer"`
	Examinations []*Examination `xml:"Examination"`
}

type Examination struct {
	XMLName     xml.Name `xml:"Examination"`
	Number      string  `xml:"Number"`
	ProgramName string  `xml:"ProgramName"`
	Result     string  `xml:"Result"`
	ExamDate   string  `xml:"ExamDate"`
	DocDate    string  `xml:"DocDate"`
	Protocol   string  `xml:"Protocol"`
}