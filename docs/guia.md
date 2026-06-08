# Guia do Usuário: Dashboard de Movimentação Portuária (CODEBA)

Bem-vindo ao guia de utilização do seu novo Dashboard de Movimentação Portuária. Este documento foi criado para explicar de forma simples e direta como utilizar o sistema e o que cada informação na tela significa.

---

## 1. Como Iniciar e Inserir Dados no Sistema

O sistema foi projetado para ser muito simples e não exige conhecimentos técnicos. Ele lê as planilhas Excel e PDFs gerados pela CODEBA e transforma esses números em gráficos automáticos.

**Passo a passo para usar:**
1. Ao acessar o sistema (pelo navegador de internet), você verá uma tela de "Upload" (Envio de arquivos).
2. **Arraste e solte** os arquivos (Planilhas Excel `.xlsx` e Relatórios OpenPort em `.pdf`) na área tracejada da tela. Você pode jogar vários arquivos de uma vez.
3. Se preferir, clique no botão **"Selecionar Arquivos"** e escolha os documentos no seu computador.
4. Após os arquivos aparecerem na lista, clique no botão **"Processar Dashboard"**.
5. Aguarde alguns segundos. O sistema vai organizar tudo e a tela do painel vai aparecer!

---

## 2. Entendendo os Indicadores Principais (KPIs)

Na parte de cima da tela, logo abaixo do cabeçalho, você verá o **Resumo do Mês**. Esses são os "termômetros" da sua operação:

*   **Entradas (Seta Verde):** Mostra o total de toneladas (`t`) de mercadoria que *chegou* e foi registrada nas planilhas/PDFs fornecidos.
*   **Saídas (Seta Vermelha):** Mostra o total de toneladas que *saiu* do porto. *(Nota: Nesta versão inicial, o foco principal de processamento está em Entradas e Saldo).*
*   **Saldo em Estoque (Seta Azul):** É a quantidade total de mercadorias armazenadas atualmente, consolidando tudo o que entrou menos o que saiu.

---

## 3. Entendendo os Gráficos

O Dashboard conta com dois gráficos principais para te ajudar a entender a operação visualmente:

### Gráfico 1: Evolução do Saldo por Mercadoria (Gráfico de Linhas)
*   **O que ele mostra?** Ele desenha uma linha do tempo mostrando como o estoque de cada tipo de mercadoria cresceu ou diminuiu ao longo dos dias.
*   **Como ler?** Se a linha sobe, o estoque daquela mercadoria aumentou naqueles dias. Se a linha fica reta, não houve movimentação.
*   **Interação:** Você pode passar o mouse (ou o dedo, no celular) por cima das linhas para ver a quantidade exata de estoque em um dia específico.

### Gráfico 2: Distribuição do Saldo (Gráfico de Barras Horizontais)
*   **O que ele mostra?** Um "raio-x" do estoque atual. Ele divide o bolo total e te mostra qual mercadoria ocupa mais espaço hoje.
*   **Como ler?** A barra mais longa é a mercadoria que você tem em maior quantidade armazenada.
*   **Aba "Por Mercadoria":** Mostra o total por tipo de produto (ex: Manganês, Milho, Lítio).

---

## 4. Funcionalidades Extras

*   **Trocar Tema (Claro/Escuro):** No canto superior direito, clique no ícone do **Sol** ou da **Lua** para mudar a cor de fundo do painel. Excelente para descansar os olhos à noite ou para apresentar em telões mais claros.
*   **Substituir Arquivos:** Se você esquecer de colocar uma planilha ou colocar o arquivo errado, não se preocupe! Basta clicar em **"Substituir Arquivo"** no topo da tela para voltar à tela inicial e jogar os arquivos corretos.

---
*Dúvidas? Entre em contato com a equipe de desenvolvimento. Este é um MVP (Produto Mínimo Viável) e está em constante evolução para atender as necessidades do Porto.*
