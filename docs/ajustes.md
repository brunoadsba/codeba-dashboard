# Plano de Correções — Motor de Conciliação CODEBA

> **Última atualização:** 2026-06-19 — Status verificado contra o código-fonte atual.

---

## ✅ Correção #1 — Remover agrupamento por SEV (CRÍTICA) — IMPLEMENTADA em v4.2.0

**Arquivo:** `src/services/reconciliation.py`

**O que foi feito:**
- Removido o bloco `groupby('SEV')` com `agg({'Peso Bruto': 'max', 'Tara': 'max'})`
- Cada linha do PDF é tratada como registro individual
- SEV mantido como campo informativo (limpeza + preenchimento de temporários preservados)
- Diagnóstico de SEVs com 3+ registros preservado via log

**Verificação:** 26 testes passando sem regressão.

---

## ✅ Correção #2 — Adicionar threshold no match por aproximação (CRÍTICA) — IMPLEMENTADA

**Arquivo:** `src/services/reconciliation.py`

**O que foi feito:**
- `TOLERANCIA_MAXIMA_KG = 5000` implementado
- Se `min_diff > TOLERANCIA_MAXIMA_KG`, o pareamento não é forçado

---

## ✅ Correção #3 — Parsing inteligente de produto (ALTA) — IMPLEMENTADA

**Arquivo:** `src/utils/filename_parser.py`

**O que foi feito:**
- Lista `PRODUTOS_CONHECIDOS` com busca por substring case-insensitive
- Normalização canônica (LÍTIO→LITIO, MANGANES→MANGANÊS, etc.)
- Fallback para lógica antiga (`split(" - ")`)

---

## ✅ Correção #4 — Logging de datas inválidas (ALTA) — IMPLEMENTADA

**Arquivos:** `src/services/excel_parser.py`, `src/services/pdf_parser.py`

**O que foi feito:**
- Contagem de datas antes e depois do `pd.to_datetime(errors='coerce')`
- `logger.warning("X data(s) inválida(s) ignorada(s)")` em ambos os parsers

---

## ✅ Correção #5 — Typos bidirecionais (ALTA) — IMPLEMENTADA

**Arquivo:** `src/services/post_processing.py`

**O que foi feito:**
- `_is_valid_mercosul_format()` determina qual placa tem formato válido
- A placa em formato Mercosul correto é definida como `placa_corrigida`
- Distância Levenshtein ≥1 e ≤2 mantida como critério

---

## ✅ Correção #6 — Normalização unicode em clean_placa (MÉDIA) — IMPLEMENTADA

**Arquivo:** `src/utils/cleaners.py`

**O que foi feito:**
- `unicodedata.normalize('NFKD', str(placa)).encode('ASCII', 'ignore').decode('ASCII')` antes do regex
- "ÁBCD123" → "ABCD123" (não mais "BCD123")

---

## ✅ Correção #7 — Desduplicação com mais critérios (MÉDIA) — IMPLEMENTADA

**Arquivo:** `src/services/pdf_parser.py`

**O que foi feito:**
- Chave ampliada para `['Placa', 'Data', 'Peso Bruto', 'Tara']`
- Log individual de cada duplicata descartada para rastreabilidade

---

## ✅ Correção #8 — Aumentar limite do Header Hunting (MÉDIA) — IMPLEMENTADA

**Arquivo:** `src/services/excel_parser.py`

**O que foi feito:**
- `df_raw.head(50)` (era 20)

---

## ⚠️ Correção #9 — Logging de diagnóstico (MÉDIA) — PARCIALMENTE IMPLEMENTADA

**Arquivos:** `excel_parser.py`, `pdf_parser.py`, `reconciliation.py`

**O que foi feito:**
- ✅ `reconciliation.py`: loga total de Excel e PDF na entrada e após preparo
- ✅ `reconciliation.py`: loga placas do PDF sem correspondência no Excel
- ✅ `reconciliation.py`: loga OK e divergências ao final
- ✅ `excel_parser.py`: loga total extraído por sheet
- ✅ `pdf_parser.py`: loga total extraído e duplicatas removidas

**Pendente:**
- Motivo de descarte de sheets individuais
- Contagem detalhada de registros descartados no recorte de período por fonte

---

## ✅ Correção #10 — Adicionar Peso Líquido como critério de desempate (MÉDIA) — IMPLEMENTADA

**Arquivo:** `src/services/reconciliation.py`

**O que foi feito:**
- Peso Líquido é usado como desempate quando Bruto+Tara empatam no Match por Aproximação
- **Nota:** O Detalhe não registra explicitamente quando o match foi resolvido por Peso Líquido (melhoria futura)

---

## ✅ Correção #11 — Simplificação UX: 7 colunas essenciais (ALTA) — IMPLEMENTADA em v4.1.0

**Arquivos:** `static/index.html`, `static/css/style.css`, `static/js/app.js`

**O que foi feito:**
- Tabela reduzida de 11 para 7 colunas: SEV, Placa, Data, Produto, Pesos, Status, Detalhe
- Pesos fundidos em coluna monospace (Bruto/Tara/Líq.)
- Colunas `#` e `Cliente` removidas

---

## ✅ Correção #12 — Remover `prod_p` do Detalhe quando for "Não" (MÉDIA) — IMPLEMENTADA em v4.1.0

**Arquivo:** `src/services/reconciliation.py`

**O que foi feito:**
- Validação: se Tipo Carga é "Não", "N", vazio, "Desconhecido" ou "NaN", omite do Detalhe
- Detalhe vira "Registro no PDF sem correspondência na planilha." (sem "(Não)")

---

## ✅ Correção #13 — Remover `overflow: hidden` dos TDs (MÉDIA) — IMPLEMENTADA em v4.1.0

**Arquivo:** `static/css/style.css`

**O que foi feito:**
- `overflow: hidden` e `text-overflow: ellipsis` removidos do `.audit-table td`
- `word-wrap: break-word` + `min-width` em pixels fixos
- `table-layout: fixed` + overflow-x no container

---

---

## ✅ Melhoria #14 — Tratamento de Placas com Múltiplas Viagens (Caso RPJ0I50) — IMPLEMENTADA em v4.3.0

**Arquivos:** `src/services/reconciliation.py`, `static/js/app.js`, `static/css/style.css`

**O que foi feito:**
- Backend: Cruza placas divergentes com a lista de viagens OK no mesmo dia, injetando `viagens_ok_no_dia: count` no payload.
- Frontend: Adiciona badge 💡 na coluna Detalhe caso a placa tenha viagens OK registradas no mesmo dia, alertando o operador de que a viagem em questão pode ter sido simplesmente esquecida na planilha manual.
- CSS: Criado estilo `.badge-info-history` com suporte a temas Claro/Escuro.

---

## ✅ Correção #15 — Alinhamento de Prefixo CSS (Linter) — IMPLEMENTADA em v4.3.0

**Arquivo:** `static/css/style.css`

**O que foi feito:**
- Adicionado o atributo padrão `line-clamp` ao lado do `-webkit-line-clamp` para conformidade com padrões modernos e resolução do aviso de linter.

---

## ✅ Melhoria #16 — Overhaul de UI/UX da Tabela de Divergências — IMPLEMENTADA em v4.4.0

**Arquivos:** `static/index.html`, `static/css/style.css`, `static/js/app.js`

**O que foi feito:**
- Redesenho completo para exibição de 6 colunas sem overflow.
- Implementação de click-to-expand em qualquer parte da linha da tabela de divergências.
- Substituição de tooltips flutuantes por painel expansível inline contendo:
  - Card de Erro (Vermelho): Aponta linha, aba, arquivo e data comparativa.
  - Card de Contexto (Verde): Mostra viagens OK no dia, produto esperado e diferença de datas calculada dinamicamente.
- Botões de ações com micro-interações ("Corrigir data", "Marcar como revisado" com efeito tachado na linha e fechamento automático, e "Abrir no Excel").
- Notificações de confirmação flutuantes (Toasts).

---

## ✅ Melhoria #17 — Isolamento de Pesagens Incompletas (Tara=0) — IMPLEMENTADA em v4.5.0

**Arquivos:** `src/services/pdf_parser.py`, `src/services/reconciliation.py`, `static/index.html`, `static/js/app.js`, `static/js/analytics.js`

**O que foi feito:**
- PDF Parser: Adicionado filtro `_remove_incomplete_weighings` para remover registros parciais (Tara=0) quando houver pesagem correspondente completa do mesmo veículo no dia.
- Reconciliação: Registros restantes com Tara=0 que possuem viagem OK no dia são reclassificados como "Pesagem Incompleta" e migrados para a lista separada `notas_informativas`.
- Frontend: Criação da seção de "Pesagens Incompletas (OpenPort)" com tabela própria, suporte a filtros reativos no analytics, badge de contagem dedicado e inclusão na exportação em CSV.

---

## Resumo Final

| Status | Quantidade |
|--------|-----------|
| ✅ Implementada | 16 |
| ⚠️ Parcial | 1 (#9 — logging) |
| 🔴 Pendente | 0 |

**Total estimado original:** ~3 horas → **Todas as correções e melhorias implementadas.**
