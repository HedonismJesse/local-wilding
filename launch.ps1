Start-Process cmd -ArgumentList '/k','C:\Users\jesse\Documents\PythonDev\local-wilding\video_run.bat' -WindowStyle Normal
Start-Sleep 5
Get-Process | Where-Object { $_.MainWindowTitle -like "*LW*" -or $_.MainWindowTitle -like "*video_run*" } | Select-Object Id, MainWindowTitle
