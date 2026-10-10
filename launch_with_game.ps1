# Starts the lamp sync, then the game command Steam passed in, then stops the sync.
# The game still starts if the lamp script fails.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Log = Join-Path $Root "lamp_sync.log"
$SyncScript = Join-Path $Root "witcher_lamp_sync.py"

function Find-Pythonw {
    $onPath = Get-Command pythonw -ErrorAction SilentlyContinue
    if ($onPath -and (Test-Path -LiteralPath $onPath.Source)) {
        return $onPath.Source
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $sibling = Join-Path (Split-Path -Parent $python.Source) "pythonw.exe"
        if (Test-Path -LiteralPath $sibling) {
            return $sibling
        }
    }
    $candidates = @(
        "$env:LocalAppData\Programs\Python\Python313\pythonw.exe",
        "$env:LocalAppData\Programs\Python\Python312\pythonw.exe",
        "C:\Python313\pythonw.exe",
        "C:\Python312\pythonw.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

$Pythonw = Find-Pythonw

function Write-Log([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $Log -Value $line -Encoding utf8
}

function Test-WitcherRunning {
    return $null -ne (Get-Process -Name "witcher3" -ErrorAction SilentlyContinue)
}

$sync = $null
try {
    if (-not (Test-Path -LiteralPath $Pythonw)) {
        Write-Log "pythonw.exe was not found. Starting the game without the lamp sync."
    } else {
        $sync = Start-Process -FilePath $Pythonw -ArgumentList @($SyncScript) -WorkingDirectory $Root -WindowStyle Hidden -PassThru
        Write-Log "Lamp sync started. pid $($sync.Id)"
    }
} catch {
    Write-Log "Lamp sync did not start: $($_.Exception.Message)"
    $sync = $null
}

if ($args.Count -lt 1 -or [string]::IsNullOrWhiteSpace($args[0])) {
    Write-Log "Steam did not pass a game command."
    if ($sync) { Stop-Process -Id $sync.Id -Force -ErrorAction SilentlyContinue }
    exit 1
}

$exe = $args[0]
$gameArgs = @()
if ($args.Count -gt 1) {
    $gameArgs = $args[1..($args.Count - 1)]
}
Write-Log ("Launching " + $exe)

try {
    if ($gameArgs.Count -gt 0) {
        $game = Start-Process -FilePath $exe -ArgumentList $gameArgs -PassThru -Wait
    } else {
        $game = Start-Process -FilePath $exe -PassThru -Wait
    }
    Write-Log "Launch command exited. code $($game.ExitCode)"
} catch {
    Write-Log "Game launch failed: $($_.Exception.Message)"
    if ($sync) { Stop-Process -Id $sync.Id -Force -ErrorAction SilentlyContinue }
    exit 1
}

# Steam sometimes hands us the RED launcher, which exits after witcher3.exe is running.
$launchedGame = [IO.Path]::GetFileName($exe) -eq "witcher3.exe"
if (-not $launchedGame) {
    $deadline = (Get-Date).AddSeconds(90)
    $sawGame = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-WitcherRunning) {
            $sawGame = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if ($sawGame) {
        Write-Log "Waiting for witcher3.exe to close."
        while (Test-WitcherRunning) {
            Start-Sleep -Seconds 2
        }
    }
}

if ($sync -and -not $sync.HasExited) {
    Stop-Process -Id $sync.Id -Force -ErrorAction SilentlyContinue
    Write-Log "Lamp sync stopped."
}
exit 0
