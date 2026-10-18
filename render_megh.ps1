$ErrorActionPreference = 'Stop'
$outDir = 'C:\Users\HP\Downloads\code\megh_render'
$pdf = 'C:\Users\HP\Downloads\code\megh_ppt\MeghSentinel-SIH26077.pdf'
$pptx = 'C:\Users\HP\Downloads\code\megh_ppt\MeghSentinel-SIH26077-SIH-Idea-Submission.pptx'
if (Test-Path $outDir) { Remove-Item -Recurse -Force $outDir }
New-Item -ItemType Directory -Path $outDir | Out-Null
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open($pptx, $true, $false, $false)
$pres.SaveAs($outDir, 18)   # ppSaveAsPNG
$pres.SaveAs($pdf, 32)      # ppSaveAsPDF
$pres.Close()
$pp.Quit()
Write-Output "rendered + pdf done"
Get-ChildItem $outDir | Select-Object -ExpandProperty Name
