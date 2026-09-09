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
REM ============================================================
REM  run-mcp.bat - Wrapper to run a python -m module with args
REM  inside the project's virtual environment.
REM
REM  Usage:
REM      run-mcp.bat <module> [args...]
REM
REM  Examples:
REM      run-mcp.bat nxp.mcp.gateway configs\gateway.stdio.yaml
REM      run-mcp.bat nxp.mcp.gateway configs\gateway.http.yaml
REM ============================================================

setlocal

REM --- Resolve script directory (works no matter where it's called from) ---
set "SCRIPT_DIR=%~dp0"
set "PYTHONUTF8=1"

REM --- Validate arguments ---
if "%~1"=="" (
    echo [run-mcp] ERROR: missing module name.
    echo Usage: %~nx0 ^<module^> [args...]
    echo Example: %~nx0 nxp.mcp.gateway configs\gateway.stdio.yaml
    exit /b 1
)

REM --- Move into project root ---
cd /d "%SCRIPT_DIR%" || (
    echo [run-mcp] ERROR: cannot cd to "%SCRIPT_DIR%"
    exit /b 1
)

REM --- Activate virtual environment (only if it exists) ---
if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
) else (
    echo [run-mcp] INFO: no venv found at "%SCRIPT_DIR%.venv", using system Python >&2
)

REM --- Verify python is available on PATH ---
where python >nul 2>&1
if errorlevel 1 (
    echo [run-mcp] ERROR: 'python' not found on PATH. Install Python or create a .venv at "%SCRIPT_DIR%.venv".
    exit /b 1
)

REM --- Run python with all passed arguments ---
python -m %*
set "EXITCODE=%ERRORLEVEL%"

endlocal & exit /b %EXITCODE%
