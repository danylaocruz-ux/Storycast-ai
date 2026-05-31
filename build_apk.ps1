# ============================================================
#  StoryCast AI — Build APK automático (Windows)
#  Execute no PowerShell como Administrador:
#  Set-ExecutionPolicy Bypass -Scope Process; .\build_apk.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

function Log($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)  { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Err($msg) { Write-Host "  ✗ $msg" -ForegroundColor Red; exit 1 }

# ── 1. Verifica / instala Flutter ──────────────────────────────────────────
Log "Verificando Flutter..."
$flutterCmd = Get-Command flutter -ErrorAction SilentlyContinue

if (-not $flutterCmd) {
    Log "Flutter não encontrado. Baixando Flutter SDK..."
    $flutterZip = "$env:TEMP\flutter_windows.zip"
    $flutterDir = "$env:LOCALAPPDATA\flutter"

    if (-not (Test-Path $flutterDir)) {
        $url = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.19.6-stable.zip"
        Write-Host "  Baixando $url" -ForegroundColor Yellow
        Write-Host "  (pode demorar alguns minutos...)"
        Invoke-WebRequest -Uri $url -OutFile $flutterZip -UseBasicParsing
        Write-Host "  Extraindo..."
        Expand-Archive -Path $flutterZip -DestinationPath "$env:LOCALAPPDATA" -Force
        Remove-Item $flutterZip -Force
    }

    # Adiciona flutter ao PATH desta sessão
    $env:PATH = "$flutterDir\bin;$env:PATH"
    $flutterCmd = "$flutterDir\bin\flutter.bat"
    Ok "Flutter instalado em $flutterDir"
} else {
    Ok "Flutter encontrado: $(flutter --version 2>&1 | Select-String 'Flutter' | Select-Object -First 1)"
}

# ── 2. Verifica Java ───────────────────────────────────────────────────────
Log "Verificando Java..."
try {
    $javaVer = java -version 2>&1 | Select-Object -First 1
    Ok "Java: $javaVer"
} catch {
    Write-Host "  Java não encontrado. Instalando via winget..." -ForegroundColor Yellow
    winget install Microsoft.OpenJDK.17 --silent --accept-package-agreements --accept-source-agreements
    $env:PATH = "$env:ProgramFiles\Microsoft\jdk-17*\bin;$env:PATH"
}

# ── 3. Localiza Android SDK ────────────────────────────────────────────────
Log "Procurando Android SDK..."
$androidSdk = $null

$candidates = @(
    "$env:LOCALAPPDATA\Android\Sdk",
    "$env:USERPROFILE\AppData\Local\Android\Sdk",
    "C:\Android\Sdk",
    "$env:LOCALAPPDATA\flutter\bin\cache\artifacts\android"
)

foreach ($c in $candidates) {
    if (Test-Path "$c\build-tools") {
        $androidSdk = $c
        Ok "Android SDK encontrado em $androidSdk"
        break
    }
}

if (-not $androidSdk) {
    Write-Host "  Android SDK não encontrado — flutter doctor vai configurar automaticamente." -ForegroundColor Yellow
    Write-Host "  Rodando flutter doctor..."
    & flutter doctor --android-licenses 2>&1 | ForEach-Object { Write-Host "  $_" }
}

# ── 4. Configura projeto ───────────────────────────────────────────────────
$mobileDir = Join-Path $ROOT "storycast_ai\mobile"
if (-not (Test-Path $mobileDir)) {
    Err "Pasta storycast_ai\mobile não encontrada. Certifique-se de que este script está na raiz do projeto extraído."
}

Log "Instalando dependências Flutter..."
Set-Location $mobileDir
& flutter pub get
if ($LASTEXITCODE -ne 0) { Err "flutter pub get falhou" }
Ok "Dependências instaladas"

# ── 5. Aceita licenças Android ─────────────────────────────────────────────
Log "Aceitando licenças Android..."
"y`ny`ny`ny`ny`ny`n" | flutter doctor --android-licenses 2>&1 | Out-Null

# ── 6. Build APK ───────────────────────────────────────────────────────────
Log "Compilando APK (pode demorar 3-5 minutos)..."
& flutter build apk --split-per-abi --release
if ($LASTEXITCODE -ne 0) { Err "Build falhou. Rode 'flutter doctor' para diagnosticar." }

# ── 7. Copia APK para raiz ─────────────────────────────────────────────────
Log "Copiando APK..."
$apkSource = Join-Path $mobileDir "build\app\outputs\flutter-apk"
$apkDest   = Join-Path $ROOT "StoryCast_AI.apk"

# Copia o APK arm64 (compatível com 99% dos celulares modernos)
$arm64 = Get-ChildItem $apkSource -Filter "*arm64*release*" | Select-Object -First 1
if ($arm64) {
    Copy-Item $arm64.FullName $apkDest -Force
    Ok "APK gerado: $apkDest"
    Ok "Tamanho: $([math]::Round($arm64.Length / 1MB, 1)) MB"
} else {
    # Fallback: copia o APK universal
    $universal = Get-ChildItem $apkSource -Filter "*release*" | Select-Object -First 1
    if ($universal) {
        Copy-Item $universal.FullName $apkDest -Force
        Ok "APK gerado: $apkDest"
    } else {
        Err "APK não encontrado em $apkSource"
    }
}

# ── 8. Resumo ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  APK PRONTO: StoryCast_AI.apk" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para instalar no celular:" -ForegroundColor White
Write-Host "  1. Transfira StoryCast_AI.apk para o celular (WhatsApp, cabo USB, etc)"
Write-Host "  2. No celular: Configuracoes > Seguranca > Fontes desconhecidas (ativar)"
Write-Host "  3. Abra o arquivo .apk no celular e instale"
Write-Host ""
Write-Host "Lembre de iniciar o backend antes de usar o app:" -ForegroundColor Yellow
Write-Host "  cd storycast_ai\backend"
Write-Host "  pip install -r requirements.txt"
Write-Host "  uvicorn app.main:app --host 0.0.0.0 --port 8000"
Write-Host ""

Set-Location $ROOT
