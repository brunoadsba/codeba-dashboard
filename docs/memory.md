# Memória do Projeto (CODEBA Dashboard de Auditoria)

**Estado Atual:** Sistema de Auditoria de Pesagens **v3.2.0** — Multi-Produto com Analytics Dinâmico, Persistência SQLite, Histórico Consultável e Identidade Visual CODEBA.

Dashboard cruza dados de múltiplas planilhas Excel (digitação manual do balanceiro, organizadas por produto) com o PDF do OpenPort (pesagem automática) para identificar divergências, propagar informação de produto, deduzir associações por histórico de placas e visualizar **volume em toneladas** por produto e período. A aplicação segue Clean Architecture e 12-Factor App.

---

## Base de Conhecimento Primária: OpenPort (PDF)

> **O relatório do OpenPort (PDF) é a fonte de verdade primária do sistema.**
> Ele contém TODAS as pesagens (SEVs) de TODAS as cargas que passaram pela balança — independentemente do tipo de produto (Lítio, Óxido de Magnésio, Manganês, Milho, Níquel, etc.).
>
> Os dados do Excel são a fonte **secundária** e servem como registro manual de controle feito pelo balanceiro, organizado por produto/cliente. O Excel pode conter erros de digitação, faltas ou dados incompletos.
>
> **Hierarquia de confiança:**
> 1. **OpenPort (PDF)** — dados automáticos do sistema de pesagem → máxima confiança
> 2. **Excel (Planilhas)** — dados manuais do balanceiro → sujeitos a erro humano
>
> Quando há conflito entre os dados, o OpenPort prevalece como referência.

---

## O que foi construído?

Ecossistema para a CODEBA contendo:

1. **Dashboard de Auditoria de Pesagens (Multi-Produto):** Painel web que recebe múltiplos `.xlsx` e `.pdf`, concilia automaticamente, exibe divergências, conformidade por produto e gráficos de tonelagem dinâmicos.
2. **Persistência e Histórico:** Cada auditoria processada é salva em SQLite; o usuário pode consultar e recarregar auditorias anteriores sem reenviar arquivos.
3. **Robô de Automação (RPA):** `scripts/rpa_codeba.py` com Playwright para coleta do relatório 7015 no OpenPort Ilhéus.
4. **Suite de Testes:** Pytest + FastAPI `TestClient` — 14 testes cobrindo E2E, analytics, persistência e frontend.

---

## Arquitetura Modular (v3.1.0)

### Backend (`src/`)

| Módulo | Responsabilidade |
|--------|------------------|
| `app.py` | FastAPI: upload, histórico (`/api/runs`), lifespan SQLite |
| `config.py` | Paths, `DATABASE_PATH`, limites de upload |
| `logging_config.py` | Logs centralizados em `logs/app.log` |
| `services/excel_parser.py` | Header Hunting nas primeiras 20 linhas |
| `services/pdf_parser.py` | Extração PDF via `pdfplumber` |
| `services/reconciliation.py` | Motor de conciliação + `volume` no resultado |
| `services/post_processing.py` | Erros de placa + dedução de produto por histórico |
| `services/analytics.py` | `build_volume_records()` — toneladas por viagem/produto/data |
| `services/persistence.py` | SQLite: save/list/get/delete de `audit_runs` |
| `utils/cleaners.py` | Placas, decimais BR (`safe_to_numeric`) |
| `utils/filename_parser.py` | Produto e cliente a partir do nome do arquivo |

### Frontend (`static/`)

| Arquivo | Responsabilidade |
|---------|------------------|
| `index.html` | Upload + dashboard + drawer de histórico + popover de datas |
| `js/app.js` | Orquestração, tabelas, KPIs, upload, export CSV |
| `js/analytics.js` | `filterState`, `applyFilters()`, `aggregateVolume()` |
| `js/charts.js` | Wrappers Chart.js (barras empilhadas + donut) |
| `js/history.js` | Painel de histórico, fetch `/api/runs` |
| `css/style.css` | Design system v2 + analytics + histórico |
| `css/responsive.css` | Breakpoints mobile/tablet |

**Dependências CDN:** Chart.js 4, Flatpickr (pt-BR), Phosphor Icons, Inter.

---

## API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/` | Serve `index.html` |
| `POST` | `/api/upload` | Processa arquivos, persiste, retorna auditoria |
| `GET` | `/api/runs` | Lista auditorias (`?limit=20&offset=0`) |
| `GET` | `/api/runs/{id}` | Payload completo de uma auditoria |
| `DELETE` | `/api/runs/{id}` | Remove auditoria do histórico |

### Resposta do upload (campos principais)

```json
{
  "run_id": "uuid",
  "created_at": "2026-06-08T14:30:00+00:00",
  "resumo": { "total_processado": 13, "ok": 13, "divergencias": 0 },
  "ok": [ /* registros conciliados */ ],
  "divergencias": [ /* divergências */ ],
  "produtos_detectados": ["LITIO", "ÓXIDO DE MAGNÉSIO"],
  "clientes_por_produto": { "LITIO": ["Cliente A"] },
  "volume": {
    "records": [
      {
        "data": "05/06/2026",
        "produto": "LITIO",
        "toneladas": 38.3,
        "viagens": 1,
        "is_ok": true,
        "placa": "PFI5E14"
      }
    ],
    "meta": { "unidade": "toneladas", "fonte_peso": "Peso Liquido / Bruto-Tara" }
  }
}
```

### Campos de registro OK

`Placa`, `Data` (DD/MM/YYYY), `Peso Bruto`, `Tara`, `Peso Liquido`, `Produto`, `Cliente`, `Detalhe`

### Campos de divergência

`Placa`, `Data`, `Status`, `Detalhe`, `Produto`, `Cliente`, `Peso Bruto`, `Tara`  
Status possíveis: `Diferença de Peso`, `Falta no PDF`, `Falta no Excel`, `Erro de Placa` (com `Placa_Excel` / `Placa_PDF`)

---

## Analytics Dinâmico (v3.1)

### Visualizações

- **Barras empilhadas:** toneladas por data, empilhadas por produto (Chart.js)
- **Donut:** distribuição percentual de toneladas por produto no período
- **KPI Volume Total:** soma de toneladas conforme filtros ativos
- **Conformidade por produto:** barras CSS OK vs divergências (herdado v3.0)

### Filtros reativos (client-side)

Objeto central `filterState` em `analytics.js`:

```javascript
{ dateStart, dateEnd, placa, produto, volumeScope: 'ok' | 'all' }
```

- **Período no topo:** badge clicável → Flatpickr range + presets (Hoje, 7d, 30d, Tudo)
- **Barra de filtros:** placa (debounce 250ms), produto, data única (atalho que sincroniza o range)
- **Toggle volume:** `ok` = apenas pesagens auditadas; `all` = inclui divergências com peso calculável
- **Badge de período:** reflete o subset filtrado, não o dataset completo
- Períodos > 90 dias: agrupamento automático por semana no eixo X

### Persistência SQLite

- Banco: `data/auditoria.db` (configurável via `DATABASE_PATH`)
- Tabela `audit_runs`: payload JSON completo + metadados (período, arquivos, resumo)
- `init_db()` no startup FastAPI; `_ensure_db()` defensivo em cada operação
- Arquivo ignorado no `.gitignore`

### Histórico (UI)

- Botão **Histórico** na topbar → drawer (desktop) / bottom sheet (mobile)
- Lista runs com data, período, resumo OK/div, nomes dos arquivos
- **Carregar** restaura dashboard completo; **Excluir** com confirmação

---

## Como Rodar

```powershell
cd operacao
.\.venv\Scripts\Activate.ps1
python -m uvicorn src.app:app --reload --port 8000
```

Acesse: **http://localhost:8000**

### Variáveis de ambiente (`.env.example`)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `HOST` | `127.0.0.1` | Host do servidor |
| `PORT` | `8000` | Porta |
| `DATABASE_PATH` | `data/auditoria.db` | Banco SQLite |
| `UPLOAD_DIR` | `temp_uploads` | Uploads temporários |
| `MAX_FILE_SIZE_MB` | `50` | Limite por arquivo |

---

## Estrutura de Diretórios

```
operacao/
├── pyproject.toml
├── .env.example
├── requirements.txt
│
├── src/
│   ├── app.py
│   ├── config.py
│   ├── logging_config.py
│   ├── services/
│   │   ├── excel_parser.py
│   │   ├── pdf_parser.py
│   │   ├── reconciliation.py
│   │   ├── post_processing.py
│   │   ├── analytics.py          # v3.1
│   │   └── persistence.py      # v3.1
│   └── utils/
│       ├── cleaners.py
│       └── filename_parser.py
│
├── static/
│   ├── index.html
│   ├── css/
│   │   ├── style.css
│   │   └── responsive.css        # v3.1
│   └── js/
│       ├── app.js
│       ├── analytics.js          # v3.1
│       ├── charts.js             # v3.1
│       └── history.js            # v3.1
│
├── data/
│   ├── excel/
│   ├── relatorios/
│   └── auditoria.db              # gerado em runtime (gitignored)
│
├── tests/
│   ├── conftest.py               # fixture TestClient com lifespan
│   ├── test_e2e.py
│   ├── test_analytics.py         # v3.1
│   └── test_persistence.py       # v3.1
│
├── scripts/
│   ├── rpa_codeba.py
│   └── diagnostics/
│
├── logs/
└── temp_uploads/
```

---

## Suite de Testes

**Comando:** `python -m pytest tests/ -v`  
**Total:** 14 testes

| Arquivo | Cobertura |
|---------|-----------|
| `test_e2e.py` | Upload completo, só PDF, frontend + API histórico + `volume` |
| `test_analytics.py` | Normalização produto, peso líquido, `build_volume_records`, período |
| `test_persistence.py` | Save/load, listagem, delete, init do banco |

O `TestClient` usa fixture com `with TestClient(app)` para disparar o lifespan e inicializar o SQLite.

---

## Fluxo de Dados (v3.1)

```
Upload → reconcile_data() → build_volume_records()
       → save_audit_run() → SQLite
       → JSON (ok + divergencias + volume + run_id)
       → globalAuditData (frontend)
       → applyFilters() → aggregateVolume() → Chart.js + KPIs + tabelas
```

Recarregar do histórico: `GET /api/runs/{id}` → mesmo pipeline de renderização, sem re-upload.

---

## Lições Aprendidas e Bugs Resolvidos

### v3.0

1. **Header Hunting & Sujeira:** busca dinâmica de linha com "PLACA" + ("PESO" ou "DATA") nas primeiras 20 linhas.
2. **0 Interseção em PDFs Gigantes:** recorte bidirecional de datas entre Excel e PDF antes da conciliação.
3. **Locks do Windows:** `WinError 32` ao apagar uploads. Mitigado com `with pd.ExcelFile()`, `gc.collect()` e retry progressivo (5×) em `_cleanup_temp_files`.
4. **Falsos Alertas de UX:** card "Menor Acurácia" vira "Conformidade" verde quando todos os produtos estão 100%.
5. **Legibilidade de Tabelas:** números à direita, datas ao centro, textos à esquerda.
6. **Tabelas Vazias:** seções ocultas via `display: none` quando zero registros.
7. **Pseudo-elemento CSS:** `td:first-child::before` em vez de `tr::before` (evita coluna fantasma).
8. **Empty States:** removidos para seções sem dados — interface mais limpa.
9. **`ERR_UPLOAD_FILE_CHANGED`:** arquivos Excel devem estar fechados antes do upload.

### v3.1

10. **Aviso de recorte de período:** backend retorna `avisos.recorte_periodo`; frontend exibe banner em linguagem simples, com datas ignoradas em `<details>` expansível (evita wall of text).
11. **SQLite sem tabela em testes:** `TestClient` sem lifespan não executava `init_db()` — resolvido com fixture `client` em `conftest.py` + `_ensure_db()` defensivo em `persistence.py`.
12. **Pluralização "viagemns":** corrigido para `viagens` via helper `formatViagensCount()`.
13. **Filtro de data única insuficiente:** migrado para intervalo (`dateStart`/`dateEnd`) com Flatpickr; atalho de dia único na barra de filtros sincroniza o range.
14. **Tonelagem só em OK:** divergências passam a contribuir no modo "Total" via `Peso Bruto - Tara`; toggle no dashboard.
15. **Gráficos e tema:** Chart.js recriado ao alternar dark/light; `resizeCharts()` ao abrir/fechar drawer de histórico.
16. **Períodos longos:** agrupamento por semana quando range > 90 dias para legibilidade do eixo X.
17. **Painel de conformidade compacto:** anel de confiabilidade + chips por produto em faixa única; tipografia ampliada para legibilidade.
18. **Repositório remoto:** [github.com/brunoadsba/codeba-dashboard](https://github.com/brunoadsba/codeba-dashboard.git)

### v3.2.0 (Identidade Visual)

19. **Cores da Marca e Padrão Executivo:** As cores estáticas do Tailwind foram substituídas pela **Paleta de Cores Corporativa CODEBA** (Azul Marinho, Azul Royal, Verde Petróleo e Cinza).
20. **Variáveis CSS Dinâmicas no Chart.js:** Para suportar temas Claro e Escuro com a paleta oficial, introduzimos variáveis (`--color-litio`, `--color-manganes`, etc.) no `:root` e `.light-theme`. O `analytics.js` (`getProductColor`) foi refatorado para ler essas variáveis em tempo de execução via `getComputedStyle`, aplicando a cor correta aos gráficos (Chart.js) e aos chips de produto, garantindo responsividade de tema sem perder a identidade institucional.

### v3.2.1 (Aprimoramentos de UX e Layout)

21. **Fluid Typography e Layout Vertical nos KPIs:** Números na ordem de dezenas de milhões (ex: `57.536.390`) extrapolavam o layout flexível. Solução: migrar os KPI Cards (`.kpi-card`) para `flex-direction: column` centralizado, aplicando `clamp()` no `font-size` para dimensionamento dinâmico baseado na largura (`vw`) sem gerar quebras indesejadas, e separando a unidade de medida ("kg") como sufixo.
22. **Rodapé Dinâmico Multi-Cálculo:** A tabela de Pesagens OK passou a calcular e exibir ativamente no rodapé os totais de Peso Bruto, Tara e Peso Líquido lado a lado, com a introdução elegante do contador de viagens à esquerda, otimizando o preenchimento da `grid`.
23. **Fuzzy Matching Escalável:** A lógica do `analytics.js` unifica dezenas de planilhas de um mesmo produto mas com shippers/clientes diversos (ex: `ÓXIDO DE MAGNÉSIO - MAGNESITA` vs `ÓXIDO DE MAGNÉSIO - IBAR NORDESTE`) utilizando `string.includes()`, permitindo mapeamento de cor nativa e processamento sem distorções no frontend.
24. **Afinidade de Controles Analíticos:** Toggles ambíguos ("Auditado (OK)" vs "Total") foram refatorados com introdução de labels visuais claras (`Exibir nos gráficos: Todo o Volume / Somente Aprovadas`), tornando a intenção do controle explícita e imutável.
25. **Cache Busting Definitivo:** Implantação de "version bump" (`?v=3.6`) rigorosa nas tags `<script>` e `<link>` dentro do `index.html` para anular os efeitos destrutivos de *cache stale* do navegador Chrome na injeção de novas regras de UX e CSS.
26. **Hierarquia Tipográfica de Boas-Vindas:** Na tela inicial de Upload, inserimos os títulos "PORTO DE ILHÉUS" (`h1` com alto peso e `letter-spacing` imponente) e "ANÁLISE DE DADOS" (`h2` com cor de destaque), reestruturando a hierarquia visual (`style.css`) para garantir impacto premium e autoridade corporativa logo no primeiro contato do usuário com a plataforma.

---

## Próximos passos sugeridos (não implementados)

- Export CSV com resumo de tonelagem
- Autenticação e rate limiting (nota em `config.py`)
- Filtro de data no backend (`filter_date` já existe em `reconcile_data`, não exposto na API)
- Agrupamento mensal configurável pelo usuário
