$ErrorActionPreference='Stop'
$candidates=@('C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe','C:\Program Files\Microsoft\Edge\Application\msedge.exe','C:\Program Files\Google\Chrome\Application\chrome.exe')
$browserPath=$candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $browserPath) { throw 'Install Edge/Chrome or edit the browser path in this script.' }
$captureUrl='http://127.0.0.1:8877/output?capture=1&bg=green&subtitles=0&model=SignHuman_Final'
Start-Process -FilePath $browserPath -ArgumentList @("--app=$captureUrl",'--window-size=760,800','--disable-background-timer-throttling','--disable-renderer-backgrounding') -WindowStyle Normal
