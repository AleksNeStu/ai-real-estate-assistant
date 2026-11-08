<#
.SYNOPSIS
    Docker mode launcher for AI Real Estate Assistant.
.DESCRIPTION
    Forces Docker mode and runs the application in containers.
    All arguments are passed through to the Python launcher.
.PARAMETER Args
    Arguments to pass to the launcher.
.EXAMPLE
    .\scripts\docker.ps1
    .\scripts\docker.ps1 --docker-mode gpu
    .\scripts\docker.ps1 --internet
#>
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"

# Help support
if ($Args -contains '--help' -or $Args -contains '-h' -or $Args -contains '-?') {
    @”
Usage: docker.ps1 [options]

Docker mode launcher for AI Real Estate Assistant.
Runs the application in Docker containers.

Options:
  --help, -h, -?    Show this help message
  --dry-run         Show commands without executing
  --docker-mode     auto | cpu | gpu | ask (default: auto)
  --internet        Enable web search (SearXNG)

Docker Profiles:
  (default)         External AI only
  local-llm         + Ollama CPU
  local-llm + gpu   + Ollama GPU
  internet          + SearXNG web search

Examples:
  .\scripts\docker.ps1                      # Docker with auto GPU detection
  .\scripts\docker.ps1 --docker-mode cpu    # CPU-only mode
  .\scripts\docker.ps1 --docker-mode gpu    # GPU mode
  .\scripts\docker.ps1 --internet           # With web search

For full options, run: python scripts/start.py --help
“@
    exit 0
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

. (Join-Path $root "scripts\shared\resolve_python.ps1")

$invocation = Get-PythonInvocation -ProjectRoot $root
& $invocation.Python @($invocation.Args) (Join-Path $root "scripts\start.py") --mode docker @Args
exit $LASTEXITCODE
