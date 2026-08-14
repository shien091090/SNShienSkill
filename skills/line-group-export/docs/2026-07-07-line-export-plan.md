# LINE 群組訊息匯出自動化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill (`line-group-export`) that, when triggered with "LINE匯出紀錄", automates clicking through LINE 桌面版 to save chat history for every group under the "自動化" label, then automatically chains into the existing `line-group-daily-report` skill.

**Architecture:** A PowerShell helper library (`LineExportHelper.ps1`) provides low-level, testable building blocks — window discovery, screenshot capture, coordinate-based mouse clicks, UI-Automation-based native dialog button clicks, and file-stability polling. A `SKILL.md` orchestrates these blocks; Claude itself performs all visual judgment (reading screenshots via the Read tool, deciding coordinates) rather than a separate AI vision API call.

**Tech Stack:** PowerShell 7+ (pwsh) on Windows 11, .NET assemblies only (`System.Windows.Forms`, `System.Drawing`, `UIAutomationClient`, `UIAutomationTypes`), Win32 P/Invoke (`user32.dll`). No Python, no external PowerShell modules, no separate Anthropic API key.

## Global Constraints

- Target skill folder: `C:\Users\lithoshu\.claude\skills\line-group-export\` — this location is **not inside a git repository**. No task in this plan includes a `git commit` step; each task ends with "confirm the file is saved" instead.
- Every PowerShell tool invocation runs in a **fresh process** — `Add-Type` declarations, functions, and variables do NOT persist between separate tool calls. Every script that uses `LineExportHelper.ps1` functions MUST start by dot-sourcing it: `. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"`.
- No test framework (no Pester) is used — verification steps are plain PowerShell snippets run via the PowerShell tool, with expected output described in each step.
- OS UI locale is Traditional Chinese. Wherever a control is a **standard Win32 dialog** (message box, common file dialog), prefer matching buttons by **AutomationId** (numeric, language-independent — e.g. `6` = IDYES, `7` = IDNO, `1` = IDOK) over localized button text. Fall back to `-like` name-pattern matching only when AutomationId is unknown.
- Target export folder is the existing `C:\Users\lithoshu\Desktop\Line社群訊息紀錄` — LINE already remembers this path per conversation from prior manual saves; no path-picking logic is needed.
- Precondition assumed throughout: LINE 桌面版 is already logged in and running in the background (icon visible in the taskbar). No task handles login or first-launch flows.

---

## File Structure

- Create: `C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1` — all reusable PowerShell functions (Tasks 1–5)
- Create: `C:\Users\lithoshu\.claude\skills\line-group-export\SKILL.md` — skill instructions (Task 7)
- Created at runtime: `C:\Users\lithoshu\.claude\skills\line-group-export\logs\YYYY-MM-DD.log` (by `Write-ExportLog`)
- Already exists: `C:\Users\lithoshu\.claude\skills\line-group-export\docs\2026-07-07-line-export-design.md` (spec, no changes needed)

---

### Task 1: Scaffold helper script + window discovery functions

**Files:**
- Create: `C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1`

**Interfaces:**
- Produces: `Find-AppWindow -ProcessName <string> [-TimeoutSeconds <int, default 10>]` → returns `[PSCustomObject]@{Handle;Left;Top;Right;Bottom;Width;Height}` or `$null` if not found within timeout.
- Produces: `Show-AppWindow -Handle <IntPtr>` → returns `$true`/`$false` (result of `SetForegroundWindow`).
- Produces: shared type `LineExportWin32` (P/Invoke class) and `$script:SW_RESTORE`, `$script:MOUSEEVENTF_LEFTDOWN`, `$script:MOUSEEVENTF_LEFTUP` constants, used by later tasks.

- [ ] **Step 1: Confirm the failure state (file doesn't exist yet)**

Run:
```powershell
Test-Path "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
```
Expected: `False`

- [ ] **Step 2: Create `LineExportHelper.ps1` with the shared header and window functions**

```powershell
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
using System.Runtime.InteropServices;

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
    public static extern bool SetCursorPos(int X, int Y);

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
```

- [ ] **Step 3: Verify against Notepad**

Run:
```powershell
Start-Process notepad.exe
Start-Sleep -Milliseconds 800
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"

$window = Find-AppWindow -ProcessName "notepad"
if ($null -eq $window) { throw "Find-AppWindow returned null" }
if ($window.Width -le 0 -or $window.Height -le 0) { throw "Invalid window size: $($window.Width)x$($window.Height)" }
Write-Output "FOUND: Handle=$($window.Handle) Size=$($window.Width)x$($window.Height)"

$shown = Show-AppWindow -Handle $window.Handle
Start-Sleep -Milliseconds 300
$fg = [LineExportWin32]::GetForegroundWindow()
Write-Output "Show-AppWindow returned: $shown"
Write-Output "Foreground matches target: $($fg -eq $window.Handle)"
```
Expected:
```
FOUND: Handle=<some non-zero number> Size=<width>x<height>
Show-AppWindow returned: True
Foreground matches target: True
```

- [ ] **Step 4: Confirm file saved**

Run: `Test-Path "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"`
Expected: `True`
(No git commit — this location is not a git repository.)

---

### Task 2: Screen capture function

**Files:**
- Modify: `C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1` (append function)

**Interfaces:**
- Consumes: nothing new (uses `System.Drawing`/`System.Windows.Forms` already loaded in Task 1's header)
- Produces: `Invoke-ScreenCapture -OutputPath <string>` → captures the full virtual screen (all monitors) to a PNG file, returns `$OutputPath`.

- [ ] **Step 1: Write the verification script first (will fail — function doesn't exist yet)**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
Invoke-ScreenCapture -OutputPath (Join-Path $env:TEMP "capture_test.png")
```
Expected: error — `The term 'Invoke-ScreenCapture' is not recognized...`

- [ ] **Step 2: Append the function to `LineExportHelper.ps1`**

```powershell

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
```

- [ ] **Step 3: Run verification again, expect PASS**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
$path = Invoke-ScreenCapture -OutputPath (Join-Path $env:TEMP "capture_test.png")
$file = Get-Item $path
Write-Output "Saved: $path  Size: $($file.Length) bytes"
Remove-Item $path
```
Expected: `Saved: ...capture_test.png  Size: <a number greater than 0> bytes`

- [ ] **Step 4: Confirm file saved**

Run: `Select-String -Path "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1" -Pattern "function Invoke-ScreenCapture"`
Expected: one match found.

---

### Task 3: Raw coordinate mouse click function

**Files:**
- Modify: `C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1` (append function)

**Interfaces:**
- Consumes: `LineExportWin32` type and `$script:MOUSEEVENTF_LEFTDOWN`/`$script:MOUSEEVENTF_LEFTUP` from Task 1's header.
- Produces: `Invoke-MouseClick -X <int> -Y <int>` → moves the cursor to the given absolute screen coordinate and performs a left click. No return value.

- [ ] **Step 1: Write the verification script first (will fail — function doesn't exist yet)**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
Invoke-MouseClick -X 100 -Y 100
```
Expected: error — `The term 'Invoke-MouseClick' is not recognized...`

- [ ] **Step 2: Append the function to `LineExportHelper.ps1`**

```powershell

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
```

- [ ] **Step 3: Verify against a real clickable target (MessageBox Yes/No button)**

This test uses UI Automation *only to read* the button's on-screen position (not to click it), so the click itself is independently verified.

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
Get-Job | Stop-Job -PassThru | Remove-Job -Force -ErrorAction SilentlyContinue

$job = Start-Job -ScriptBlock {
    Add-Type -AssemblyName System.Windows.Forms
    $result = [System.Windows.Forms.MessageBox]::Show("Click test", "ClickTestDialog", [System.Windows.Forms.MessageBoxButtons]::YesNo)
    return $result.ToString()
}
Start-Sleep -Milliseconds 1500

$root = [System.Windows.Automation.AutomationElement]::RootElement
$nameCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, "ClickTestDialog")
$dialog = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $nameCondition)
$buttonCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button)
$buttons = $dialog.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)

$yesButton = $null
foreach ($b in $buttons) { if ($b.Current.AutomationId -eq "6") { $yesButton = $b } }
$rect = $yesButton.Current.BoundingRectangle
$centerX = [int]($rect.X + $rect.Width / 2)
$centerY = [int]($rect.Y + $rect.Height / 2)

Invoke-MouseClick -X $centerX -Y $centerY

$jobResult = Receive-Job -Job $job -Wait -AutoRemoveJob -ErrorAction SilentlyContinue
Write-Output "JOB_RESULT: $jobResult"
```
Expected: `JOB_RESULT: Yes`

- [ ] **Step 4: Confirm file saved**

Run: `Select-String -Path "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1" -Pattern "function Invoke-MouseClick"`
Expected: one match found.

---

### Task 4: Native dialog button click via UI Automation

**Files:**
- Modify: `C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1` (append function)

**Interfaces:**
- Consumes: `UIAutomationClient`/`UIAutomationTypes` assemblies loaded in Task 1's header.
- Produces: `Invoke-DialogButtonClick -AutomationId <string> [-NamePattern <string>] [-DialogName <string>] [-TimeoutSeconds <int, default 10>]` → finds a standard dialog (class `#32770`, or the one matching `-DialogName` if given), finds a button by `AutomationId` (preferred) or `NamePattern` (fallback), invokes it. Returns `$true` if a button was found and invoked, `$false` on timeout. Throws if neither `-AutomationId` nor `-NamePattern` is given.

- [ ] **Step 1: Write the verification script first (will fail — function doesn't exist yet)**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
Invoke-DialogButtonClick -AutomationId "6" -TimeoutSeconds 2
```
Expected: error — `The term 'Invoke-DialogButtonClick' is not recognized...`

- [ ] **Step 2: Append the function to `LineExportHelper.ps1`**

```powershell

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
```

- [ ] **Step 3: Verify against a real MessageBox dialog**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
Get-Job | Stop-Job -PassThru | Remove-Job -Force -ErrorAction SilentlyContinue

$job = Start-Job -ScriptBlock {
    Add-Type -AssemblyName System.Windows.Forms
    $result = [System.Windows.Forms.MessageBox]::Show("Dialog click test", "DialogClickTest", [System.Windows.Forms.MessageBoxButtons]::YesNo)
    return $result.ToString()
}
Start-Sleep -Milliseconds 1500

$clicked = Invoke-DialogButtonClick -AutomationId "6" -DialogName "DialogClickTest" -TimeoutSeconds 5
Write-Output "Invoke-DialogButtonClick returned: $clicked"

$jobResult = Receive-Job -Job $job -Wait -AutoRemoveJob -ErrorAction SilentlyContinue
Write-Output "JOB_RESULT: $jobResult"
```
Expected:
```
Invoke-DialogButtonClick returned: True
JOB_RESULT: Yes
```

- [ ] **Step 4: Confirm file saved**

Run: `Select-String -Path "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1" -Pattern "function Invoke-DialogButtonClick"`
Expected: one match found.

---

### Task 5: File-stability polling and export logging

**Files:**
- Modify: `C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1` (append two functions)

**Interfaces:**
- Produces: `Wait-FileStable -Path <string> [-StableChecks <int, default 3>] [-IntervalMilliseconds <int, default 700>] [-TimeoutSeconds <int, default 60>]` → returns `$true` once the file's size and last-write-time are unchanged across `StableChecks` consecutive polls, `$false` on timeout.
- Produces: `Write-ExportLog -LogFolder <string> -Message <string>` → appends a timestamped line to `<LogFolder>\<today's date>.log` (creating the folder if needed), returns the log file path.

- [ ] **Step 1: Write the verification script first (will fail — functions don't exist yet)**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
Wait-FileStable -Path "C:\nonexistent.txt" -TimeoutSeconds 2
```
Expected: error — `The term 'Wait-FileStable' is not recognized...`

- [ ] **Step 2: Append both functions to `LineExportHelper.ps1`**

```powershell

function Wait-FileStable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [int]$StableChecks = 3,
        [int]$IntervalMilliseconds = 700,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastSize = -1
    $lastWrite = [DateTime]::MinValue
    $stableCount = 0

    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $Path) {
            $file = Get-Item -LiteralPath $Path
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
```

- [ ] **Step 3: Verify `Wait-FileStable` — both the stabilizing case and the timeout case**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"

$testFile = Join-Path $env:TEMP "stable_test.txt"
if (Test-Path $testFile) { Remove-Item $testFile }
"line1" | Out-File $testFile -Encoding utf8

$job = Start-Job -ScriptBlock {
    param($path)
    Start-Sleep -Milliseconds 500
    "line2" | Add-Content $path
    Start-Sleep -Milliseconds 500
    "line3" | Add-Content $path
} -ArgumentList $testFile

$result = Wait-FileStable -Path $testFile -StableChecks 3 -IntervalMilliseconds 300 -TimeoutSeconds 15
Write-Output "Stabilizing case result: $result (expect True)"
Receive-Job -Job $job -Wait -AutoRemoveJob | Out-Null
Remove-Item $testFile

$result2 = Wait-FileStable -Path (Join-Path $env:TEMP "nonexistent_$(Get-Random).txt") -TimeoutSeconds 3
Write-Output "Timeout case result: $result2 (expect False)"
```
Expected:
```
Stabilizing case result: True (expect True)
Timeout case result: False (expect False)
```

- [ ] **Step 4: Verify `Write-ExportLog`**

Run:
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
$testLogFolder = Join-Path $env:TEMP "export_log_test"
if (Test-Path $testLogFolder) { Remove-Item $testLogFolder -Recurse -Force }

$logFile1 = Write-ExportLog -LogFolder $testLogFolder -Message "first message"
$logFile2 = Write-ExportLog -LogFolder $testLogFolder -Message "second message"
Write-Output "Same file: $($logFile1 -eq $logFile2)"
Get-Content $logFile1
Remove-Item $testLogFolder -Recurse -Force
```
Expected:
```
Same file: True
[HH:mm:ss] first message
[HH:mm:ss] second message
```
(with real timestamps in place of `HH:mm:ss`)

- [ ] **Step 5: Confirm file saved**

Run: `Select-String -Path "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1" -Pattern "function Wait-FileStable|function Write-ExportLog"`
Expected: two matches found.

---

### Task 6: Live inspection of LINE's actual save dialogs (requires user's screen)

**This task cannot be done by an isolated subagent — it requires the user's LINE desktop app to be open and the user present to click through a few steps live.**

**Files:** none created/modified in this task; its output (recorded AutomationId/Name values) feeds directly into Task 7's `SKILL.md`.

**Interfaces:**
- Consumes: `Invoke-DialogButtonClick`'s `-AutomationId`/`-NamePattern` parameters (Task 4) — this task determines what concrete values to pass for LINE's real dialogs.
- Produces: two recorded values — `$SaveButtonSelector` and `$OverwriteYesButtonSelector` (each either an AutomationId or a Name pattern) — written into `SKILL.md` in Task 7.

- [ ] **Step 1: Ask the user to open LINE and get to the point right before saving**

Ask the user to: open LINE, click into any one group chat, click "...", click "儲存聊天" so the "另存新檔" dialog is on screen — then tell you it's ready.

- [ ] **Step 2: Dump the Save dialog's button identifiers**

Run:
```powershell
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$classCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, "#32770")
$dialogs = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $classCondition)

Write-Output "Dialog count: $($dialogs.Count)"
foreach ($dialog in $dialogs) {
    Write-Output "---- Dialog Name=[$($dialog.Current.Name)] ----"
    $buttonCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button)
    $buttons = $dialog.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
    foreach ($b in $buttons) {
        Write-Output ("  Button Name=[{0}] AutomationId=[{1}]" -f $b.Current.Name, $b.Current.AutomationId)
    }
}
```
Expected: output lists the "另存新檔" dialog with a button whose `Name` contains "存檔". Record its `AutomationId` if present and non-empty; otherwise record its exact `Name` string for `-NamePattern` fallback (e.g. `"*存檔*"`).

- [ ] **Step 3: Trigger the overwrite-confirmation dialog and dump its buttons**

Ask the user to click that recorded Save button (or click it yourself using `Invoke-DialogButtonClick` with the selector found in Step 2) so the "是否覆蓋" confirmation dialog appears, then re-run the same dump script from Step 2.

Expected: output lists a new dialog with Yes/No-style buttons. Record the "Yes"/覆蓋 button's `AutomationId` (expected to be `6`, matching the standard Win32 IDYES convention already confirmed in Task 4's test) or its `Name` fallback.

- [ ] **Step 4: Record the two selectors for use in Task 7**

Write down (in the task notes, not a file):
- `$SaveButtonSelector` = the AutomationId or Name pattern found in Step 2
- `$OverwriteYesButtonSelector` = the AutomationId or Name pattern found in Step 3

No file changes in this task — nothing to "save" beyond these two recorded values.

---

### Task 7: Write `SKILL.md`

**Files:**
- Create: `C:\Users\lithoshu\.claude\skills\line-group-export\SKILL.md`

**Interfaces:**
- Consumes: every function from `LineExportHelper.ps1` (Tasks 1–5) and the two selectors recorded in Task 6.
- Produces: the skill definition triggered by "LINE匯出紀錄", callable by Claude Code like `line-group-daily-report` or `shien`.

- [ ] **Step 1: Write `SKILL.md`**

```markdown
# LINE 群組訊息匯出自動化

## 觸發詞：LINE匯出紀錄

當使用者說「LINE匯出紀錄」時，執行以下步驟（**全程自動執行，不需使用者確認**，任一群組失敗則跳過並記錄，不中斷整體流程）：

前提：LINE 桌面版已登入且在背景執行。所有 PowerShell 指令開頭都要先執行：
```powershell
. "C:\Users\lithoshu\.claude\skills\line-group-export\LineExportHelper.ps1"
```

### Step 0 — 校準視窗

```powershell
$window = Find-AppWindow -ProcessName "LINE" -TimeoutSeconds 10
if (-not $window) { throw "找不到 LINE 視窗，請確認 LINE 已啟動" }
Show-AppWindow -Handle $window.Handle
```
記下 `$window.Left/Top/Right/Bottom/Width/Height`，之後點擊座標一律用「相對這個 rect 的偏移量」計算。

### Step 1 — 定位「自動化」tab 並讀取群組清單

```powershell
$screenshot1 = Invoke-ScreenCapture -OutputPath (Join-Path $env:TEMP "line_export_step1.png")
```
用 Read 工具查看 `$screenshot1`，在 `$window` 範圍內找到上方「自動化」分類 tab 的座標，呼叫 `Invoke-MouseClick` 點擊。再截圖一次：

```powershell
$screenshot2 = Invoke-ScreenCapture -OutputPath (Join-Path $env:TEMP "line_export_step2.png")
```
用 Read 工具查看 `$screenshot2`，讀出「自動化」分類下所有可見群組名稱，列為 `$pendingGroups`（陣列）。v1 假設一畫面看得完，不捲動；若群組清單超出畫面高度，記錄此限制並只處理看得到的群組。

### Step 2 — 逐一處理群組（迴圈直到 `$pendingGroups` 全部處理過）

對 `$pendingGroups` 中「尚未處理」的第一個群組（用視覺重新確認目前清單，因排序會變動）：

1. 截圖 → Read 查看 → 找到該群組名稱座標 → `Invoke-MouseClick`
2. 等待約 1 秒，截圖確認聊天視窗已開啟
3. 在 `$window` 右上角附近截圖 → Read 確認「...」按鈕座標（大約在 `$window.Right` 往左一小段、`$window.Top` 往下一小段的範圍）→ `Invoke-MouseClick`
4. 截圖確認選單彈出 → Read 找到「儲存聊天」項目座標 → `Invoke-MouseClick`
5. 等待「另存新檔」對話框出現：
   ```powershell
   $saved = Invoke-DialogButtonClick -AutomationId "<Task 6 記錄的 SaveButtonSelector，若無則改用 -NamePattern>" -TimeoutSeconds 10
   ```
   若 `$saved` 為 `$false`，記錄失敗（`Write-ExportLog`），跳過此群組，回到迴圈頂端處理下一個。
6. 等待「是否覆蓋」對話框並點擊「是」：
   ```powershell
   $overwritten = Invoke-DialogButtonClick -AutomationId "6" -TimeoutSeconds 10
   ```
   （`6` = 標準 Win32 IDYES，已在 Task 4/6 驗證過為語言無關的可靠寫法）
   若 `$overwritten` 為 `$false`，記錄失敗，跳過此群組。
7. 完成偵測（取代看「100%」的視覺判斷）：
   ```powershell
   $targetFile = "C:\Users\lithoshu\Desktop\Line社群訊息紀錄\$groupName.txt"
   $stable = Wait-FileStable -Path $targetFile -StableChecks 3 -IntervalMilliseconds 700 -TimeoutSeconds 60
   ```
   若 `$stable` 為 `$false`，記錄失敗，跳過此群組。
8. 截圖 → Read 找到右上角「X」關閉按鈕座標 → `Invoke-MouseClick` 關閉聊天室
9. 標記該群組完成：
   ```powershell
   Write-ExportLog -LogFolder "C:\Users\lithoshu\.claude\skills\line-group-export\logs" -Message "群組 [$groupName] 匯出成功"
   ```
10. 回到迴圈頂端，重新截圖判讀目前清單，取下一個尚未處理的群組；若目前清單中所有先前記錄的群組都已標記完成，結束迴圈。

### Step 3 — 收尾

輸出本次執行摘要（成功/失敗各幾個、失敗原因列表），接著自動觸發既有 `line-group-daily-report` skill 的摘要流程（比照該 skill 觸發詞「LINE群組日報」的流程執行）。

### 錯誤處理

- 「自動化」tab 本身找不到（Step 1 找不到 tab 或讀不到任何群組名稱）→ 視為整次執行失敗，記錄後停止，不嘗試處理任何群組。
- 個別群組任一步驟失敗或逾時 → 記錄原因（`Write-ExportLog`），跳過該群組，繼續下一個。
```

- [ ] **Step 2: Self-review against the design doc**

Open `C:\Users\lithoshu\.claude\skills\line-group-export\docs\2026-07-07-line-export-design.md` side by side with the new `SKILL.md` and confirm every item in the design's "元件與流程" (Step 0–3) and "錯誤處理" sections has a corresponding, concrete instruction in `SKILL.md` — not a placeholder like "figure out coordinates" without saying how. Fix any gaps found inline.

- [ ] **Step 3: Confirm file saved**

Run: `Test-Path "C:\Users\lithoshu\.claude\skills\line-group-export\SKILL.md"`
Expected: `True`

---

### Task 8: Live end-to-end acceptance test (requires user's screen)

**This task cannot be done by an isolated subagent — it requires triggering the real skill against the user's live LINE desktop app, with the user present to confirm results.**

**Files:** none created/modified — this is a live behavioral verification of Tasks 1–7 together.

**Interfaces:**
- Consumes: the complete `line-group-export` skill (Task 7) and all helper functions (Tasks 1–5).
- Produces: a go/no-go confirmation that the feature works end-to-end; any bugs found here get fixed by revisiting the relevant earlier task.

- [ ] **Step 1: Trigger the skill**

With the user present and watching the screen, invoke the skill by having the user type "LINE匯出紀錄" (or trigger it directly as the acting agent, narrating each action).

- [ ] **Step 2: Verify window calibration and group list reading**

Confirm: the LINE window was found and brought to foreground; the "自動化" tab was correctly identified and clicked; the group list read from the screenshot matches what's actually visible in LINE.

- [ ] **Step 3: Verify each group is exported correctly**

Run after the skill completes:
```powershell
Get-ChildItem "C:\Users\lithoshu\Desktop\Line社群訊息紀錄" -Filter "*.txt" | Select-Object Name, LastWriteTime
```
Expected: every group's `.txt` file has a `LastWriteTime` from within the last few minutes (i.e., just overwritten).

- [ ] **Step 4: Verify failure handling with a deliberately induced failure**

With the user's cooperation, interrupt one group's flow partway (e.g., manually close the chat window right after it opens, before the skill clicks "..."), and confirm:
- The skill logs the failure and moves on to the next group rather than halting.
- Run: `Get-Content (Get-ChildItem "C:\Users\lithoshu\.claude\skills\line-group-export\logs" -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName`
- Expected: log contains a failure line for the interrupted group and success lines for the others.

- [ ] **Step 5: Verify auto-chain into `line-group-daily-report`**

Confirm that after the export summary is printed, the daily report summary (as produced by the `line-group-daily-report` skill) is generated automatically in the same turn, without the user needing to type "LINE群組日報" separately.

- [ ] **Step 6: Record final confirmation**

If all of Steps 2–5 pass, tell the user the feature is working end-to-end. If any step fails, identify which earlier task (1–7) needs revisiting, fix it, and re-run this task from Step 1.

---

## Self-Review Notes

- **Spec coverage:** Step 0 (校準) → Task 1; Step 1 (定位 tab + 讀清單) → Task 7 Step 1 code + Task 1's window functions; Step 2 (逐一處理群組, all 8 sub-steps including dialog handling and completion detection) → Task 7 Step 1 code using Tasks 2–5's functions, with real button selectors from Task 6; Step 3 (收尾 + 自動連動日報) → Task 7 Step 1 code, verified in Task 8 Step 5; 錯誤處理 (skip+log, tab-not-found = hard stop) → Task 7 Step 1 code, verified in Task 8 Step 4; 已知限制 (no scroll in v1) → explicitly called out in Task 7's Step 1 instructions.
- **Placeholder scan:** no TBD/TODO remain; the two values left for live discovery (`SaveButtonSelector`, `OverwriteYesButtonSelector`) are explicitly scoped to Task 6 with a concrete procedure to obtain them, not left vague.
- **Type consistency:** function names/parameters (`Find-AppWindow`, `Show-AppWindow`, `Invoke-ScreenCapture`, `Invoke-MouseClick`, `Invoke-DialogButtonClick`, `Wait-FileStable`, `Write-ExportLog`) are used identically across Tasks 1–7.
