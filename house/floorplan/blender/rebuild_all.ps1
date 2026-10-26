# Runs the whole chain from the source .blend: build, finalize, the repaints and the furniture. About 4 minutes.
#   .\rebuild_all.ps1 -Source "C:\...\redtower.blend" -Out "C:\...\ha-floorplan"
param(
  [Parameter(Mandatory = $true)][string]$Source,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)
$ErrorActionPreference = 'Continue'
$S = $PSScriptRoot
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$log = Join-Path $Out 'rebuild.log'
"build" | Out-File $log
& $Blender -b $Source --python "$S\build_ha.py" -- $Out *>> $log
"finalize" | Out-File $log -Append
& $Blender -b "$Out\redtower_ha.blend" --python "$S\finalize.py" -- $Out *>> $log
foreach ($p in 'repaint.py','repaint2.py','repaint3.py','repaint4.py','repaint5.py','furnish_bedroom.py','furnish_living.py','furnish_car.py') {
  $p | Out-File $log -Append
  & $Blender -b "$Out\redtower_ha.blend" --python "$S\$p" -- $Out *>> $log
}
Remove-Item "$Out\redtower_ha.blend1" -ErrorAction SilentlyContinue
"DONE" | Out-File $log -Append
