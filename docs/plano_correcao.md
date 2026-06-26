# Plano de Correção Detalhado — CODEBA Dashboard v4.6.0

> **Data:** 2026-06-25  
> **Total de itens:** 30 correções organizadas em 4 lotes  
> **Estimativa total:** ~6h implementação + 2h testes

---

## LOTE 1 — Estabilidade do Motor (🔥 Crítico — ~2h)

### 1.1 — Proteger operações aritméticas contra tipos não numéricos

**Arquivo:** `src/services/reconciliation.py:132,169,246-247`

**Problema:** `abs(ex['Peso Bruto'] - p['Peso Bruto'])` levanta `TypeError` se qualquer valor for `string`, `None` ou `Decimal`. O `match_trips` não tem proteção.

**Solução:**
```python
# Antes de qualquer operação aritmética no match_trips:
ex_pb = pd.to_numeric(ex.get('Peso Bruto', 0), errors='coerce')
ex_tara = pd.to_numeric(ex.get('Tara', 0), errors='coerce')
p_pb = pd.to_numeric(p.get('Peso Bruto', 0), errors='coerce')
p_tara = pd.to_numeric(p.get('Tara', 0), errors='coerce')
diff = abs(ex_pb - p_pb) + abs(ex_tara - p_tara)
```

**Critério de aceite:** Teste com DataFrame contendo strings `"1.500,50"` (vírgula decimal) ou `None` em colunas de peso não quebra.

**Arquivos afetados:** `reconciliation.py` (match_trips, linhas 132, 169, 246)

---

### 1.2 — Trocar subscript direto por `.get()` em match_trips

**Arquivo:** `src/services/reconciliation.py:132,144-156,198-213,216-232,237-250`

**Problema:** `ex['Peso Bruto']`, `p['Tara']`, `ex['Placa']` usando `[]` levantam `KeyError` se a chave não existir.

**Solução:**
```python
# Onde houver subscript direto, trocar por .get() com fallback apropriado:
ex.get('Peso Bruto', 0)
p.get('Tara', 0)
ex.get('Placa', '')
p.get('Data', '')
```

**Escopo:** Todos os 4 blocos de construção de dict (ok_list, divergencias: Diferença de Peso, Falta no PDF, Falta no Excel).

**Critério de aceite:** `match_trips` funciona com registros que tenham apenas subconjunto de colunas.

---

### 1.3 — Corrigir `_is_valid_mercosul_format` (falso positivo)

**Arquivo:** `src/services/post_processing.py:22-27`

**Problema:** Aceita `ABCDEFG` (7 letras) como placa Mercosul válida — só verifica `len==7` + `[:3].isalpha()` + `[3:].isalnum()`.

**Solução:**
```python
def _is_valid_mercosul_format(placa: str) -> bool:
    if len(placa) != 7:
        return False
    # Padrão antigo: ABC1234 (3 letras + 4 números)
    if placa[:3].isalpha() and placa[3:].isdigit():
        return True
    # Padrão Mercosul: ABC1D23 (3 letras + 1 dígito + 1 letra + 2 dígitos)
    if (placa[:3].isalpha() and placa[3].isdigit() and
        placa[4].isalpha() and placa[5:].isdigit()):
        return True
    return False
```

**Critério de aceite:** `_is_valid_mercosul_format("ABCDEFG")` → `False`, `_is_valid_mercosul_format("ABC1D23")` → `True`, `_is_valid_mercosul_format("ABC1234")` → `True`.

---

### 1.4 — Aumentar tolerância de detecção de typos

**Arquivo:** `src/services/post_processing.py:53`

**Problema:** `abs(fp['Peso Bruto'] - fe['Peso Bruto']) < 0.1` — tolerância de 100g impossível na prática (variação normal de balança é 10-50 kg).

**Solução:**
```python
# Usar a mesma tolerância do match exato
TOLERANCIA_TYPO_KG = 50
if (abs(fp['Peso Bruto'] - fe['Peso Bruto']) < TOLERANCIA_TYPO_KG and
    abs(fp['Tara'] - fe['Tara']) < TOLERANCIA_TYPO_KG):
```

**Critério de aceite:** Duas pesagens do mesmo caminhão com diferença de 30 kg são detectadas como typo.

---

### 1.5 — Corrigir header hunting sem break no Excel parser

**Arquivo:** `src/services/excel_parser.py:28-47`

**Problema:** Ao encontrar o header (`header_idx = idx`), o loop **continua**. Se uma linha seguinte (ex: totais) contiver "PLACA", sobrescreve o header.

**Solução:**
```python
# Após detectar o header, dar break no loop interno de detecção de header
# (mas continuar procurando PR nas linhas restantes)

# Separar em dois loops:
# Loop 1: encontrar header_idx (com break ao achar)
# Loop 2: procurar PR (full scan das 50 linhas)
```

**Critério de aceite:** Planilha com linha de total contendo "PLACA" não perde o header verdadeiro.

---

### 1.6 — Eliminar `innerHTML` com interpolação de dados

**Arquivo:** `static/js/app.js:1079,1233,1340,1400`

**Problema:** 4 pontos usam `innerHTML` com `${item.Placa}`, `${item.linha_erro_data}`, etc. — XSS se backend retornar dados malformados.

**Solução:** Substituir por `document.createTextNode()` + `appendChild()` ou usar `textContent` seguro:

```javascript
// ANTES (inseguro):
errorDesc.innerHTML = `Registro presente no PDF <strong>sem correspondência</strong>... Linha <strong>${item.linha_erro_data}</strong>...`;

// DEPOIS (seguro):
errorDesc.innerHTML = '';  // limpa
errorDesc.appendChild(document.createTextNode('Registro presente no PDF '));
const strong1 = document.createElement('strong');
strong1.textContent = 'sem correspondência';
errorDesc.appendChild(strong1);
errorDesc.appendChild(document.createTextNode(' na planilha... Linha '));
const strong2 = document.createElement('strong');
strong2.textContent = item.linha_erro_data;
errorDesc.appendChild(strong2);
```

Ou, mais pragmático para o caso dos pesos (apenas valores numéricos conhecidos):
```javascript
// pesosHtml: aceitável pois valores são numéricos, mas usar textContent nos spans:
tdPesos.textContent = '';  // replaceChildren ou innerHTML=''
tdPesos.appendChild(pesosDom(item));  // criar DOM nodes em vez de string HTML
```

**Critério de aceite:** Nenhum `innerHTML` com `${...}` de dados dinâmicos. Apenas strings fixas ou ícones conhecidos.

---

### 1.7 — Corrigir `<button>` aninhado no history.js

**Arquivo:** `static/js/history.js:86,130,140`

**Problema:** Elemento `history-item` é `<button>` contendo outros `<button>` internos — HTML inválido.

**Solução:**
```javascript
// ANTES:
const item = document.createElement('button');
item.className = 'history-item';

// DEPOIS:
const item = document.createElement('div');
item.className = 'history-item';
item.setAttribute('role', 'button');
item.setAttribute('tabindex', '0');
// Adicionar listener de Enter/Space para acessibilidade
item.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        loadHistoryRun(run.id);
    }
});
```

**Critério de aceite:** Navegadores e leitores de tela reconhecem o elemento interativo corretamente. Navegação por teclado funciona.

---

## LOTE 2 — Performance e Robustez (🔴 Alta — ~1.5h)

### 2.1 — Substituir JSON round-trip por conversão recursiva

**Arquivo:** `src/services/reconciliation.py:720`

**Problema:** `json.loads(json.dumps(result, default=_json_fallback))` serializa e desserializa todo o payload — caro para datasets grandes.

**Solução:**
```python
def _convert_numpy(obj):
    """Converte numpy types in-place sem JSON round-trip."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj

# Substituir:
# result = json.loads(json.dumps(result, default=_json_fallback))
# Por:
result = _convert_numpy(result)
```

**Critério de aceite:** Teste de conciliação com dados reais produz mesmo resultado, sem erro de serialização (`TypeError: Object of type int64 is not JSON serializable`).

---

### 2.2 — Precomputar timestamps para sort key

**Arquivo:** `src/services/reconciliation.py:637-642`

**Problema:** `pd.to_datetime` chamado O(n log n) vezes dentro da função sort.

**Solução:**
```python
# Adicionar campo temporário de ordenação antes do sort:
for item in divergencias + ok_list:
    try:
        item['_sort_ts'] = pd.to_datetime(item['Data'], dayfirst=True)
    except Exception:
        item['_sort_ts'] = pd.Timestamp.min

divergencias.sort(key=lambda x: x['_sort_ts'])
ok_list.sort(key=lambda x: x['_sort_ts'])

# Remover os _sort_ts após ordenar
for item in divergencias + ok_list:
    item.pop('_sort_ts', None)
```

**Critério de aceite:** Mesmo resultado de ordenação, tempo de execução reduzido em datasets com 500+ registros.

---

### 2.3 — Otimizar contagem de `viagens_ok_no_dia` com lookup dict

**Arquivo:** `src/services/reconciliation.py:653-657`

**Problema:** Para cada divergência (n), itera sobre toda ok_list (m) — O(n*m).

**Solução:**
```python
# Pre-computar lookup: (placa, data_dia) -> count
ok_lookup = defaultdict(int)
for ok_item in ok_list:
    placa_ok = ok_item.get('Placa', '')
    data_ok = str(ok_item.get('Data', '')).split(' ')[0]
    ok_lookup[(placa_ok, data_ok)] += 1

# Usar lookup em vez de sum() com filtro:
viagens_ok = ok_lookup.get((placa_div, data_dia_div), 0)
```

**Critério de aceite:** Mesmo valor de `viagens_ok_no_dia`, tempo de execução O(n+m) em vez de O(n*m).

---

### 2.4 — Adicionar RotatingFileHandler no logging

**Arquivo:** `src/logging_config.py:15-33`

**Problema:** `FileHandler` simples — `app.log` cresce sem limite.

**Solução:**
```python
from logging.handlers import RotatingFileHandler

"handlers": {
    "file": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": log_file,
        "maxBytes": 10 * 1024 * 1024,  # 10 MB
        "backupCount": 5,
        "encoding": "utf-8",
        "formatter": "standard",
    },
    ...
}
```

**Critério de aceite:** Após 10 MB, o log rotaciona mantendo 5 backups.

---

### 2.5 — Validar DATABASE_PATH antes de makedirs

**Arquivo:** `src/app.py:44`

**Problema:** Se `DATABASE_PATH` for só `"auditoria.db"` (sem diretório), `os.path.dirname()` retorna `""` e `os.makedirs("")` quebra.

**Solução:**
```python
db_dir = os.path.dirname(DATABASE_PATH)
if db_dir:  # só criar se houver diretório
    os.makedirs(db_dir, exist_ok=True)
```

**Critério de aceite:** App inicia com `DATABASE_PATH="auditoria.db"`.

---

## LOTE 3 — Cobertura de Testes (🟡 Média — ~2.5h)

### 3.1 — Adicionar testes para `cleaners.py`

**Arquivo:** `tests/` (criar `test_cleaners.py`)

**Problema:** Zero testes para `clean_placa` e `safe_to_numeric` — funções chamadas por todos os parsers.

**Casos de teste:**

| Função | Entrada | Esperado |
|--------|---------|----------|
| `clean_placa` | `"ABC-1234"` | `"ABC1234"` |
| `clean_placa` | `"ÁBCD123"` | `"ABCD123"` |
| `clean_placa` | `"abc1d23"` | `"ABC1D23"` |
| `clean_placa` | `""` | `""` |
| `clean_placa` | `None` | `""` |
| `clean_placa` | `"TOTAL"` | `""` |
| `clean_placa` | `"ABC 1234"` | `"ABC1234"` |
| `safe_to_numeric` | `"1.234,56"` | `1234.56` |
| `safe_to_numeric` | `"1.234"` | `1234.0` |
| `safe_to_numeric` | `"57.840"` | `57840.0` |
| `safe_to_numeric` | `"1,5"` | `1.5` |
| `safe_to_numeric` | `None` | `0.0` |
| `safe_to_numeric` | `""` | `0.0` |
| `safe_to_numeric` | `"N/A"` | `0.0` |

---

### 3.2 — Adicionar testes para `filename_parser.py`

**Arquivo:** `tests/` (criar `test_filename_parser.py`)

| Entrada | Esperado |
|---------|----------|
| `"2026-06-18 - LITIO - CBL.xlsx"` | `"LITIO"` |
| `"LITIO - CBL.xlsx"` | `"LITIO"` |
| `"Relatório - ÓXIDO DE MAGNÉSIO.xlsx"` | `"ÓXIDO DE MAGNÉSIO"` |
| `"MANGANES - VALE.xlsx"` | `"MANGANÊS"` |
| `"NÍQUEL- ATLANTIC NICKEL.xlsx"` | `"NÍQUEL"` |
| `"random_file_name.xlsx"` | `None` |

---

### 3.3 — Adicionar testes de borda para recorte de período

**Arquivo:** `tests/test_recorte_aviso.py`

**Cobertura atual:** 2 testes (só Excel fora do range).

**Testes a adicionar:**
- PDF fora do range do Excel (apenas pdf_ignorados deve aparecer)
- Ambos com dados fora da interseção
- Dataset de 1 dia apenas
- filter_date definido (deve pular a lógica de recorte)

---

### 3.4 — Adicionar testes para o DELETE endpoint

**Arquivo:** `tests/test_e2e.py`

**Problema:** Endpoint `DELETE /api/runs/{run_id}` completamente sem teste.

**Testes:**
- Deletar run existente → 200 + `{"deleted": true}`
- Deletar run inexistente → 404
- Verificar que run deletada não aparece mais no listing

---

### 3.5 — Isolar E2E tests com tmp_path

**Arquivo:** `tests/conftest.py`, `tests/test_e2e.py`, `tests/test_report.py`

**Problema:** Testes E2E escrevem no `data/auditoria.db` real e em `temp_uploads/` real — estado vaza entre execuções e entre testes.

**Solução:**
```python
# conftest.py
@pytest.fixture
def isolated_env(tmp_path):
    """Cria ambiente isolado com DB e upload dir temporários."""
    db_path = tmp_path / "test_auditoria.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    
    # Salvar paths originais
    from src import config
    original_db = config.DATABASE_PATH
    original_upload = config.UPLOAD_DIR
    
    # Substituir
    config.DATABASE_PATH = str(db_path)
    config.UPLOAD_DIR = str(upload_dir)
    
    # Reinicializar DB
    from src.services.persistence import init_db
    init_db(str(db_path))
    
    yield {"db_path": db_path, "upload_dir": upload_dir}
    
    # Restaurar
    config.DATABASE_PATH = original_db
    config.UPLOAD_DIR = original_upload
```

---

### 3.6 — Extrair upload boilerplate em fixture compartilhada

**Arquivo:** `tests/conftest.py`

**Problema:** Código idêntico de upload em `test_e2e.py:6-22` e `test_report.py:6-22`.

**Solução:**
```python
@pytest.fixture
def uploaded_run(client, fixtures_dir):
    """Faz upload dos fixtures e retorna o resultado."""
    files = [
        ('files', open(fixtures_dir / 'litio_test.xlsx', 'rb')),
        ('files', open(fixtures_dir / 'relatorio_test.pdf', 'rb')),
    ]
    try:
        resp = client.post("/api/upload", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert "error" not in data, f"Upload failed: {data.get('error')}"
        return data
    finally:
        for _, f in files:
            f.close()
```

---

## LOTE 4 — Dívida Técnica (🔵 Baixa — ~2h)

### 4.1 — Extrair constantes hardcoded para config

**Arquivo:** `src/config.py`, `src/services/reconciliation.py`

**Itens a extrair:**
- `PRODUCT_TO_CLIENT` (reconciliation.py:35-47)
- `DEFAULT_PR_MAP` (reconciliation.py:61-73)
- `TOLERANCIA_EXATA_KG = 50`
- `TOLERANCIA_MAXIMA_KG = 5000`
- `TOLERANCIA_DATA_KG = 100`
- Motivação fixa `'EGS'`

**Formato sugerido:** Variáveis de ambiente ou arquivo YAML em `config/`.

---

### 4.2 — Adicionar type hints

**Arquivo:** `src/services/reconciliation.py`

**Funções a tipar:**
```python
def match_trips(
    ex_list: list[dict],
    p_list: list[dict]
) -> tuple[list[dict], list[dict]]: ...

def reconcile_data(
    df_excel: pd.DataFrame,
    df_pdf: pd.DataFrame,
    filter_date: str | None = None,
    produtos_enviados: list[str] | None = None
) -> dict: ...

def get_cliente(produto: str) -> str: ...
def clean_sev(sev_val) -> str: ...
def _summarize_discarded(df_discarded: pd.DataFrame) -> dict: ...
```

---

### 4.3 — Adicionar validação de colunas obrigatórias

**Arquivo:** `src/services/reconciliation.py` (início de `reconcile_data`)

**Solução:**
```python
REQUIRED_EXCEL_COLS = {'Placa', 'Data', 'Peso Bruto', 'Tara'}
REQUIRED_PDF_COLS = {'Placa', 'Data', 'Peso Bruto', 'Tara'}

if not df_excel.empty:
    missing_excel = REQUIRED_EXCEL_COLS - set(df_excel.columns)
    if missing_excel:
        raise ValueError(f"Excel: colunas obrigatórias ausentes: {missing_excel}")

if not df_pdf.empty:
    missing_pdf = REQUIRED_PDF_COLS - set(df_pdf.columns)
    if missing_pdf:
        raise ValueError(f"PDF: colunas obrigatórias ausentes: {missing_pdf}")
```

---

### 4.4 — Extrair funções duplicadas de preparo Excel/PDF

**Arquivo:** `src/services/reconciliation.py:330-435`

**Solução:** Extrair para função auxiliar:
```python
def _prepare_dataframe(
    df: pd.DataFrame,
    source: str,  # 'excel' ou 'pdf'
    logger_prefix: str
) -> tuple[pd.DataFrame, dict]:
    """Limpeza comum: placa, data, normalização ton->kg, descartados."""
```

---

### 4.5 — Refatorar `reconcile_data` (412 → ~200 linhas)

**Arquivo:** `src/services/reconciliation.py`

**Extrair para funções:**
1. `_validate_and_prepare_excel(df_excel)` → `pd.DataFrame`
2. `_validate_and_prepare_pdf(df_pdf)` → `pd.DataFrame`
3. `_apply_period_filter(df_ex, df_p, filter_date)` → `(df_ex, df_p, recorte_aviso)`
4. `_run_matching_engine(ex_records, p_records)` → `(ok_list, divergencias)`
5. `_post_process(ok_list, divergencias, ...)` → `(ok_list, divergencias, notas_informativas)`
6. `_build_result(ok_list, divergencias, ...)` → `dict`

---

### 4.6 — Refatorar renderDivergencias / renderIncompletas (DRY)

**Arquivo:** `static/js/app.js:1086-1271`

**Solução:** Criar função genérica `renderTable(data, containerId, options)` que recebe configuração de colunas.

---

### 4.7 — Adicionar focus trap e ARIA nos drawers

**Arquivo:** `static/js/history.js`, `static/index.html`

**Solução:**
```javascript
// focus trap simples
function trapFocus(element) {
    const focusable = element.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    element.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
        if (e.key === 'Escape') closePanel();
    });
}
```

**Atributos a adicionar:**
- `role="dialog"` no drawer
- `aria-modal="true"` quando aberto
- `aria-label="Histórico de auditorias"` no drawer header
- `aria-label="Fechar"` no botão de fechar

---

### 4.8 — Tratar `'NAO'` (sem acento) no match de Tipo Carga

**Arquivo:** `src/services/reconciliation.py:189`

**Problema:** `prod_p.upper() in ('NÃO', 'N', '', 'DESCONHECIDO', 'NAN')` — se o PDF tiver `'NAO'` (sem acento, comum em OCR), não é reconhecido.

**Solução:**
```python
# Normalizar: remover acentos para comparação
import unicodedata
def _normalize_text(t: str) -> str:
    return unicodedata.normalize('NFKD', t).encode('ASCII', 'ignore').decode('ASCII').strip().upper()

prod_p_normalized = _normalize_text(prod_p)
if prod_p_normalized in ('NAO', 'N', '', 'DESCONHECIDO', 'NAN'):
    prod_p = ''
```

---

### 4.9 — Trocar `iterrows()` por vetorização nos parsers

**Arquivo:** `src/app.py:202-206`, `src/services/excel_parser.py`

**Solução:**
```python
# ANTES:
produtos_enviados = sorted(set(
    row['Produto'] for df_ in dfs_excel
    for _, row in df_.iterrows()
    if row.get('Produto')
))

# DEPOIS:
produtos_enviados = sorted(set(
    prod for df_ in dfs_excel
    for prod in df_['Produto'].dropna().unique()
))
```

---

### 4.10 — Adicionar fallback para `replaceChildren()` (Safari < 14)

**Arquivo:** `static/js/app.js`

**Solução:**
```javascript
function safeReplaceChildren(parent, ...children) {
    if (typeof parent.replaceChildren === 'function') {
        parent.replaceChildren(...children);
    } else {
        while (parent.firstChild) parent.removeChild(parent.firstChild);
        children.forEach(child => parent.appendChild(child));
    }
}
```

---

## Resumo por Complexidade

| Lote | Itens | Esforço | Prioridade | Risco se não fizer |
|------|-------|---------|------------|---------------------|
| 1 — Estabilidade | 7 | ~2h | 🔴 Imediata | Crash do motor / XSS / acessibilidade quebrada |
| 2 — Performance | 5 | ~1.5h | 🟡 Alta | Log enche disco / lentidão em datasets reais |
| 3 — Testes | 6 | ~2.5h | 🟡 Alta | Regressões não detectadas |
| 4 — Dívida Técnica | 10 | ~2h | 🔵 Média | Manutenibilidade comprometida |

**Ordem de execução recomendada:** Lote 1 → Lote 2 → Lote 3 → Lote 4  
**Verificação a cada lote:** `python -m pytest tests/ -v` (38 testes devem passar)
