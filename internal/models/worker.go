package models

import "time"

type Worker struct {
	ID             string    `json:"id"`
	LastName       string    `json:"last_name"`
	FirstName      string    `json:"first_name"`
	MiddleName     string    `json:"middle_name"`
	SNILS         string    `json:"snils"`
	Position      string    `json:"position"`
	EmployerINN   string    `json:"employer_inn"`
	EmployerTitle string    `json:"employer_title"`
	TCINN        string    `json:"tc_inn"`
	TCTitle      string    `json:"tc_title"`
	Result        string    `json:"result"`
	Program      string    `json:"program"`
	Date         string    `json:"date"`
	Protocol     string    `json:"protocol"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type Organization struct {
	TCINN         string `json:"tc_inn"`
	TCTitle       string `json:"tc_title"`
	EmployerINN   string `json:"employer_inn"`
	EmployerTitle string `json:"employer_title"`
}

type ExamJournal struct {
	ID              string    `json:"id"`
	SendDate        time.Time `json:"send_date"`
	SetID          string    `json:"set_id"`
	LastName       string    `json:"last_name"`
	FirstName      string    `json:"first_name"`
	MiddleName     string    `json:"middle_name"`
	SNILS         string    `json:"snils"`
	Position      string    `json:"position"`
	Program        string    `json:"program"`
	ProgramTitle   string    `json:"program_title"`
	ExamDate      string    `json:"exam_date"`
	Protocol      string    `json:"protocol"`
	Result        string    `json:"result"`
	Status        string    `json:"status"` // "ожидает", "получен"
	BaseNo        string    `json:"base_no"` // регистрационный номер
}

type Commission struct {
	OrgName       string `json:"org_name"`
	ProtocolNo    string `json:"protocol_no"`
	ExamDate     string `json:"exam_date"`
	OrderNo      string `json:"order_no"`
	OrderDate    string `json:"order_date"`
	Chairperson  string `json:"chairperson"`
	ChairTitle  string `json:"chair_title"`
	Member1     string `json:"member1"`
	Member1Title string `json:"member1_title"`
	Member2     string `json:"member2"`
	Member2Title string `json:"member2_title"`
	Member3     string `json:"member3"`
	Member3Title string `json:"member3_title"`
	TradeUnion  string `json:"trade_union"`
	TradeTitle  string `json:"trade_title"`
}

type Program struct {
	Number      string `json:"number"`
	Title      string `json:"title"`
	DocNo      string `json:"doc_no"`
	Hours      int    `json:"hours"`
}

var ValidPrograms = map[string]string{
	"1":  "Оказание первой помощи пострадавшим",
	"2":  "Использование (применение) средств индивидуальной защиты",
	"3":  "Общие вопросы охраны труда и функционирования системы управления охраной труда",
	"4":  "Безопасные методы и приемы выполнения работ при воздействии вредных и (или) опасных производственных факторов",
	"6":  "Безопасные методы и приемы выполнения земляных работ",
	"7":  "Без��пасные методы и приемы выполнения ремонтных, монтажных и демонтажных работ зданий и сооружений",
	"8":  "Безопасные методы и приемы выполнения работ при размещении, монтаже, техническом обслуживании и ремонте технологического оборудования",
	"9":  "Безопасные методы и приемы выполнения работ на высоте",
	"10": "Безопасные методы и приемы выполнения пожароопасных работ",
	"11": "Безопасные методы и приемы выполнения работ в ограниченных и замкнутых пространствах (ОЗП)",
	"12": "Безопасные методы и приемы выполнения строительных работ",
	"13": "Безопасные методы и приемы выполнения работ, связанных с опасностью воздействия сильнодействующих и ядовитых веществ",
	"14": "Безопасные методы и приемы выполнения газоопасных работ",
	"15": "Безопасные методы и приемы выполнения огневых работ",
	"16": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией подъемных сооружений",
	"17": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией тепловых энергоустановок",
	"18": "Безопасные методы и приемы выполнения работ в электроустановках",
	"19": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией сосудов, работающих под избыточным давлением",
	"20": "Безопасные методы и приемы обращения с животными",
	"21": "Безопасные методы и приемы при выполнении водолазных работ",
	"22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
	"23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
	"24": "Безопасные методы и приемы работ, на участках с патогенным заражением почвы",
	"25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
	"26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов",
	"27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
	"28": "Безопасные методы и приемы работ с ручным инструментом, в том числе с пиротехническим",
	"29": "Безопасные методы и приемы ��абот в театрах",
}