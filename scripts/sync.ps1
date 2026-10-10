# sync.ps1 - copy the skills from the local cc-switch library into this repo,
# laid out by category, with personal identifiers scrubbed.
#
# Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync.ps1
#
# Never deletes files: NOTICE.md and your own additions in the target skill
# folders survive. After running, review with `git status` / `git diff` and
# commit only what you intend to publish.
#
# Encoding note: PowerShell 5.1's Get-Content defaults to the ANSI codepage,
# which silently mangles UTF-8 Chinese text. Every read/write here therefore
# goes through explicit System.Text.Encoding::UTF8 with no BOM.

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$mapPath  = Join-Path $PSScriptRoot 'map.json'
$map = Get-Content -Raw -Encoding UTF8 $mapPath | ConvertFrom-Json

$source = Join-Path $env:USERPROFILE $map.sourceRoot
if (-not (Test-Path $source)) { throw "source skill library not found: $source" }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$textExt = @($map.textExtensions)
$copied = 0; $scrubbedFiles = 0; $remaining = 0; $missing = @()

foreach ($cat in $map.categories.PSObject.Properties) {
  $catName = $cat.Name
  $dest    = Join-Path $repoRoot $catName
  New-Item -ItemType Directory -Force -Path $dest | Out-Null

  foreach ($skill in $cat.Value) {
    $src = Join-Path $source $skill
    if (-not (Test-Path $src)) { $missing += "$catName/$skill"; continue }
    $dst = Join-Path $dest $skill

    Get-ChildItem -LiteralPath $src -Recurse -File | ForEach-Object {
      $rel = $_.FullName.Substring($src.Length).TrimStart('\','/')
      $target = Join-Path $dst $rel
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
      Copy-Item -LiteralPath $_.FullName -Destination $target -Force
      $copied++
    }

    Get-ChildItem -LiteralPath $dst -Recurse -File | ForEach-Object {
      if ($textExt -notcontains $_.Extension.ToLower()) { return }
      $raw = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
      $new = $raw
      foreach ($pair in $map.scrub) {
        $needle = [string]$pair[0]
        if ($new.Contains($needle)) { $new = $new.Replace($needle, [string]$pair[1]) }
      }
      # normalize to LF so a .sh stays runnable on Linux and diffs stay quiet
      $new = $new.Replace("`r`n", "`n")
      if ($new -ne $raw) {
        [System.IO.File]::WriteAllText($_.FullName, $new, $utf8NoBom)
        $scrubbedFiles++
      }
    }
  }
}

# verification pass: nothing sensitive may survive
foreach ($pair in $map.scrub) {
  $needle = [string]$pair[0]
  Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Exclude *.ps1 |
    Where-Object { $textExt -contains $_.Extension.ToLower() } |
    Where-Object { $_.FullName -ne $mapPath } | ForEach-Object {
      $t = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
      if ($t.Contains($needle)) {
        $remaining++
        Write-Host ("STILL PRESENT: " + $_.FullName.Substring($repoRoot.Length + 1))
      }
    }
}

Write-Host ""
Write-Host ("copied files          : " + $copied)
Write-Host ("files scrubbed        : " + $scrubbedFiles)
Write-Host ("sensitive left over   : " + $remaining)
Write-Host ("skills missing source : " + ($(if ($missing.Count) { $missing -join ', ' } else { 'none' })))
if ($remaining -gt 0) { throw "scrub verification failed - do NOT publish" }
Write-Host "next: review with 'git status' then commit."
