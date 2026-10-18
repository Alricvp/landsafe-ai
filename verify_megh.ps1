$ErrorActionPreference = "Stop"
$pp = New-Object -ComObject PowerPoint.Application
$path = "C:\Users\HP\Downloads\code\megh_ppt\MeghSentinel-SIH26077-SIH-Idea-Submission.pptx"
$pres = $pp.Presentations.Open($path, $true, $false, $false)
$avail = @{2=1.84; 3=1.93; 4=1.63; 5=1.98; 6=3.89}
foreach ($i in 2..6) {
  $slide = $pres.Slides.Item($i)
  foreach ($sh in $slide.Shapes) {
    if ($sh.Name -eq "TextBox 8") {
      $bh = $sh.TextFrame2.TextRange.BoundHeight / 72.0
      $a = $avail[$i]
      $status = if ($bh -le $a) { "OK" } else { "OVERFLOW" }
      Write-Output ("S{0} body text = {1:N2} in  available {2:N2} in  -> {3}" -f $i, $bh, $a, $status)
      try {
        $p1 = $sh.TextFrame2.TextRange.Paragraphs(1).ParagraphFormat.Bullet.Type
        $p2 = $sh.TextFrame2.TextRange.Paragraphs(2).ParagraphFormat.Bullet.Type
        Write-Output ("     bullet para1={0} para2={1}  {2}" -f $p1, $p2, $(if ("$p1" -eq "$p2") { "consistent" } else { "MISMATCH" }))
      } catch { Write-Output ("     bullet check failed: " + $_.Exception.Message) }
    }
    if ($sh.HasTable -eq -1) {
      $top = $sh.Top / 72.0; $h = $sh.Height / 72.0
      Write-Output ("S{0} table top={1:N2} height={2:N2} bottom={3:N2} (footer starts 6.95)" -f $i, $top, $h, ($top + $h))
    }
    if ($sh.Type -eq 13) {
      $top = $sh.Top / 72.0; $bot = ($sh.Top + $sh.Height) / 72.0
      Write-Output ("S{0} picture top={1:N2} bottom={2:N2}" -f $i, $top, $bot)
    }
  }
}
$pres.Close()
$pp.Quit()
