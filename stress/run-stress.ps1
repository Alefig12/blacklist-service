# Ejecuta la prueba de estrés de k6 contra el ALB de Fargate usando la imagen oficial de k6 en Docker.
#   .\stress\run-stress.ps1                  # perfil smoke (30 s, 2 usuarios)
#   .\stress\run-stress.ps1 -Perfil stress   # rampa completa hasta 100 usuarios (~11 min)
# El token se genera en memoria con el JWT_SECRET_KEY de SSM: no se imprime ni se guarda en disco.
param(
    [ValidateSet('smoke', 'stress')] [string] $Perfil = 'smoke',
    [string] $BaseUrl = 'http://blacklist-alb-1898589174.us-east-2.elb.amazonaws.com'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

$env:JWT_SECRET_KEY = aws ssm get-parameter --region us-east-2 --name /blacklist-service/JWT_SECRET_KEY `
    --with-decryption --query Parameter.Value --output text
try { $token = (python (Join-Path $repo 'scripts/generate_token.py')).Trim() }
finally { Remove-Item Env:JWT_SECRET_KEY }

$results = Join-Path $PSScriptRoot 'results'
New-Item -ItemType Directory -Force $results | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

Write-Host "Prueba '$Perfil' contra $BaseUrl (inicio $(Get-Date -Format 'HH:mm:ss'))"
docker run --rm -i `
    -v "${PSScriptRoot}:/scripts" `
    -e BASE_URL=$BaseUrl -e PROFILE=$Perfil -e TOKEN=$token `
    grafana/k6:1.2.0 run --summary-export "/scripts/results/$Perfil-$stamp.json" /scripts/blacklist-stress.js
Write-Host "Fin $(Get-Date -Format 'HH:mm:ss'). Resumen en stress/results/$Perfil-$stamp.json"
