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
Lista as inconsistências e erros encontrados na conciliação. 

Para manter o painel limpo, os detalhes da divergência ficam ocultos por padrão. **Clique em qualquer parte de uma linha de divergência** para abrir o painel expansível inline:

- **Card de Erro (Borda Vermelha):** Exibe a explicação da falha e, no caso de erros de data, aponta o arquivo, aba, linha e as datas em conflito (Excel vs PDF).
- **Card de Contexto (Borda Verde):** Apresenta o contexto operacional do veículo (viagens OK no dia, produto esperado e a diferença em dias calculada dinamicamente).
- **Ações Rápidas (Rodapé):**
  - **Corrigir Placa:** Aplica a correção de placa sugerida pelo sistema (PDF como fonte primária). *Em desenvolvimento — exibe notificação toast.*
  - **Ignorar:** Mantém a placa original do Excel, descartando a sugestão automática. *Em desenvolvimento — exibe notificação toast.*
  - **Cadastrar viagem:** Cria um registro de viagem para a placa quando não há vínculo. *Em desenvolvimento — abre modal de aviso.*
  - **Marcar como revisado:** Altera o status visual da linha (reduz opacidade, tacha os dados e atualiza o badge para "Revisado") para indicar que a análise já foi feita. O painel é recolhido automaticamente após 450ms.
  - **Abrir no Excel:** Atalho para abrir a planilha manual na aba e linha correspondentes. *Em desenvolvimento — exibe notificação toast.*

> [!NOTE]
> **Ações em desenvolvimento:** Os botões de ação do painel de detalhes ainda não estão conectados ao backend. Ao clicar, o sistema exibe uma notificação toast (ações leves) ou um modal (Cadastrar viagem) informando que a funcionalidade será disponibilizada em breve. Os botões aparecem com opacidade reduzida e exibem tooltip ao passar o mouse.

> [!TIP]
> **Contexto de Multiviagens:** O Card de Contexto (Verde) exibirá se a placa possui viagens bem-sucedidas (OK) no mesmo dia. Se sim, isso é um forte indício de que a pesagem divergente foi simplesmente esquecida na planilha manual de controle do balanceiro.

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

- O **OpenPort (PDF)** é a fonte de verdade primária — os dados automáticos da balança prevalecem sobre a digitação manual do balanceiro.
- **Registros Individuais:** Cada linha do PDF é tratada como uma pesagem individual (sem agrupamento automático por SEV), garantindo que múltiplas viagens legítimas do mesmo caminhão no mesmo dia sejam integralmente auditadas.
- O sistema deduz automaticamente o produto de caminhões sem identificação na planilha, baseado no histórico da placa.

---

*Dúvidas? Entre em contato com a equipe de desenvolvimento.*
