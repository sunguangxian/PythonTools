# ================================
# USB Serial Menu Script (usbipd)
# ================================

function Show-ActionMenu {
    Write-Host ""
    Write-Host "Select action:"
    Write-Host "[0] Attach (connect USB device to WSL)"
    Write-Host "[1] Detach (disconnect USB device from WSL)"
    Write-Host "[2] Status (show current status)"
    Write-Host "[q] Quit"
}

function Get-UsbDevices {
    return usbipd list | Select-Object -Skip 1
}

while ($true) {

    Show-ActionMenu
    $action = Read-Host "Enter action number"

    if ($action -eq "q") {
        Write-Host "Exit."
        break
    }

    if ($action -notin @("0","1","2")) {
        Write-Host "Invalid action."
        continue
    }

    if ($action -eq "2") {
        Write-Host "`n[Windows] USB devices:"
        usbipd list

        Write-Host "`n[WSL] Serial devices:"
        wsl -e bash -c "ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || echo '(none)'"
        continue
    }

    $devices = Get-UsbDevices

    if (-not $devices -or $devices.Count -eq 0) {
        Write-Host "No USB devices found."
        continue
    }

    Write-Host "`nAvailable USB devices:"
    $map = @{}

    for ($i = 0; $i -lt $devices.Count; $i++) {
        Write-Host "[$i] $($devices[$i])"
        $map[$i] = $devices[$i]
    }

    $choice = Read-Host "`nSelect device index(es) (e.g. 0 or 0,2)"

    $indexes = $choice -split "," | ForEach-Object { $_.Trim() }

    foreach ($idx in $indexes) {
        if ($idx -match '^\d+$' -and $map.ContainsKey([int]$idx)) {

            $busid = ($map[[int]$idx] -split "\s+")[0]

            if ($action -eq "0") {
                Write-Host "Attaching BUSID=$busid"
                usbipd attach --busid $busid --wsl
            }
            elseif ($action -eq "1") {
                Write-Host "Detaching BUSID=$busid"
                usbipd detach --busid $busid
            }

        } else {
            Write-Host "Invalid index: $idx"
        }
    }

    if ($action -eq "0") {
        Write-Host "`n[WSL] Serial devices after attach:"
        wsl -e bash -c "ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || echo '(none)'"
    }
}
