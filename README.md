# CODEBA — Dashboard de Auditoria de Pesagens (v4.0.0)

Este projeto realiza a **conciliação e auditoria de pesagens rodoviárias** comparando as planilhas da CODEBA (origem Excel, digitação manual do balanceiro) com os registros do OpenPort (PDF, pesagem automática). Ele identifica automaticamente divergências de peso, placas digitadas incorretamente no Excel, deduz o produto com base no histórico do caminhão e gera relatórios analíticos com gráficos de volume.

---

## Funcionalidades

- **Upload multi-arquivo:** Arraste planilhas `.xlsx` + relatório OpenPort `.pdf` de uma vez
- **Conciliação automática:** cruza pesagens do Excel com o PDF, aponta OK vs divergências
- **Desduplicação inteligente:** remove registros duplicados do OpenPort antes da análise
- **Analytics dinâmico:** gráficos de barras empilhadas (toneladas por produto/data), donut de distribuição e KPIs
- **Filtros reativos:** período (Flatpickr com presets), placa (debounce), produto, toggle auditado/total
- **Agrupamento semanal:** para períodos > 90 dias, eixo X agrupa por semana
- **Histórico persistente:** cada auditoria salva em SQLite, consultável e recarregável
- **Relatório PDF:** download com filtros ativos aplicados
- **Temas Claro/Escuro** com identidade visual CODEBA
- **Suporte a Tela 7714** do OpenPort (novo formato de relatório)

---

## Estrutura do Projeto

```
operacao/
├── pyproject.toml              # Metadados e config de ferramentas (PEP 518)
├── .gitignore
├── .env.example                # Config de ambiente (12-Factor App)
├── requirements.txt            # Dependências legacy
├── README.md
│
├── src/                        # Código-fonte principal
│   ├── app.py                  # FastAPI: rotas, upload, histórico, lifespan SQLite
│   ├── config.py               # Paths, limites de upload
│   ├── logging_config.py       # Logs centralizados
│   │
│   ├── services/
│   │   ├── excel_parser.py     # Header Hunting nas primeiras 20 linhas
│   │   ├── pdf_parser.py       # Extração PDF + desduplicação de pesagens
│   │   ├── reconciliation.py   # Motor de conciliação + volume no resultado
│   │   ├── post_processing.py  # Erros de placa + dedução de produto por histórico
│   │   ├── analytics.py        # build_volume_records() — toneladas por viagem
│   │   ├── persistence.py      # SQLite: CRUD de audit_runs
│   │   └── report_generator.py # Geração de relatório PDF com reportlab
│   │
│   └── utils/
│       ├── cleaners.py         # Limpeza de placas, decimais BR (safe_to_numeric)
│       ├── filename_parser.py  # Extração de produto/cliente do nome do arquivo
│       └── file_utils.py       # Cleanup de arquivos temporários com retry (Windows)
│
├── static/                     # Frontend (HTML, CSS, JS puro)
│   ├── index.html
│   ├── bg-ilheus.png           # Background image (foto aérea do Porto)
│   ├── css/
│   │   ├── style.css           # Design system CODEBA
│   │   └── responsive.css      # Breakpoints mobile/tablet
│   └── js/
│       ├── app.js              # Orquestração, upload, KPIs, tabelas
│       ├── analytics.js        # filterState, applyFilters(), aggregateVolume()
│       ├── charts.js           # Wrappers Chart.js (barras empilhadas + donut)
│       └── history.js          # Painel de histórico, fetch /api/runs
│
├── data/                       # Dados de referência (gitignored)
│   └── auditoria.db            # SQLite — gerado em runtime
│
├── tests/
│   ├── conftest.py             # Fixture TestClient com lifespan
│   ├── test_e2e.py             # Upload completo, frontend, API histórico
│   ├── test_analytics.py       # Normalização produto, volume, período
│   ├── test_persistence.py     # CRUD do SQLite
│   ├── test_report.py          # Geração de relatório PDF
│   └── test_deduplication.py   # Desduplicação de pesagens
│
├── scratch/                    # Scripts de teste standalone (offline)
│   ├── run_e2e_tests.py
│   └── run_all_tests.py
│
├── scripts/
│   └── rpa_codeba.py           # Robô RPA (Playwright) para download do relatório
│
├── docs/
│   ├── memory.md               # Memória do projeto (histórico de decisões)
│   ├── guia.md                 # Guia do usuário
│   ├── automacao.md            # Roteiro do RPA
│   ├── dados-openport.md       # Contexto dos dados OpenPort
│   └── ideia.md                # Concepção original
│
├── logs/                       # Logs de execução
└── temp_uploads/               # Arquivos temporários de upload
```

---

## Como Executar

### 1. Preparar o Ambiente

Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
copy .env.example .env       # Windows
```

Edite `.env` se necessário (OPENPORT_USER, OPENPORT_PASS para o RPA).

### 2. Iniciar o Servidor

```bash
python -m uvicorn src.app:app --reload --port 8000
```

Acesse **http://localhost:8000**

---

## Testes

```bash
python -m pytest tests/ -v
```

23 testes cobrindo upload E2E, analytics, persistência, relatório PDF e desduplicação.

---

## Variáveis de Ambiente (`.env`)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `HOST` | `127.0.0.1` | Host do servidor |
| `PORT` | `8000` | Porta |
| `DATABASE_PATH` | `data/auditoria.db` | Banco SQLite |
| `UPLOAD_DIR` | `temp_uploads` | Uploads temporários |
| `MAX_FILE_SIZE_MB` | `50` | Limite por arquivo |
| `OPENPORT_USER` | — | CPF do operador (RPA) |
| `OPENPORT_PASS` | — | Senha do operador (RPA) |
| `RPA_DOWNLOAD_DIR` | — | Diretório de download do RPA |

---

## Segurança

- **Path Traversal:** uploads salvos com nome `uuid4()`
- **XSS:** renderização via `.textContent`/`.appendChild`, sem `innerHTML`
- **Validação:** rejeita arquivos > 50 MB ou extensões fora da allow-list (`.xlsx`, `.xls`, `.pdf`)
- **Cleanup:** remoção sistemática com retry progressivo (5×) para lidar com locks do Windows
- **Credenciais:** credenciais do OpenPort lidas de variáveis de ambiente, nunca hardcoded
