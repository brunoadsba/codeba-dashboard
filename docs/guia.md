# Guia do Usuário: Dashboard de Auditoria de Pesagens (CODEBA)

Bem-vindo ao guia de utilização do Dashboard de Auditoria de Pesagens. Este documento explica como usar o sistema para conciliar os registros manuais do balanceiro (Excel) com as pesagens automáticas do OpenPort (PDF).

---

## 1. Como Inserir os Dados

1. Acesse o sistema pelo navegador em **http://localhost:8000**
2. Na tela inicial, arraste os arquivos para a área tracejada **ou** clique em "Selecionar Arquivos"
3. Você pode selecionar múltiplos arquivos de uma vez: planilhas `.xlsx` e o relatório `.pdf` do OpenPort
4. Após os arquivos aparecerem na lista, clique em **"Processar Dashboard"**
5. O sistema processa e exibe o painel com os resultados da auditoria

### Arquivos esperados:
- **Planilha da balança (.xlsx):** Registro manual do balanceiro, organizado por produto
- **Relatório OpenPort (.pdf):** Relatório de pesagens automáticas do sistema OpenPort (Tela 7714)

---

## 2. Entendendo os Resultados

### Resumo (KPIs)
- **OK / Total:** Quantas viagens conferem entre Excel e PDF vs. total processado
- **Conformidade:** Percentual de viagens sem divergência
- **Divergências:** Quantidade de registros com diferenças encontradas

### Aba de Pesagens OK
Lista as viagens que conferem entre as duas fontes. Colunas: Placa, Data, Peso Bruto, Tara, Peso Líquido, Produto, PR, SEV (número do romaneio).

### Aba de Divergências
Registros com problemas divididos em categorias:
- **Diferença de Peso:** Mesma placa/data mas pesos diferentes entre Excel e PDF
- **Falta no PDF:** Viagem registrada no Excel mas ausente no relatório OpenPort
- **Falta no Excel:** Viagem do OpenPort que não foi registrada na planilha
- **Erro de Placa:** Placa digitada incorretamente no Excel (detectado por similaridade)

---

## 3. Gráficos Analíticos

### Barras Empilhadas
Mostra o volume em toneladas por data, empilhado por produto. Passe o mouse para ver o detalhe.

### Donut (Distribuição)
Percentual de toneladas por produto no período selecionado.

### Filtros
- **Período:** Clique no badge de data no topo para abrir o calendário. Use os presets (Hoje, 7 dias, 30 dias, Tudo)
- **Placa:** Digite no campo de busca (filtra enquanto digita)
- **Produto:** Selecione um produto específico no dropdown
- **Toggle de Volume:** "Todo o Volume" (inclui divergências com peso) ou "Somente Aprovadas" (só registros OK)

---

## 4. Outras Funcionalidades

### Relatório PDF
Clique em **"Gerar Relatório"** para baixar um PDF com os dados filtrados no momento.

### Histórico
Clique no botão **Histórico** na barra superior para ver auditorias anteriores. Você pode:
- **Carregar:** Restaurar o dashboard com os dados da auditoria selecionada
- **Excluir:** Remover uma auditoria do histórico

### Tema Claro/Escuro
Clique no ícone de Sol/Lua no canto superior direito para alternar entre os temas.

### Substituir Arquivos
Clique em **"Novo Upload"** no topo para voltar à tela inicial e processar novos arquivos.

---

## 5. Dicas

- O **OpenPort (PDF)** é a fonte de verdade primária — os dados automáticos da balança prevalecem sobre a digitação manual do balanceiro
- Uma mesma SEV (romaneio) pode ter múltiplas pesagens (entrada/saída). O sistema agrupa por SEV mantendo a maior pesagem
- O sistema deduz automaticamente o produto de caminhões sem identificação na planilha, baseado no histórico da placa

---

*Dúvidas? Entre em contato com a equipe de desenvolvimento.*
