param (
    [int]$ApiPort = 8000,
    [int]$UiPort = 4200,
    [switch]$Unified,
    [switch]$NoNewWindow
)

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$noWindow = $Unified -or $NoNewWindow

& "$rootDir\start_local.ps1" -ApiPort $ApiPort -UiPort $UiPort -NoNewWindow:$noWindow
