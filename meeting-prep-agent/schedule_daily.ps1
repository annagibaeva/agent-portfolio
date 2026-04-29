# Register a Windows Scheduled Task that runs `python main.py --daily` at 7am.
# Run this PowerShell script once, as the user (no admin needed for user-scope tasks).

$ProjectDir = "$PSScriptRoot"
$Python = (Get-Command python).Source
$TaskName = "MeetingPrepAgent-Daily"

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "main.py --daily" `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Daily -At 8:30am   # local time of this machine; set to Singapore TZ for SGT delivery

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Meeting Prep Agent — daily brief generation" `
    -Force

Write-Host "Registered task '$TaskName' for 7:00am daily."
Write-Host "Inspect: Get-ScheduledTask -TaskName $TaskName"
Write-Host "Remove:  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
