<#
Monitorea un despliegue consultando GET /ping cada medio segundo.

Guarda cada respuesta (hora, estado, versión, instancia) en deploy-logs/<nombre>.csv
y, al detenerlo con Ctrl+C, imprime un resumen: errores, primera y última respuesta
de cada versión y cuántas respuestas dio cada instancia.

Uso (PowerShell, desde la raíz del repo):
    .\scripts\monitor_deploy.ps1 -Name 2a-allatonce
#>
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Url = "http://blacklist-env.eba-uiks4ffx.us-east-2.elasticbeanstalk.com/ping",
    [int]$IntervalMs = 500
)

$dir = Join-Path $PSScriptRoot "..\deploy-logs"
New-Item -ItemType Directory -Force $dir | Out-Null
$log = Join-Path $dir "$Name.csv"
"hora,estado,version,host" | Set-Content $log
Write-Host "Registrando en $log  (Ctrl+C para terminar y ver el resumen)`n"

try {
    while ($true) {
        $t = Get-Date -Format "HH:mm:ss"
        try {
            $r = Invoke-RestMethod $Url -TimeoutSec 3
            $line = "$t,OK,$($r.version),$($r.host)"
            Write-Host $line
        }
        catch {
            $code = $_.Exception.Response.StatusCode.value__
            if (-not $code) { $code = "timeout" }
            $line = "$t,ERROR-$code,,"
            Write-Host $line -ForegroundColor Red
        }
        $line | Add-Content $log
        Start-Sleep -Milliseconds $IntervalMs
    }
}
finally {
    $d = Import-Csv $log
    $errors = @($d | Where-Object estado -ne "OK")
    Write-Host "`n===== Resumen: $Name ====="
    Write-Host "Respuestas: $($d.Count)   Errores: $($errors.Count)"
    if ($errors.Count) {
        Write-Host "Primer error: $($errors[0].hora)   Último error: $($errors[-1].hora)"
        $errors | Group-Object estado | ForEach-Object { Write-Host "  $($_.Name): $($_.Count)" }
    }
    Write-Host "`nVersiones (primera y última respuesta):"
    $d | Where-Object version | Group-Object version | ForEach-Object {
        Write-Host "  v$($_.Name): $($_.Group[0].hora) -> $($_.Group[-1].hora)  ($($_.Count) respuestas)"
    }
    Write-Host "`nRespuestas por instancia y versión:"
    $d | Where-Object host | Group-Object host, version |
        Select-Object Count, Name | Format-Table -AutoSize | Out-String | Write-Host
}
