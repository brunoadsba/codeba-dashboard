$ErrorActionPreference = "Continue"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   Automacao de Setup - CODEBA Dashboard" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Verifica se o Python está disponível e funcional
Write-Host "`n[1/4] Verificando instalacao do Python..." -ForegroundColor Yellow
$pythonCmd = "python"
$pythonOk = $false

try {
    # O stub do Windows Store falha ou não retorna a versão certa
    $versionOutput = & $pythonCmd --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $versionOutput -match "Python 3") {
        $pythonOk = $true
    }
} catch {
    $pythonOk = $false
}

if (-not $pythonOk) {
    Write-Host "Python ausente ou quebrado. Tentando instalar Python 3.12 via winget..." -ForegroundColor Magenta
    winget install -e --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
    
    Write-Host "Atualizando variaveis de ambiente da sessao atual..." -ForegroundColor Yellow
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    # Testa novamente
    try {
        $versionOutput = & $pythonCmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $versionOutput -match "Python 3") {
            $pythonOk = $true
        }
    } catch {
        $pythonOk = $false
    }
    
    if (-not $pythonOk) {
        Write-Host "AVISO: O Python foi instalado, mas nao esta acessivel nesta sessao do terminal." -ForegroundColor Red
        Write-Host "Por favor, reinicie o VS Code / Terminal e rode este script novamente." -ForegroundColor Red
        exit 1
    }
}

Write-Host "OK! Python disponivel: $versionOutput" -ForegroundColor Green

# 2. Remover o .venv quebrado se existir
Write-Host "`n[2/4] Verificando ambiente virtual (.venv)..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "Removendo ambiente virtual antigo/quebrado..." -ForegroundColor Magenta
    Remove-Item -Recurse -Force .venv
    Write-Host "Ambiente antigo removido." -ForegroundColor Green
}

# 3. Criar novo ambiente
Write-Host "`n[3/4] Criando um novo ambiente virtual limpo..." -ForegroundColor Yellow
& $pythonCmd -m venv .venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Erro ao criar o ambiente virtual." -ForegroundColor Red
    exit 1
}
Write-Host "Ambiente virtual criado com sucesso!" -ForegroundColor Green

# 4. Instalar dependências
Write-Host "`n[4/4] Instalando pacotes do requirements.txt..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "`n==============================================" -ForegroundColor Cyan
Write-Host " TUDO PRONTO! Iniciando o servidor..." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan

.\.venv\Scripts\python.exe -m uvicorn src.app:app --reload --port 8000
