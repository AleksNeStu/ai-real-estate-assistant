param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

. (Join-Path $PSScriptRoot "..\shared\resolve_python.ps1")

$invocation = Get-PythonInvocation -ProjectRoot $root
& $invocation.Python @($invocation.Args) (Join-Path $root "scripts\start.py") --mode local --internet @Args
exit $LASTEXITCODE
