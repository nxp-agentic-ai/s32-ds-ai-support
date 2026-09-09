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
REM check_problems.bat - canonical validation invocation for graft_driver_instance_mex
REM
REM Usage:
REM   check_problems.bat <name> <Tool>     [optional <s32ct_install>]
REM
REM   <name>  : basename used for the .mex (without extension); the script
REM             expects C:\tmp_mex\<name>.mex to exist already (copy your
REM             work-in-progress .mex there before invoking - that's how we
REM             avoid the "path-with-spaces breaks cmd redirection" trap).
REM   <Tool>  : Pins | Clocks | Peripherals | DCD | IVT | eFUSE | GTM | QuadSPI | FFC
REM
REM Output:
REM   stdout -> C:\tmp_mex\<name>_<tool>_stdout.txt
REM   stderr -> C:\tmp_mex\<name>_<tool>_stderr.txt
REM   The exit_code that toolsc.exe returned is ECHOED but should be
REM   IGNORED - it returns 0 even on validation errors. Use filter_problems.py
REM   on the stderr file to get the honest answer.

setlocal
set "NAME=%~1"
set "TOOL=%~2"
set "S32CT=%~3"
if "%S32CT%"=="" set "S32CT=%S32CT_INSTALL%"
if "%S32CT%"=="" (
    echo ERROR: S32CT install path not specified.
    echo Pass as third argument, or set the S32CT_INSTALL environment variable.
    echo Example: check_problems.bat probe Peripherals C:\NXP\S32ConfigTools.^<release^>
    exit /b 2
)
if "%NAME%"=="" goto :usage
if "%TOOL%"=="" goto :usage

if not exist "C:\tmp_mex\%NAME%.mex" (
    echo Cannot find C:\tmp_mex\%NAME%.mex - copy your .mex there first.
    exit /b 2
)

"%S32CT%\toolsc.exe" -Load "C:\tmp_mex\%NAME%.mex" -HeadlessTool %TOOL% -Enable -ShowProblems ^
    1> "C:\tmp_mex\%NAME%_%TOOL%_stdout.txt" ^
    2> "C:\tmp_mex\%NAME%_%TOOL%_stderr.txt"
echo exit=%ERRORLEVEL%  (DO NOT TRUST - filter the stderr file)
echo stderr -> C:\tmp_mex\%NAME%_%TOOL%_stderr.txt
exit /b 0

:usage
echo Usage: check_problems.bat ^<basename^> ^<Tool^> [^<s32ct_install^>]
echo Example: check_problems.bat probe Peripherals
exit /b 2
