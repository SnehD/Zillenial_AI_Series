param([string]$In, [string]$OutDir, [string]$Voice = "Microsoft Zira Desktop", [int]$Rate = 1)
# Reads lines "id<TAB>text" and writes OutDir\id.wav using the offline Windows voice.
Add-Type -AssemblyName System.Speech
New-Item -ItemType Directory -Force $OutDir | Out-Null
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice)
$s.Rate = $Rate
Get-Content -Encoding UTF8 $In | ForEach-Object {
  if ($_.Trim() -eq "") { return }
  $p = $_ -split "`t", 2
  $s.SetOutputToWaveFile((Join-Path $OutDir ($p[0] + ".wav")))
  $s.Speak($p[1])
  $s.SetOutputToNull()
}
$s.Dispose()
