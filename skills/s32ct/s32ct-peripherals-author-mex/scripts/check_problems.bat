@rem Copyright 2026 NXP
@rem
@rem NXP Proprietary. This software is owned or controlled by NXP and may
@rem only be used strictly in accordance with the applicable license terms.
@rem By expressly accepting such terms or by downloading, installing,
@rem activating and/or otherwise using the software, you are agreeing that
@rem you have read, and that you agree to comply with and are bound by,
@rem such license terms.  If you do not agree to be bound by the applicable
@rem license terms, then you may not retain, install, activate or otherwise
@rem use the software.

@echo off
REM ============================================================================
REM check_problems.bat - canonical -ShowProblems validation gate for S32CT.
REM ============================================================================
REM Why this script exists:
REM   toolsc.exe always exits 0 even when the Problems View has errors.
REM   Real errors appear on STDERR as `SEVERE: [TOOL]` and `SEVERE: [Generation`
REM   lines emitted by the Java validation logger. The MCP wrapper truncates
REM   stderr at ~3 KB so you cannot see them through the wrapper alone.
REM
REM   This script:
REM     1. Copies the .mex to a path without spaces (cmd's redirection parser
REM        fails on spaces inside quoted exe paths).
REM     2. Runs toolsc.exe with explicit stderr -> file.
REM     3. Greps the captured stderr for real `[TOOL]`/`[Generation` lines.
REM
REM Usage:
REM   check_problems.bat <abs path to .mex> [ToolName]
REM       ToolName ? Pins | Clocks | Peripherals | DCD | IVT | eFUSE | GTM
REM                  | QuadSPI | FFC     (default: Peripherals)
REM
REM Pass = exit_code 0 AND filtered output is empty.
REM Fail = any line printed under "Real Problems-view lines" below.
REM
REM Configure S32CT_EXE for your install (use the absolute path including the
REM build folder, e.g. C:\NXP\S32ConfigTools.2025.R1.9\B260206\toolsc.exe).
REM ============================================================================

setlocal ENABLEDELAYEDEXPANSION

if "%S32CT_EXE%"=="" set "S32CT_EXE=C:\NXP\S32ConfigTools.2025.R1.9\B260206\toolsc.exe"
if "%PROBE_DIR%"=="" set "PROBE_DIR=C:\Workspace\MCP\probe_out"
if "%PROBE_MEX%"=="" set "PROBE_MEX=C:\Workspace\MCP\probe.mex"

set "INPUT_MEX=%~1"
set "TOOL=%~2"
if "%TOOL%"=="" set "TOOL=Peripherals"

if "%INPUT_MEX%"=="" (
    echo Usage: %~nx0 ^<abs path to .mex^> [ToolName]
    exit /b 2
)

if not exist "%S32CT_EXE%" (
    echo ERROR: S32CT_EXE not found at %S32CT_EXE%
    echo Set the environment variable S32CT_EXE before invoking this script.
    exit /b 3
)

if not exist "%PROBE_DIR%" mkdir "%PROBE_DIR%" >nul

REM 1. Stage the .mex at a path without spaces.
REM NOTE: this overwrites %PROBE_MEX% without prompting. The probe
REM location is a scratch staging area, not a project file - disclose the
REM destination so the caller can see what is being replaced.
echo Staging "%INPUT_MEX%"
echo      -^> "%PROBE_MEX%" (existing file at this path is overwritten)
copy /Y "%INPUT_MEX%" "%PROBE_MEX%" >nul
if errorlevel 1 (
    echo ERROR: failed to copy "%INPUT_MEX%" to "%PROBE_MEX%"
    exit /b 4
)

REM 2. Run the tool, redirecting stdout/stderr to files
"%S32CT_EXE%" -Load "%PROBE_MEX%" -HeadlessTool %TOOL% -Enable -ShowProblems ^
    1> "%PROBE_DIR%\out.txt" 2> "%PROBE_DIR%\err.txt"
set "EC=%ERRORLEVEL%"

echo --- exit_code=%EC%
echo --- stdout bytes:
for %%F in ("%PROBE_DIR%\out.txt") do echo     %%~zF
echo --- stderr bytes:
for %%F in ("%PROBE_DIR%\err.txt") do echo     %%~zF

REM 3. Grep stderr for real Problems-view lines. The filter excludes generic
REM    framework chatter that appears on every clean run.
echo --- Real Problems-view lines (filtered):
findstr /c:"SEVERE: [TOOL]" /c:"SEVERE: [Generation" "%PROBE_DIR%\err.txt" ^
    | findstr /v /c:"No script file found while trying to recompile the codegeneration script for SerDes Config Tool" ^
    > "%PROBE_DIR%\real_problems.txt"

if exist "%PROBE_DIR%\real_problems.txt" (
    for %%F in ("%PROBE_DIR%\real_problems.txt") do (
        if %%~zF GTR 0 (
            type "%PROBE_DIR%\real_problems.txt"
            echo --- FAIL: real problems above ---
            exit /b 1
        ) else (
            echo --- ^(none^)
            echo --- PASS: 0 real problems after filtering ---
            exit /b 0
        )
    )
)

echo --- PASS: 0 real problems after filtering ---
exit /b 0
