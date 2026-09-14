<#
Copies a local file to a folder on the LIMO robot over SCP.

Requires:
  - OpenSSH client on Windows (already present: C:\Windows\System32\OpenSSH\scp.exe)
  - An SSH server running on the robot's Ubuntu side. If it's not installed:
      sudo apt install openssh-server
      sudo systemctl enable --now ssh
    (NoMachine alone does not give you SSH/SCP access -- this is separate.)

Usage:
  .\deploy_to_robot.ps1 -LocalFile ..\node-red-additions\dashboard-bridge.json -RemotePath "~/.node-red/" -RobotHost 192.168.1.50 -RobotUser agilex
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$LocalFile,

    [Parameter(Mandatory = $true)]
    [string]$RemotePath,

    [Parameter(Mandatory = $true)]
    [string]$RobotHost,

    [string]$RobotUser = "agilex",

    [int]$Port = 22
)

if (-not (Test-Path $LocalFile)) {
    Write-Error "Local file not found: $LocalFile"
    exit 1
}

$destination = "${RobotUser}@${RobotHost}:${RemotePath}"
Write-Host "Copying '$LocalFile' -> '$destination' (port $Port)..."

scp -P $Port $LocalFile $destination

if ($LASTEXITCODE -eq 0) {
    Write-Host "Transfer complete."
} else {
    Write-Error "scp failed (exit $LASTEXITCODE). Check that SSH is enabled on the robot and the host/user/port/path are correct."
}
