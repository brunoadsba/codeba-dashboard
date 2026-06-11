# CODEBA — Dashboard de Auditoria de Pesagens (v3.0.0)

Este projeto realiza a **conciliação e auditoria de pesagens rodoviárias** comparando os manifestos da CODEBA (origem Excel) com os registros do OpenPort (saída PDF). Ele identifica automaticamente divergências de peso, placas digitadas incorretamente no Excel e deduce o produto com base no histórico do caminhão.

---

## 🏗️ Estrutura do Projeto

O projeto foi reorganizado seguindo boas práticas da indústria, como **Clean Architecture**, **12-Factor App** e **Separation of Concerns**:

```
operacao/
├── pyproject.toml              # Metadados do projeto e configurações de ferramentas (PEP 518)
├── .gitignore                  # Regras de exclusão do Git
├── .env.example                # Configurações de ambiente (12-Factor App)
├── README.md                   # Esta documentação
├── requirements.txt            # Dependências em formato legacy para compatibilidade
│
├── src/                        # Código-fonte principal da aplicação
│   ├── __init__.py
│   ├── app.py                  # Servidor FastAPI (Rotas e Middleware)
│   ├── config.py               # Constantes e caminhos de forma portátil e segura
│   ├── logging_config.py       # Configuração única e unificada de logs (dictConfig)
│   │
│   ├── services/               # Lógica de negócio e processamento de dados (ETL)
│   │   ├── __init__.py
│   │   ├── excel_parser.py     # Parser inteligente de planilhas com Header Hunting
│   │   ├── pdf_parser.py       # Parser de relatórios do OpenPort em PDF
│   │   ├── reconciliation.py   # Motor principal de reconciliação de viagens
│   │   └── post_processing.py  # Corretores de placas e dedução de produtos
│   │
│   └── utils/                  # Utilitários puros
│       ├── __init__.py
│       ├── cleaners.py         # Limpeza e sanitização de placas e números
│       └── filename_parser.py  # Extração de dados com base nos nomes de arquivos
│
├── static/                     # Frontend (HTML, CSS e JavaScript puro)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
│
├── data/                       # Arquivos de dados de referência
│   ├── excel/                  # Planilhas da CODEBA por produto
│   └── relatorios/             # PDFs de pesagem do OpenPort
│
├── tests/                      # Suite de testes automatizados
│   ├── __init__.py
│   ├── conftest.py             # Fixtures globais do pytest
│   └── test_e2e.py             # Testes integrados de ponta a ponta
│
├── scripts/                    # Scripts auxiliares e automações
│   ├── rpa_codeba.py           # Robô RPA de download automático
│   └── diagnostics/            # Scripts de diagnóstico e debug
│
├── logs/                       # Arquivos de log de execução
└── temp_uploads/               # Diretório temporário para processamento de uploads
```

---

## 🚀 Como Executar

### 1. Preparar o Ambiente

Certifique-se de ter o Python 3.10+ instalado. No diretório `operacao/`:

1. Crie o ambiente virtual:
   ```bash
   python -m venv .venv
   ```
2. Ative o ambiente virtual:
   * **Windows:** `.\.venv\Scripts\activate`
   * **Linux/Mac:** `source .venv/bin/activate`
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Crie o arquivo `.env` com base no `.env.example`:
   ```bash
   copy .env.example .env
   ```

### 2. Iniciar o Servidor

Execute o servidor localmente por meio do módulo Uvicorn:

```bash
python -m uvicorn src.app:app --reload --port 8000
```

O painel estará disponível em [http://localhost:8000](http://localhost:8000).

---

## 🧪 Rodando os Testes

O projeto utiliza o **Pytest** para testes integrados. Para rodar a suite de testes inteira:

```bash
python -m pytest tests/ -v
```

---

## 🛡️ Segurança

* **Prevenção de Path Traversal:** Os arquivos enviados por upload são salvos temporariamente sob nomes gerados por `uuid.uuid4()`.
* **Sanitização contra XSS:** O frontend renderiza todos os dados dinâmicos construindo nós nativos do DOM com `.textContent` e `.appendChild`, evitando o uso perigoso de `innerHTML`.
* **Validação de Tamanho e Extensões:** O backend rejeita arquivos maiores que 50MB ou com extensões que não estejam na allow-list (`.xlsx`, `.xls`, `.pdf`).
* **Tratamento de Arquivos Locais:** Limpeza sistemática dos arquivos temporários após o processamento, incluindo tratamento específico para locks de arquivo no sistema de arquivos do Windows.
