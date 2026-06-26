# Memória do Projeto (CODEBA Dashboard de Auditoria)

**Estado Atual:** Sistema de Auditoria de Pesagens **v5.2.0** — Multi-Produto com Analytics Dinâmico, Persistência SQLite, Histórico Consultável, Identidade Visual CODEBA, Desduplicação de Pesagens do OpenPort, Geração de Relatório PDF. Tabela de **7 colunas** com SEV como coluna dedicada: `ÍTEM | SEV | PLACA | DATA/HORA | PRODUTO | PESOS | STATUS`. Painel de detalhes inline expansível com layout flex, overflow controlado, quebra de texto (`word-break: break-word`), e espaçamento de 6px entre linhas de informações. Sistema de feedback padronizado para funcionalidades não implementadas: **Toast** (Corrigir Placa, Ignorar, Abrir no Excel, Corrigir) e **Modal** (Cadastrar viagem) — função `handleNotImplemented(actionName, mode)`. Botões com dimming visual (`opacity: 0.65` → `1` no hover) e tooltip `title="Funcionalidade em desenvolvimento"`. Ícones Phosphor nos badges de status. Pesos em linha única (`Bruto / Tara / **Líquido**`), scrollbar oculta, `table-layout: fixed`. Hierarquia visual de placa: placa corrigida (verde, bold) → placa original (cinza, itálico) → SEV na coluna separada.

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
4. **Suite de Testes:** Pytest + FastAPI `TestClient` — 40 testes cobrindo E2E, analytics, persistência, frontend, deduplication, date_typo, history_hint, recorte_aviso e incomplete_weighings.

---

## Arquitetura Modular (v5.2.0)

### Backend (`src/`)

| Módulo | Responsabilidade |
|--------|------------------|
| `app.py` | FastAPI: upload, histórico (`/api/runs`), lifespan SQLite |
| `config.py` | Paths, `DATABASE_PATH`, limites de upload |
| `logging_config.py` | Logs centralizados em `logs/app.log` |
| `services/excel_parser.py` | Header Hunting nas primeiras 20 linhas |
| `services/pdf_parser.py` | Extração PDF via `pdfplumber` + desduplicação de pesagens |
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

`Placa`, `Data`, `Status`, `Detalhe`, `Produto`, `Peso Bruto`, `Tara`, `Peso Liquido`, `SEV`  
Status possíveis: `Diferença de Peso`, `Falta no PDF`, `Falta no Excel`, `Erro de Placa` (com `Placa_Excel` / `Placa_PDF`)

**Tabela (7 colunas):** Ítem, SEV, Placa, Data/Hora, Produto, Pesos (Bruto/Tara/Líq.), Status

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
cd codeba-dashboard
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
│   ├── test_persistence.py       # v3.1
│   └── test_report.py            # v3.3.0 (endpoint de relatórios)
│
├── scripts/
│   ├── rpa_codeba.py
│   └── diagnostics/
│
├── scratch/
│   ├── run_e2e_tests.py          # v3.3.0 (testes E2E standalone com requests)
│   └── run_all_tests.py          # v3.3.0 (testes unitários + E2E standalone)
│
├── logs/
└── temp_uploads/
```

---

## Suite de Testes

**Comando:** `python -m pytest tests/ -v`  
**Total:** 40 testes

| Arquivo | Cobertura |
|---------|-----------|
| `test_e2e.py` | Upload completo, só PDF, frontend + API histórico + `volume` |
| `test_analytics.py` | Normalização produto, peso líquido, `build_volume_records`, período |
| `test_persistence.py` | Save/load, listagem, delete, init do banco |
| `test_report.py` | Geração de relatório PDF com e sem filtros ativos |
| `test_deduplication.py` | Desduplicação: duplicatas exatas, pesos diferentes, DataFrame vazio, SEV |
| `test_date_typo.py` | Erros de data: data errada vs PDF, tolerâncias de peso e falsos positivos |
| `test_history_hint.py` | Injeção e não-injeção da flag de viagens OK no mesmo dia |
| `test_recorte_aviso.py` | Validação de corte de período de Excel fora da interseção |
| `test_incomplete_weighings.py` | Filtro e reclassificação de pesagens incompletas (Tara=0) no motor de reconciliação |

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
18. **Repositório remoto:** (configurado via git remote)

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
27. **Adesão de Nomenclaturas Oficiais e Otimização do Modal:** O rótulo da área de upload foi alterado de um texto genérico para "Relatório de Pesagem Balança (.xlsx) e Relatório OpenPort (.pdf) Tela 7015", orientando melhor a operação portuária. O texto de carregamento do spinner também foi refinado.
28. **Desbloqueio de Overflow em Auditorias de Alta Densidade:** Auditorias que resultavam em tabelas colossais (ex: 1.638 viagens na seção de Divergências) sofriam "clipping" visual devido ao limite estrutural de `max-height: 5000px` na `section-body`, utilizado para animações de *collapse*. A propriedade foi severamente majorada para `250000px`, acomodando layouts de relatórios virtualmente ilimitados no `grid` sem quebrar a UI.

---

### v3.2.2 (Desduplicação de Pesagens)

29. **Desduplicação na origem (pdf_parser.py):** O sistema OpenPort gera registros duplicados de pesagem com pequenas variações de digitação na placa ou SEV (ex: pesagens 44354/44358, onde a placa aparece como `RDP6D75` e `RDP6075`). Implementada função `_deduplicate_weighings()` no `pdf_parser.py` que remove duplicatas **antes** dos dados chegarem ao motor de conciliação. Critério: mesma `Data` + mesmo `Peso Bruto` + mesma `Tara` (match exato). Mantém a primeira ocorrência. Cada duplicata descartada é logada com Placa, Data, Pesos e SEV para rastreabilidade. Isso elimina falsos alertas de "Falta no Excel" e "Diferença de Peso" causados por sujeira do OpenPort, sem alterar nenhuma outra camada do sistema (blindagem da regra de negócio no `reconciliation.py`).

### v3.2.3 (Validação E2E com Dados Reais)

30. **Ambiente Offline e Executável de Teste:** O ambiente de produção offline impede a instalação do `pytest`. Desenvolveu-se um script de testes standalone (`scratch/e2e_test_runner.py`) usando a biblioteca `requests` pré-instalada para automatizar o upload, conferência dos cálculos, persistência em banco e leitura do histórico sem necessidade do pytest.
31. **Validação E2E e Métricas de Referência:** O processamento com os arquivos reais (`ÓXIDO DE MAGNÉSIO - MAGNESITA.xlsx`, `Relatório de Pesquisa - 7015.pdf`, `LITIO - CBL.xlsx`) validou a corretude do motor de conciliação. As métricas de referência estabelecidas foram: Confiabilidade de 88.2% (60/68 viagens OK), 8 divergências, 4 deduções de produto automáticas de Lítio e Óxido de Magnésio, e volume total de 2.807,6 t.
---

### v3.3.0 (Botão "Gerar Relatório" & Testes E2E Offline)

32. **Download de Relatório com Filtros Ativos:** Adicionado no `app.js` o event listener para o botão `#btn-report` ("Gerar Relatório"), utilizando um elemento `<a>` dinâmico temporário para realizar o download. Isso evita abas em branco e transmite os filtros selecionados (`placa`, `produto`, `date_start`, `date_end`) para o endpoint `/api/runs/{run_id}/report`.
33. **Testes de Unidade para Relatório PDF:** Criado o teste `tests/test_report.py` validando o download do PDF e os cabeçalhos de resposta HTTP corretos (como `Content-Type: application/pdf` e `Content-Disposition`).
34. **Script de Testes E2E Autônomo e Offline:** Como o ambiente local offline pode apresentar restrições para instalar o `pytest` via rede no PyPI, criamos os scripts `scratch/run_e2e_tests.py` (testes E2E com `requests`) e `scratch/run_all_tests.py` (testes unitários e de integração mockados) que executam testes reais locais contra a porta do servidor, garantindo a integridade dos fluxos.

---

### v3.4.0 (Correções de Horários, Suporte a Tela 7714 e Guia de Usuário / FAQ)

35. **Preservação de Horários em Erros de Placa:** A comparação no algoritmo de match de typos (`post_processing.py`) foi ajustada para ignorar a hora no momento da comparação de datas e usar a data/hora exata do PDF no registro gerado. Isso resolveu o problema de relatórios gerados sem o horário dos caminhões.
36. **Correção de Chaves Duplicadas no Pandas (Tela 7714):** Refatorado o mapeamento de colunas em `pdf_parser.py` para construir um DataFrame contendo apenas as colunas desejadas de forma unívoca, sanando o erro `ValueError: cannot assemble with duplicate keys` ao ler arquivos exportados pela Tela 7714 do OpenPort.
37. **SEV nas Pesagens Aprovadas (OK):** Adicionada a coluna `SEV` na visualização das pesagens aprovadas no frontend (`static/index.html` e `static/js/app.js`), mantendo a uniformidade com o relatório PDF.
38. **Guia de Ajuda e FAQ no Dashboard:** Implementado o botão "Guia / FAQ" e o painel drawer lateral retrátil explicativo no frontend com suporte a temas Claro/Escuro.

### v3.4.1 (Ajustes de UX, Refatoração "SEV" e Parsing de Milhares)

39. **Substituição do Campo "Cliente" por "SEV":** Para simplificar o agrupamento e tornar a auditoria mais direta, todo o rastreamento da coluna "Cliente" (e as heurísticas de extração dele pelo nome do arquivo Excel) foi removido do backend e do frontend. Em seu lugar, introduzimos a "SEV", que é a ID do romaneio e já vem nativamente do OpenPort, passando a ser a referência oficial no lugar do cliente nos PDFs de exportação e planilhas CSV.
40. **Parsing Inteligente de Milhares em Pesos PDF:** Correção no `cleaners.py` (`safe_to_numeric`) para interpretar corretamente pesos do OpenPort (tela 7714) que formatavam milhares com um único ponto (ex: `57.840` kg). O sistema agora distingue de forma inteligente entre um separador decimal e um separador de milhares com base na presença de exatamente 3 casas pós-ponto (ex: `57.840`), evitando que pesagens de 57 mil quilos sejam lidas como 57 quilos e zerando divergências falsas-positivas ("Diferença de Peso").
41. **Default para Tela 7714:** Atualização das chamadas textuais da interface e do script robô de automação RPA (`rpa_codeba.py`) para solicitar e baixar explicitamente o relatório da **Tela 7714** do sistema OpenPort, firmando-a como novo padrão ouro operacional.

---

### v4.0.0 (Saneamento, Refatoração e Limpeza)

42. **Saneamento de Credenciais Expostas:** O CPF e a senha do sistema OpenPort estavam hardcoded em `scripts/rpa_codeba.py` e `docs/automacao.md`. Substituídos por variáveis de ambiente (`OPENPORT_USER`, `OPENPORT_PASS`) com fallback, permitindo que cada operador configure suas próprias credenciais via `.env` sem expor dados sensíveis no repositório.
43. **Remoção de PII e Caminhos Absolutos:** Substituídos caminhos fixos com nome de usuário por `os.environ.get("USERPROFILE")` ou caminhos relativos nos scripts de diagnóstico e documentação.
44. **Dependência `reportlab` Adicionada:** O pacote `reportlab` era utilizado em `src/services/report_generator.py` mas não constava no `pyproject.toml` nem no `requirements.txt`. Adicionado para garantir que `pip install` instale todas as dependências necessárias.
45. **Extração de `cleanup_temp_files`:** A função de retry para remoção de arquivos temporários (Windows File Lock) foi extraída de `src/app.py` para `src/utils/file_utils.py`, reduzindo o acoplamento e facilitando testes unitários.
46. **Correção de Bug no "Novo Upload":** O botão "Novo Upload" (`btn-replace`) não resetava o valor do `<input type="file">`, fazendo com que o evento `change` não disparasse ao selecionar os mesmos arquivos novamente. Adicionado `fileInput.value = ''` no handler.
47. **Limpeza de Artefatos:** Removidos 5 PDFs de teste (`test_report*.pdf`) do diretório `static/`, 3 arquivos órfãos de `temp_uploads/`, ambientes virtuais excedentes (`.venv_old/`, `.venv2/`, `venv/`) e 7 scripts de diagnóstico em `scripts/diagnostics/`.
48. **Atualização do `.gitignore`:** Adicionados `scripts/diagnostics/`, `data/*.xlsx`, `data/*.pdf`, `data/relatório/`, `data/implementação/` e `.pytest_cache/` para evitar versionamento de dados operacionais e artefatos de cache.
49. **Lint Automático (ruff):** Corrigidas ~150 advertências de lint (W293, I001, F401, F841) via `ruff --fix`, incluindo imports não ordenados, espaços em branco em linhas vazias e variáveis não utilizadas em `report_generator.py`.
50. **Type Hints:** Adicionadas anotações de tipo em `cleaners.py` (`clean_placa`, `safe_to_numeric`) e `filename_parser.py` (`extract_produto_from_filename`).
51. **UX da Tela de Upload:** Reformulado o texto descritivo da drop zone para "Planilha da balança (.xlsx) + Relatório OpenPort (.pdf)" e movido "Tela 7714" como subtítulo discreto dentro do indicador visual do PDF, associando a informação ao formato correto sem poluir a chamada principal para ação.
52. **Background Image:** A imagem de fundo `areo-001.png` (1912×916 px, RGBA) foi posicionada em `static/bg-ilheus.png`, corrigindo a referência do CSS que apontava para `/static/bg-ilheus.png`.

### v4.0.1 (Limpeza de Branches)

53. **Branches obsoletas removidas:** Deletadas 7 branches locais (`limpeza`, `master`, `teste`, `resolvendo-duplicacao`, `ajuste-relatorio`, `feature/branch-no-relatorio`) e 3 remotas (`feature/branch-no-relatorio`, `feature/geracao-de-relatorios`, `inserindo-SEV`). O repositório agora contém apenas a branch `main`.

### v4.1.0 (UX Simplificada — 7 Colunas)

54. **Tabela reduzida de 11 para 7 colunas:** A expansão para 11 colunas (Ítem, SEV, Placa, Data, Produto, Cliente, P. Bruto, Tara, P. Líquido, Status, Detalhe) causou compressão severa e truncamento. Solução: fundir as 3 colunas de peso em uma única coluna "Pesos" (monospace, 3 linhas), remover colunas não essenciais (numeração `#`, Cliente). Resultado: 7 colunas legíveis mesmo em viewports médias.
55. **`overflow: hidden` removido dos TDs:** O CSS global `.audit-table td` aplicava `overflow: hidden` + `text-overflow: ellipsis`, truncando todo conteúdo excedente com "...". Removido para permitir quebra natural de linha com `word-wrap: break-word`.
56. **Larguras em pixels fixos:** Substituídas larguras percentuais por `min-width` em pixels (ex: Detalhe `min-width: 200px`), garantindo que colunas críticas nunca comprimam abaixo do legível. A tabela usa `table-layout: fixed` + overflow-x no container para scroll horizontal quando necessário.
57. **`prod_p` "Não" no Detalhe:** O Tipo Carga do PDF frequentemente contém "Não", gerando Detalhes confusos como "Registro no PDF (Não) sem correspondência na planilha.". Agora, se o Tipo Carga for "Não" ou vazio, é omitido do texto narrativo.
58. **Peso Líquido como campo calculado:** `Peso Liquido = Peso Bruto - Tara` é calculado em cada divergência no momento da criação do dicionário, garantindo que esteja sempre disponível para CSV e relatório PDF sem lógica extra no frontend.

### v4.2.0 (Correção Crítica — Registros Individuais do PDF)

59. **Remoção do agrupamento por SEV:** O `groupby('SEV')` em `reconciliation.py` colapsava múltiplas viagens legítimas com o mesmo romaneio (ex: caminhão carregado na ida e descarregado na volta) em um único registro usando `max(Bruto)` e `max(Tara)`. Isso destruía dados silenciosamente — a segunda viagem desaparecia e gerava falsos "Falta no Excel". Removido o bloco inteiro. Cada linha do PDF agora é tratada como registro individual. O SEV permanece como campo informativo. Diagnóstico de SEVs com 3+ registros preservado via log para detectar anomalias do OpenPort.
60. **Atualização dos documentos de erros e ajustes:** Os arquivos `docs/erros.md` e `docs/ajustes.md` foram atualizados para refletir o estado real do sistema — 12 dos 13 erros catalogados já estavam corrigidos, mas os documentos não haviam sido updated.

### v4.3.0 (Melhorias de UX, Resolução de Ambiguidade de Placas com Múltiplas Viagens)

61. **Tratamento de Placas com Múltiplas Viagens (Caso RPJ0I50):** O veículo `RPJ0I50` realizou duas viagens no dia 18/06/2026. A primeira foi conciliada com sucesso (OK), e a segunda não constava no Excel ("Falta no Excel"). Para evitar que o operador interprete erroneamente que houve falha do sistema por a placa já aparecer na aba OK, o backend agora injeta `viagens_ok_no_dia: count` em cada divergência cuja placa teve viagens OK no mesmo dia.
62. **Badge Informativo 💡 no Frontend:** O frontend exibe um badge destacado (`💡 Placa com X viagem(ns) OK neste dia. Verifique se esta pesagem foi esquecida.`) na coluna de Detalhes da tabela de divergências. Isso orienta o operador de que a viagem em questão pode ter sido simplesmente esquecida na planilha manual.
63. **Logs de Normalização de Toneladas para Kg:** Adicionados logs detalhados ao final do carregamento dos dados para facilitar o diagnóstico de divergências por formatação de peso (Tons vs Kg).
64. **Limitação documentada em `safe_to_numeric`:** Documentado o comportamento heurístico da limpeza de dados em relação a strings numéricas brasileiras com 3 casas decimais.
65. **Correção de Linter CSS:** Resolvida a advertência de prefixo do fornecedor para a propriedade `line-clamp` com `line-clamp` padrão no CSS.
66. **Testes de Unidade para Histórico e Dicas:** Criado o teste `tests/test_history_hint.py` contendo testes automatizados para verificar a correta injeção e não-injeção da flag `viagens_ok_no_dia` (total de testes elevado para 28, todos passando).

### v4.4.0 (Overhaul de UI/UX da Tabela de Divergências)

67. **Redesenho para 6 Colunas:** Removida a coluna de Detalhes da tabela principal. A Placa agora destaca a SEV associada como metadado secundário, e a Data / Hora é estruturada em duas linhas. A coluna de pesos alinha rótulos com destaque verde para o líquido.
68. **Painel Expansível Inline e Cards:** O clique na linha expande um painel inline de detalhes contendo dois cards temáticos: Erro (aponta aba, linha, arquivo e data errada) e Contexto (número de viagens OK no dia, produto esperado e diferença de datas calculada dinamicamente).
69. **Ações e Notificações Toasts:** Botões interativos para corrigir data, marcar como revisado (com micro-interação visual de linha tachada) e abrir no Excel. Notificações do tipo Toast informam o usuário sobre o progresso das ações executadas.
70. **Novos Testes Unitários (Total 32):** Adicionados testes unitários para a lógica de detecção de erros de digitação de data no Excel (`tests/test_date_typo.py`), totalizando 32 testes unitários que garantem a segurança do motor de conciliação.

### v4.5.0 (Tratamento de Pesagens Incompletas - Tara=0)

71. **Filtragem e Identificação de Tara=0:** Veículos parados no OpenPort geravam registros com `Tara=0` (entrada) que ficavam órfãos ou parciais. Implementado o filtro `_remove_incomplete_weighings` no `pdf_parser.py` para remover automaticamente esses registros quando existe uma pesagem completa no mesmo dia e placa.
72. **Notas Informativas de Conciliação:** Caso um registro com `Tara=0` chegue ao motor de reconciliação como "Falta no Excel", mas a placa possua viagem conciliada como OK no mesmo dia, ele é reclassificado como "Pesagem Incompleta" em `notas_informativas`, prevenindo falsos positivos na aba de Divergências.
73. **Nova Seção e Exportação no Frontend:** Criada a seção de "Pesagens Incompletas" no dashboard com sua respectiva tabela expansível e contadores de badges dedicados. A funcionalidade de exportação em CSV também foi adaptada para incluir esses registros de forma categorizada.
74. **Suite de Testes Expandida (Total 40):** Criados os testes em `tests/test_incomplete_weighings.py` para blindar o comportamento contra regressões no motor e no parser.

---

### v4.6.0 (Robustez e Confiabilidade — Hash SHA-256 e Alerta de Descartes)

75. **Cálculo de Hash SHA-256 de Integridade:** Implementado em `reconciliation.py` um mecanismo determinístico de cálculo de hash que serializa o estado dos dados auditados (`ok`, `divergencias`, `notas_informativas`) garantindo a imutabilidade matemática das conciliações. Qualquer alteração em pesos, placas ou datas invalida o hash.
76. **Assinatura no PDF Executivo:** O relatório PDF gerado pelo sistema agora estampa a assinatura hash SHA-256 em todas as páginas no rodapé, permitindo auditorias forenses externas com facilidade.
77. **Logs e Alertas de Registros Descartados:** O sistema agora detecta e separa registros com dados corrompidos ou inconsistentes (por exemplo, placas ausentes ou datas inválidas) do fluxo principal e exibe uma notificação destacada no dashboard (com opção de colapsar e dispensar), permitindo identificar falhas de entrada rapidamente.

---

### v4.7.0 (Redesign UX/UI da Tabela de Divergências)

78. **Remoção da Coluna SEV Redundante:** A coluna SEV foi removida da tabela principal de divergências e da tabela de Pesagens Incompletas. A informação SEV já era exibida 3 vezes (coluna, subtítulo da placa, painel de detalhes). A remoção economiza ~66px de espaço horizontal, permitindo colunas mais largas para dados úteis. O SEV permanece acessível no subtítulo da placa e no painel de detalhes expansível.
79. **Largura da Coluna Data Aumentada:** A coluna Data/Hora foi aumentada de 105px para 130px com `white-space: nowrap`, corrigindo o truncamento de datas completas (DD/MM/YYYY HH:MM:SS) que ocorria em视图portsmédios.
80. **Pesos em Linha Única:** A exibição de pesos foi simplificada de 3 linhas verticais (`Bruto: X / Tara: Y / Líq.: Z`) para formato compacto em linha única (`60.200 / 20.620 / **39.580** kg`), com o peso líquido destacado em verde e negrito.
81. **Transformação de Placa com Seta:** O diff de placas (caso "Erro de Placa") agora usa formato single-line com seta: `EXCEL: RDP6284 → PDF: RDP9D84`, com caracteres divergentes destacados em vermelho e sublinhados.
82. **Ícones Phosphor nos Badges de Status:** Badges de status agora incluem ícones visuais para diferenciação rápida: `ph-warning-circle` para "Erro de Placa", `ph-x-circle` para "Falta no Excel", `ph-check-circle` para OK.
83. **CSS Refatorado (6 Colunas):** As larguras de coluna foram recalculadas para a nova estrutura (Ítem: 42px, Placa: 100px, Data: 130px, Produto: 120px, Pesos: 200px, Status: 140px). Adicionadas classes utilitárias para o novo formato de pesos e placa.
84. **colSpan Atualizado:** O painel de detalhes expansível usa `colSpan=6` em vez de `colSpan=7` para alinhar corretamente com a nova estrutura da tabela.
85. **Suite de Testes Inalterada (40/40):** Todas as mudanças foram implementadas apenas no frontend (HTML/CSS/JS), sem alterar o backend. Os 40 testes existentes continuam passando, validando que a lógica de conciliação e geração de relatórios não foi afetada.

---

### v4.8.0 (Painel de Detalhes Contextual — Erro de Placa)

86. **Banner de Alerta Crítico (0 Viagens):** Quando a placa corrigida não possui viagens registradas no dia, um banner de alerta amarelo é exibido acima dos botões de ação, informando que o peso ficará sem vínculo ao aplicar a correção. O banner usa ícone `ph-warning` e formatação destacada com `<code>` para a placa.
87. **Botão "Corrigir Placa" (Contextual):** O botão "Corrigir data" foi renomeado para "Corrigir Placa" e agora aparece apenas quando o status é "Erro de Placa". Para outros tipos de erro (data), o botão "Corrigir data" continua disponível. O botão usa estilo `btn-primary-action` com cor verde para indicar ação principal.
88. **Botão "Ignorar e manter original":** Adicionado botão secundário que permite ao operador ignorar a sugestão automática e manter a placa do Excel (`Placa_Excel`). Útil quando o OCR do PDF apresenta qualidade inferior.
89. **Botão "Cadastrar viagem":** Adicionado botão de destaque (amarelo/laranja) que aparece apenas quando a placa corrigida possui 0 viagens no dia. Permite criar um registro de viagem para a placa do PDF, resolvendo o problema de vínculo órfão.
90. **Hierarquia Visual de Botões:** Implementados 3 níveis visuais: ação principal (verde), ação secundária (cinza) e ação de destaque (amarelo). Botões secundários como "Abrir no Excel" aparecem apenas quando relevantes (erros de data).
91. **Descrição do Erro de Placa Melhorada:** O card "ERRO DETECTADO" agora exibe texto descritivo claro: `Placa 'RDP6284' não confere. Corrigida para 'RDP9D84'.` quando o status é "Erro de Placa", em vez do texto genérico anterior.
92. **CSS para Warning Banner:** Adicionadas classes `.detail-warning-banner` e estilos para modo claro/escuro, com fundo amarelo translúcido, borda e ícone de alerta.

---

### v4.9.0 (Re-adição da Coluna SEV e Redesign da Tabela)

93. **Coluna SEV Re-adicionada como Coluna Dedicada:** Após a remoção em v4.7.0, a coluna SEV foi restaurada entre ÍTEM e PLACA. A informação SEV antes ficava oculta no subtítulo da placa — agora está visível imediatamente na tabela, melhorando a legibilidade. Estrutura final: `ÍTEM | SEV | PLACA | DATA/HORA | PRODUTO | PESOS | STATUS`.
94. **Larguras de Coluna Recalculadas:** Ítem (50px), SEV (100px, centralizado), Placa (28%, min 140px, flex-grow: 1), Data (14%, min 140px), Produto (14%, min 120px), Pesos (22%, min 180px), Status (12%, min 100px). O `table-layout: fixed` garante que colunas respeitem o container.
95. **Scroll Bar Oculta:** Aplicado `scrollbar-width: none` + `::-webkit-scrollbar { display: none }` no container da tabela para limpeza visual, mantendo a funcionalidade de scroll horizontal.
96. **colSpan Atualizado para 7:** O painel de detalhes expansível usa `colSpan=7` em vez de `6` para alinhar com a nova estrutura de 7 colunas.

---

### v5.0.0 (Refatoração do Layout do Painel Expansível)

97. **Conversão de Grid para Flex no Painel de Detalhes:** O container dos dois cards (Erro + Contexto) foi migrado de `display: grid; grid-template-columns: 1fr 1fr` para `display: flex; width: 100%`. Isso resolveu o bug crítico de overflow onde o painel direito (CONTEXTO DA PLACA) era empurrado para fora da tela pelo conteúdo do painel esquerdo.
98. **Overflow Controlado:** Adicionado `flex: 1; min-width: 0; overflow: hidden` em `.detail-card`. Cada card ocupa exatamente 50% do container, e conteúdo longo é contido dentro dos limites do card sem transbordar.
99. **Quebra de Texto em Nomes de Arquivo:** Adicionado `white-space: normal; word-break: break-word; text-align: right; flex: 1` em `.prop-value`. Nomes de arquivo longos (ex: `NÍQUEL- ATLANTIC NICKEL...xlsx`) agora quebram linha corretamente em vez de ultrapassar o alinhamento.
100. **Espaçamento entre Linhas Informativas:** Adicionado `padding: 6px 0; gap: var(--space-2)` em `.prop-row`, criando separação visual clara entre Arquivo, Aba, Linha e Data no painel esquerdo.
101. **Description Wrapping:** Adicionado `overflow-wrap: break-word; word-break: break-word` em `.card-description` para garantir que textos longos em ambos os cards (esquerdo e direito) sejam renderizados sem clipping.

---

### v5.1.0 (Sistema de Feedback para Funcionalidades Não Implementadas)

102. **Função `handleNotImplemented(actionName, mode)`:** Criada camada de abstração centralizada para lidar com botões cujo backend ainda não está conectado. Dois modos: `'toast'` (padrão, para ações leves) e `'modal'` (para ações com peso maior).
103. **Toast Notifications (Estratégia Leve):** Botões `Corrigir Placa`, `Ignorar`, `Abrir no Excel` e `Corrigir` agora exibem um toast warning com mensagem `"${actionName} será liberada na próxima versão."` ao serem clicados. O toast auto-dismissa em 3.5s com fade-out.
104. **Modal de Aviso (Estratégia de Lead):** Botão `Cadastrar viagem` agora abre um modal no centro da tela com título "Funcionalidade em Desenvolvimento" e mensagem contextual. O modal possui backdrop blur, animação de entrada/saída, e fecha com botão "Fechar" ou clique no backdrop.
105. **HTML do Modal:** Adicionado `#feature-modal` ao `index.html` com ícone `ph-tools`, título dinâmico, mensagem dinâmica e botão de fechar. Segue o mesmo padrão do `#error-modal` existente.
106. **Lógica de Modal no JS:** `showFeatureModal(title, message)` e `hideFeatureModal()` — reutilizam o padrão de animação do `showError`/`hideError` (reflow trigger + classe `active`).

---

### v5.2.0 (Visual Dimming e Tooltips nos Botões)

107. **Dimming Visual:** O container `.detail-actions-wrapper` inicia com `opacity: 0.65` e sobe para `1` no hover, sinalizando visualmente que as ações ainda não estão totalmente ativas.
108. **Tooltip via CSS:** Botões com `title` exibem um tooltip puro CSS via pseudo-elemento `::after` posicionado acima do botão, com `opacity` transition de 0→1 no hover. Remove a necessidade de bibliotecas externas de tooltip.
109. **Tooltips nos Botões:** Todos os botões de ação agora possuem `title="Funcionalidade em desenvolvimento"` — Corrigir Placa, Ignorar, Cadastrar viagem, Corrigir, Abrir no Excel.

---

## Próximos passos sugeridos (não implementados)

- Export CSV com resumo de tonelagem
- Autenticação e rate limiting (nota em `config.py`)
- Filtro de data no backend (`filter_date` já existe em `reconcile_data`, não exposto na API)
- Agrupamento mensal configurável pelo usuário

