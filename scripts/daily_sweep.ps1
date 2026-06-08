# OB.1 daily read sweep runner. Registered in Windows Task Scheduler.
# Reads only; zero credit risk. Digest lands in verification\ and the Drive folder.
# Order matters: mirror sync first so the sweep's drift section reflects post-sync state.
$ErrorActionPreference = "Stop"
$env:AUDITY_TOKEN = [Environment]::GetEnvironmentVariable("AUDITY_TOKEN", "User")
$env:OBN_SUPABASE_URL = [Environment]::GetEnvironmentVariable("OBN_SUPABASE_URL", "User")
$env:OBN_SUPABASE_SERVICE_KEY = [Environment]::GetEnvironmentVariable("OBN_SUPABASE_SERVICE_KEY", "User")
$env:OBN_SYNC_SCOPE = [Environment]::GetEnvironmentVariable("OBN_SYNC_SCOPE", "User")
$env:OBN_TEST_CLIENT_PREFIXES = [Environment]::GetEnvironmentVariable("OBN_TEST_CLIENT_PREFIXES", "User")
Set-Location "$env:USERPROFILE\repos\OB-Nucleus"
python -m ob_nucleus.cli mirror sync | Out-Null
python -m ob_nucleus.cli sweep run | Out-Null
$latest = Get-ChildItem "verification\read_sweep_*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$drive = "G:\Shared drives\OB.1 Business Docs\05_TECHNICAL_DEVELOPMENT\Audity_Integration\OB-Nucleus"
if (Test-Path $drive) { Copy-Item $latest.FullName (Join-Path $drive $latest.Name) -Force }
Add-Content -Path "verification\sweep_schedule.log" -Value "$(Get-Date -Format o) mirror sync + sweep ok"
