# LineExportHelper.ps1
# Reusable Windows GUI automation functions for the line-group-export skill.
# IMPORTANT: dot-source this file at the start of every PowerShell invocation that uses
# these functions - each PowerShell tool call runs in a fresh process, so nothing here
# persists across separate tool calls.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class LineExportWin32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, IntPtr dwExtraInfo);

    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);

    // IMPORTANT: must be CharSet.Unicode + the *W entry point. Without this, group
    // names containing emoji or other non-ANSI characters come back as "?????" from
    // GetWindowText, which then breaks exact filename matching in Wait-FileStable.
    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetWindowTextW")]
    public static extern int GetWindowTextW(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    public static List<IntPtr> GetTopLevelWindowsForPid(uint pid) {
        List<IntPtr> result = new List<IntPtr>();
        EnumWindows(delegate (IntPtr hWnd, IntPtr lParam) {
            uint wpid;
            GetWindowThreadProcessId(hWnd, out wpid);
            if (wpid == pid && IsWindowVisible(hWnd)) { result.Add(hWnd); }
            return true;
        }, IntPtr.Zero);
        return result;
    }

    public static string GetTitleUnicode(IntPtr hWnd) {
        StringBuilder sb = new StringBuilder(512);
        GetWindowTextW(hWnd, sb, 512);
        return sb.ToString();
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

$script:SW_RESTORE = 9
$script:MOUSEEVENTF_LEFTDOWN = 0x0002
$script:MOUSEEVENTF_LEFTUP = 0x0004
$script:WM_CLOSE = 0x0010
$script:VK_LWIN = 0x5B
$script:VK_UP = 0x26
$script:KEYEVENTF_KEYUP = 0x0002

function Find-AppWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProcessName,
        [int]$TimeoutSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } |
            Select-Object -First 1

        if ($proc) {
            $rect = New-Object LineExportWin32+RECT
            [void][LineExportWin32]::GetWindowRect($proc.MainWindowHandle, [ref]$rect)
            return [PSCustomObject]@{
                Handle = $proc.MainWindowHandle
                Left   = $rect.Left
                Top    = $rect.Top
                Right  = $rect.Right
                Bottom = $rect.Bottom
                Width  = $rect.Right - $rect.Left
                Height = $rect.Bottom - $rect.Top
            }
        }
        Start-Sleep -Milliseconds 300
    }
    return $null
}

function Show-AppWindow {
    param(
        [Parameter(Mandatory = $true)]
        [IntPtr]$Handle
    )
    [void][LineExportWin32]::ShowWindow($Handle, $script:SW_RESTORE)
    $result = [LineExportWin32]::SetForegroundWindow($Handle)
    Start-Sleep -Milliseconds 300
    return $result
}

function Send-MaximizeShortcut {
    # Sends Win+Up to maximize a window instead of clicking a calculated maximize-button
    # coordinate. Avoids depending on the pre-maximize window rect (which drifts) to find
    # the button - the shortcut works regardless of the window's current position/size.
    # 2026-08-07 validated once on a real LINE chat window: maximized rect landed on the
    # same stable (-8,-8,1928,1040) as the old click-based approach, so downstream offsets
    # (menu button, 儲存聊天, close button) are unaffected and unchanged.
    param(
        [Parameter(Mandatory = $true)]
        [IntPtr]$Handle
    )
    [LineExportWin32]::SetForegroundWindow($Handle) | Out-Null
    Start-Sleep -Milliseconds 300
    [LineExportWin32]::keybd_event($script:VK_LWIN, 0, 0, [UIntPtr]::Zero)
    [LineExportWin32]::keybd_event($script:VK_UP, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 50
    [LineExportWin32]::keybd_event($script:VK_UP, 0, $script:KEYEVENTF_KEYUP, [UIntPtr]::Zero)
    [LineExportWin32]::keybd_event($script:VK_LWIN, 0, $script:KEYEVENTF_KEYUP, [UIntPtr]::Zero)
}

function Find-WindowByExactTitle {
    # More precise than Find-AppWindow for apps (like LINE) that own multiple top-level
    # windows (e.g. one per open chat) - Get-Process's MainWindowHandle is not guaranteed
    # to be the main/list window in that case. Matches the window's UI Automation Name
    # property exactly instead.
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [int]$TimeoutSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $root = [System.Windows.Automation.AutomationElement]::RootElement
        $nameCondition = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, $Title)
        $element = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $nameCondition)

        if ($element -ne $null) {
            $handle = [IntPtr]$element.Current.NativeWindowHandle
            $rect = New-Object LineExportWin32+RECT
            [void][LineExportWin32]::GetWindowRect($handle, [ref]$rect)
            return [PSCustomObject]@{
                Handle = $handle
                Left   = $rect.Left
                Top    = $rect.Top
                Right  = $rect.Right
                Bottom = $rect.Bottom
                Width  = $rect.Right - $rect.Left
                Height = $rect.Bottom - $rect.Top
            }
        }
        Start-Sleep -Milliseconds 300
    }
    return $null
}

function Get-ProcessWindows {
    # Enumerates all visible top-level windows owned by a process, with Unicode-safe
    # titles (see GetWindowTextW note above) and rects. This is the reliable way to
    # find LINE's chat windows - LINE's own list panel visually truncates long group
    # names (e.g. "台中 媽媽寶寶/二手商品出清/贈..."), but the real top-level window
    # title is always the full, untruncated group name. Reading it here means you never
    # have to widen the LINE window or guess at truncated text.
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProcessName
    )

    $proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $proc) { return @() }

    $handles = [LineExportWin32]::GetTopLevelWindowsForPid([uint32]$proc.Id)
    $results = @()
    foreach ($h in $handles) {
        $title = [LineExportWin32]::GetTitleUnicode($h)
        $rect = New-Object LineExportWin32+RECT
        [void][LineExportWin32]::GetWindowRect($h, [ref]$rect)
        $results += [PSCustomObject]@{
            Handle = $h
            Title  = $title
            Left   = $rect.Left
            Top    = $rect.Top
            Right  = $rect.Right
            Bottom = $rect.Bottom
            Width  = $rect.Right - $rect.Left
            Height = $rect.Bottom - $rect.Top
        }
    }
    return $results
}

function Open-LineChatWindow {
    # Double-clicks a group row in the list and identifies the resulting chat window by
    # diffing the process's top-level window list before/after the click - far more
    # robust than assuming a fixed screen position or a specific group name (both the
    # visual list AND the exported filename can truncate/mangle long or emoji-heavy
    # group names, but the live window handle+title from this diff is always correct).
    # Returns $null if no new window with a real title appears within TimeoutSeconds.
    param(
        [Parameter(Mandatory = $true)]
        [int]$X,
        [Parameter(Mandatory = $true)]
        [int]$Y,
        [string]$ProcessName = "LINE",
        [int]$TimeoutSeconds = 5
    )

    $before = Get-ProcessWindows -ProcessName $ProcessName | Select-Object -ExpandProperty Handle
    Invoke-MouseClick -X $X -Y $Y
    Start-Sleep -Milliseconds 120
    Invoke-MouseClick -X $X -Y $Y
    Start-Sleep -Milliseconds 1500

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $after = Get-ProcessWindows -ProcessName $ProcessName
        $candidate = $after | Where-Object { ($before -notcontains $_.Handle) -and $_.Title -and ($_.Height -gt 100) } | Select-Object -First 1
        if ($candidate) { return $candidate }
        Start-Sleep -Milliseconds 300
    }
    return $null
}

function Close-AppWindowByHandle {
    # Sends WM_CLOSE directly via PostMessage instead of clicking a screen coordinate.
    # Prefer this for cleanup/recovery (e.g. closing a window that a stuck modal dialog
    # is covering) since it doesn't depend on the window being visible or on top.
    param(
        [Parameter(Mandatory = $true)]
        [IntPtr]$Handle
    )
    [LineExportWin32]::PostMessage($Handle, $script:WM_CLOSE, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
}

function Invoke-ScreenCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    $screenBounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bitmap = New-Object System.Drawing.Bitmap($screenBounds.Width, $screenBounds.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screenBounds.Left, $screenBounds.Top, 0, 0, $bitmap.Size)
    $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    return $OutputPath
}

function Invoke-MouseClick {
    param(
        [Parameter(Mandatory = $true)]
        [int]$X,
        [Parameter(Mandatory = $true)]
        [int]$Y
    )
    [void][LineExportWin32]::SetCursorPos($X, $Y)
    Start-Sleep -Milliseconds 150
    [LineExportWin32]::mouse_event($script:MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 50
    [LineExportWin32]::mouse_event($script:MOUSEEVENTF_LEFTUP, 0, 0, 0, [IntPtr]::Zero)
}

function Invoke-DialogButtonClick {
    param(
        [string]$AutomationId,
        [string]$NamePattern,
        [string]$DialogName,
        [int]$TimeoutSeconds = 10
    )

    if (-not $AutomationId -and -not $NamePattern) {
        throw "Invoke-DialogButtonClick requires -AutomationId or -NamePattern"
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $root = [System.Windows.Automation.AutomationElement]::RootElement
        $dialog = $null

        if ($DialogName) {
            $nameCondition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, $DialogName)
            $dialog = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $nameCondition)
        } else {
            $classCondition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ClassNameProperty, "#32770")
            $dialog = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $classCondition)
        }

        if ($dialog -ne $null) {
            $buttonCondition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                [System.Windows.Automation.ControlType]::Button)
            $buttons = $dialog.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)

            $target = $null
            foreach ($b in $buttons) {
                if ($AutomationId -and $b.Current.AutomationId -eq $AutomationId) {
                    $target = $b
                    break
                }
                if (-not $target -and $NamePattern -and $b.Current.Name -like $NamePattern) {
                    $target = $b
                }
            }

            if ($target -ne $null) {
                $invokePattern = $target.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                $invokePattern.Invoke()
                return $true
            }
        }
        Start-Sleep -Milliseconds 300
    }
    return $false
}

function Wait-FileStable {
    # IMPORTANT (2026-07-17 incident): if $Path already exists from a previous export
    # and the save action actually fails/misses this run, a totally untouched file
    # trivially satisfies "same size + same LastWriteTime for N checks in a row" within
    # the first couple of polls - this function used to return $true for a file that was
    # never re-saved, which read as a false "success" while the real export had silently
    # failed. Always pass -Since (the timestamp captured right before you started the
    # save action) so a stale pre-existing file cannot pass as fresh.
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [int]$StableChecks = 3,
        [int]$IntervalMilliseconds = 700,
        [int]$TimeoutSeconds = 60,
        [DateTime]$Since = [DateTime]::MinValue
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastSize = -1
    $lastWrite = [DateTime]::MinValue
    $stableCount = 0

    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $Path) {
            $file = Get-Item -LiteralPath $Path
            if ($file.LastWriteTime -ge $Since) {
                if ($file.Length -eq $lastSize -and $file.LastWriteTime -eq $lastWrite) {
                    $stableCount++
                    if ($stableCount -ge $StableChecks) {
                        return $true
                    }
                } else {
                    $stableCount = 0
                    $lastSize = $file.Length
                    $lastWrite = $file.LastWriteTime
                }
            }
        }
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
    return $false
}

function Write-ExportLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogFolder,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if (-not (Test-Path -LiteralPath $LogFolder)) {
        New-Item -ItemType Directory -Path $LogFolder -Force | Out-Null
    }

    $logFile = Join-Path $LogFolder ("{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))
    $timestamp = Get-Date -Format "HH:mm:ss"
    Add-Content -LiteralPath $logFile -Value ("[{0}] {1}" -f $timestamp, $Message) -Encoding utf8
    return $logFile
}
