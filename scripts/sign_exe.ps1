# scripts/sign_exe.ps1
# Automatisches Signieren von csv2sepaXml.exe mit einem Authenticode-Zertifikat

param (
    [string]$ExePath = "dist\csv2sepaXml.exe"
)

$ErrorActionPreference = "Stop"

$rootPath = Resolve-Path (Join-Path $PSScriptRoot "..")
$targetExe = Join-Path $rootPath $ExePath

if (-not (Test-Path $targetExe)) {
    Write-Warning "[WARNUNG] Zieldatei nicht gefunden: $targetExe"
    exit 0
}

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " csv2sepaXml - Authenticode Signierung" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Zieldatei: $targetExe"

# 1. Prüfen oder Erstellen des Code-Signing-Zertifikats
$certSubject = "CN=csv2sepaXml, O=the3ver"
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -like "*CN=csv2sepaXml*" } | Select-Object -First 1

if (-not $cert) {
    Write-Host "Erstelle neues lokales Code-Signing-Zertifikat..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate -Type CodeSigningCert `
        -Subject $certSubject `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(5) `
        -FriendlyName "csv2sepaXml OpenSource Signer"
    Write-Host "Neues Zertifikat erstellt (Thumbprint: $($cert.Thumbprint))" -ForegroundColor Green
} else {
    Write-Host "Vorhandenes Zertifikat verwendet (Thumbprint: $($cert.Thumbprint))" -ForegroundColor Green
}

# 2. Authenticode-Signatur anwenden (mit Timestamp-Fallback)
Write-Host "Signiere $targetExe..." -ForegroundColor Yellow
$timestampUrls = @(
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com"
)

$signed = $false
foreach ($tsUrl in $timestampUrls) {
    try {
        $res = Set-AuthenticodeSignature -FilePath $targetExe -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $tsUrl -ErrorAction Stop
        if ($res.Status -eq "Valid" -or $res.Status -eq "UnknownError") {
            Write-Host "Erfolgreich signiert mit Zeitstempel ($tsUrl)." -ForegroundColor Green
            $signed = $true
            break
        }
    } catch {
        # Fallback zum nächsten Zeitstempel-Server
    }
}

if (-not $signed) {
    Write-Host "Signiere ohne externen Zeitstempel-Server (Offline-Modus)..." -ForegroundColor Yellow
    $res = Set-AuthenticodeSignature -FilePath $targetExe -Certificate $cert -HashAlgorithm SHA256
    Write-Host "Signatur angewendet." -ForegroundColor Green
}

# 3. Öffentliches Zertifikat (.cer) nach dist/ exportieren
$distDir = Split-Path $targetExe -Parent
$cerPath = Join-Path $distDir "csv2sepaXml.cer"
try {
    Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null
    Write-Host "Öffentliches Zertifikat exportiert: $cerPath" -ForegroundColor Cyan
} catch {
    Write-Warning "Zertifikat-Export fehlgeschlagen: $_"
}

Write-Host "Signierungsstatus der EXE:" -ForegroundColor Cyan
Get-AuthenticodeSignature $targetExe | Format-Table -AutoSize
Write-Host "Signierung abgeschlossen." -ForegroundColor Green
