import subprocess

# cmd = 'Write-Host "Hello World"'

# cases:
# Get-ChildItem -Path "C:\Program Files\"
# Write-Host "The price is $100"
# Get-Process | Where-Object {$_.Name -like "*python*"} | Select-Object -Property Id


# cmd = ["Write-Host", '"Hello World"']
cmd = ["Write-Host", '"The price is $100"']
cmd = ["powershell.exe", "-NoProfile", "-Command", "Write-Host 'Rich & Poor'"]
cmd = ["Get-Process", "|", "Where-Object", "{$_.Name -like '*python*'}", "|", "Select-Object", "-Property", "Id"]
subprocess.Popen(cmd, shell=True, executable=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
