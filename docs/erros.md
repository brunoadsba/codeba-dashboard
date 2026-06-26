# Relatório de Erros — Motor de Conciliação CODEBA

> **Última atualização:** 2026-06-19 — Status de cada erro verificado contra o código-fonte atual.

---

## 🔴 Críticos

### ✅ ERRO #1 — Agrupamento por SEV destrói viagens legítimas (CORRIGIDO em v4.2.0)
- **Arquivo:** `src/services/reconciliation.py`
- **Tipo:** Lógica de agrupamento incorreta
- **Impacto:** ALTO — Perda de registros sem aviso

**Descrição:** O código agrupava todas as linhas do PDF que compartilhavam o mesmo SEV usando `groupby('SEV')` com `agg({'Peso Bruto': 'max', 'Tara': 'max'})`. Se o OpenPort gerasse duas pesagens para o mesmo SEV (ex: caminhão carregado na ida e descarregado na volta), o sistema colapsava ambas em UM único registro.

**Correção aplicada:** Removido o bloco `groupby('SEV')`. Cada linha do PDF agora é tratada como um registro individual. O SEV é mantido como campo informativo, sem agrupamento. Diagnóstico de SEVs com 3+ registros preservado via log.

---

### ✅ ERRO #2 — Match por aproximação sem limite de tolerância (CORRIGIDO em v4.1.0)
- **Arquivo:** `src/services/reconciliation.py`
- **Tipo:** Falta de validação
- **Impacto:** ALTO — Divergências fictícias

**Descrição:** No "Match por Aproximação", o código pegava o par mais próximo independentemente da diferença de peso.

**Correção aplicada:** Adicionado `TOLERANCIA_MAXIMA_KG = 5000`. Se a diferença exceder a tolerância, o registro não é forçadamente pareado — Excel vira "Falta no PDF" e PDF vira "Falta no Excel".

---

## 🟡 Alta

### ✅ ERRO #3 — Parsing do nome do arquivo quebra o produto (CORRIGIDO em v4.0.0)
- **Arquivo:** `src/utils/filename_parser.py`
- **Tipo:** Algoritmo frágil
- **Impacto:** ALTO — Produto incorreto → matching errado

**Correção aplicada:** `extract_produto_from_filename()` agora busca produtos conhecidos (`PRODUTOS_CONHECIDOS`) no nome do arquivo via substring, com fallback para a lógica antiga.

---

### ✅ ERRO #4 — Peso Líquido ignorado no matching (CORRIGIDO em v4.1.0)
- **Arquivo:** `src/services/reconciliation.py`
- **Tipo:** Critério insuficiente
- **Impacto:** ALTO — Matching incorreto entre Excel e PDF

**Correção aplicada:** Peso Líquido é usado como critério de desempate no Match por Aproximação (linhas 166-172 do reconciliation.py).

---

### ✅ ERRO #5 — Correção de typos assume direção fixa (CORRIGIDO em v4.0.0)
- **Arquivo:** `src/services/post_processing.py`
- **Tipo:** Viés de implementação
- **Impacto:** ALTO — Erro de placa não detectado na direção oposta

**Correção aplicada:** A função `detect_plate_typos` agora valida o formato Mercosul de ambas as placas (`_is_valid_mercosul_format`) para determinar qual é a correta.

---

## 🔵 Média

### ✅ ERRO #6 — Datas inválidas são engolidas sem aviso (CORRIGIDO em v4.0.0)
- **Arquivo:** `src/services/excel_parser.py` e `pdf_parser.py`
- **Tipo:** Silêncio em erro de parsing
- **Impacto:** MÉDIO — Registros somem sem explicação

**Correção aplicada:** Ambos os parsers agora logam `logger.warning("X data(s) inválida(s) ignorada(s)")` quando datas são rejeitadas.

---

### ✅ ERRO #7 — Placas com acentos perdidas na limpeza (CORRIGIDO em v4.0.0)
- **Arquivo:** `src/utils/cleaners.py`
- **Tipo:** Limpeza excessiva
- **Impacto:** MÉDIO — Placas corrompidas silenciosamente

**Correção aplicada:** `clean_placa()` agora usa `unicodedata.normalize('NFKD')` + encode ASCII antes do regex, convertendo "ÁBCD123" → "ABCD123" em vez de "BCD123".

---

### ✅ ERRO #8 — Desduplicação pode eliminar viagens legítimas (CORRIGIDO em v3.2.2)
- **Arquivo:** `src/services/pdf_parser.py`
- **Tipo:** Critério insuficiente
- **Impacto:** MÉDIO — Viagens reais tratadas como duplicatas

**Correção aplicada:** Chave de desduplicação ampliada de `['Data', 'Peso Bruto', 'Tara']` para `['Placa', 'Data', 'Peso Bruto', 'Tara']`.

---

### ✅ ERRO #9 — Header Hunting limitado a 20 linhas (CORRIGIDO em v4.0.0)
- **Arquivo:** `src/services/excel_parser.py`
- **Tipo:** Limite arbitrário
- **Impacto:** MÉDIO — Planilhas com cabeçalho extenso são ignoradas

**Correção aplicada:** Limite aumentado para 50 linhas (`df_raw.head(50)`).

---

### ✅ ERRO #10 — Logging e Auditoria de descartes insuficiente para diagnóstico (CORRIGIDO em v4.6.0)
- **Arquivo:** Todos os módulos
- **Tipo:** Falta de observabilidade
- **Impacto:** MÉDIO — Impossível rastrear onde o pipeline quebrou

**Correção aplicada:** O motor de conciliação agora mapeia detalhadamente todos os registros descartados por placa/data corrompidos ou em branco, e retorna de forma estruturada em `avisos.registros_descartados`. Esses dados são exibidos de forma interativa e colapsável no dashboard, permitindo auditoria forense imediata sobre a qualidade dos arquivos de entrada.

---

### ✅ ERRO #11 — Coluna Tipo Carga do PDF retorna "Não" como produto (CORRIGIDO em v4.1.0)
- **Arquivo:** `src/services/reconciliation.py`
- **Tipo:** Dado não informativo propagado para o Detalhe
- **Impacto:** ALTO — Confunde o usuário

**Correção aplicada:** O valor de `Tipo Carga` é validado: se for "Não", "N", vazio, "Desconhecido" ou "NaN", é omitido do texto do Detalhe.

---

### ✅ ERRO #12 — Tabela com overflow:hidden trunca dados do usuário (CORRIGIDO em v4.1.0)
- **Arquivo:** `static/css/style.css`
- **Tipo:** CSS bloqueando visibilidade dos dados
- **Impacto:** MÉDIO — Dados aparecem truncados com "..."

**Correção aplicada:** `overflow: hidden` e `text-overflow: ellipsis` removidos do `.audit-table td`. Substituídos por `word-wrap: break-word` + `min-width` em pixels fixos.

---

### ✅ ERRO #13 — Muitas colunas na tabela causam compressão extrema (CORRIGIDO em v4.1.0)
- **Arquivo:** `static/index.html`, `static/js/app.js`, `static/css/style.css`
- **Tipo:** Layout sobrecarregado
- **Impacto:** MÉDIO — Dados desalinhados e ilegíveis

**Correção aplicada:** Tabela reduzida de 11 para 7 colunas: SEV, Placa, Data, Produto, Pesos (Bruto/Tara/Líq.), Status, Detalhe. Colunas de peso fundidas em uma única coluna monospace.

---

### ✅ ERRO #14 — Ambiguidade visual em placas com múltiplas viagens no mesmo dia (CORRIGIDO em v4.3.0)
- **Arquivos:** `src/services/reconciliation.py`, `static/js/app.js`, `static/css/style.css`
- **Tipo:** Usabilidade / Interface de Usuário
- **Impacto:** MÉDIO — Dúvidas do operador ao identificar placas marcadas como divergentes que já possuíam viagens válidas (OK).

**Descrição:** Para veículos com mais de uma viagem no mesmo dia (ex: `RPJ0I50` em 18/06/2026), se uma viagem era bem-sucedida (OK) e a outra faltava no Excel ("Falta no Excel"), a divergência era exibida de forma isolada. Isso causava confusão se a importação do veículo havia falhado de alguma forma.

**Correção aplicada:** Backend agora computa e injeta `viagens_ok_no_dia: count` no dicionário do registro divergente. O frontend lê essa flag e adiciona um badge informativo `💡 Placa com X viagem(ns) OK neste dia. Verifique se esta pesagem foi esquecida.` na coluna Detalhe, clarificando que a linha se refere a uma segunda pesagem esquecida.

---

### ✅ ERRO #15 — UnboundLocalError ao gerar divergência 'Falta no PDF' (CORRIGIDO em v4.3.0)
- **Arquivo:** `src/services/reconciliation.py`
- **Tipo:** Bug de execução (Runtime Error)
- **Impacto:** ALTO — Interrompia o motor de conciliação durante a execução de testes ou processamento quando havia registros ausentes no PDF.

**Descrição:** O código tentava incluir a chave `'PR': pr` ao criar o dicionário de divergência do tipo `Falta no PDF`. No entanto, o objeto `pr` só era inicializado dentro da condição `if best_p_idx != -1:` (onde uma correspondência era encontrada). Se a correspondência não existisse (caso do "Falta no PDF"), o Python lançava uma exceção `UnboundLocalError: local variable 'pr' referenced before assignment`.

**Correção aplicada:** Substituída a referência à chave descontinuada `'PR': pr` por `'Peso Liquido': ex['Peso Bruto'] - ex['Tara']` (conforme refatorações de SEV e remoção de Cliente/PR), eliminando a referência à variável não-declarada `pr`.

---

### ✅ ERRO #16 — Pesagens incompletas no OpenPort (Tara=0) gerando falsas divergências (CORRIGIDO em v4.5.0)
- **Arquivos:** `src/services/pdf_parser.py`, `src/services/reconciliation.py`
- **Tipo:** Regra de negócio / Falso Positivo
- **Impacto:** ALTO — Veículos parados temporariamente na balança registravam `Tara=0` e eram marcados como divergências ("Falta no Excel"), poluindo os relatórios com falsos positivos.

**Descrição:** O OpenPort grava um registro inicial com `Tara=0` antes de concluir a pesagem em definitivo. Se a pesagem for completada com sucesso na mesma data, ambos os registros ficavam no PDF. O motor comparava a pesagem incompleta (`Tara=0`) com a planilha, gerando uma divergência "Falta no Excel".

**Correção aplicada:**
1. Filtragem inteligente no PDF Parser: Remove registros parciais com `Tara=0` quando há um registro correspondente completo no mesmo dia.
2. Pós-processamento na reconciliação: Registros remanescentes com `Tara=0` que possuam viagens OK associadas no dia são reclassificados como "Pesagem Incompleta" e movidos para uma lista de notas informativas, mantendo as divergências zeradas.

---

## Resumo

| Status | Quantidade |
|--------|-----------|
| ✅ Corrigido | 16 |
| ⚠️ Parcial | 0 |
| 🔴 Pendente | 0 |
