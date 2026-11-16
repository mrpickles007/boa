@echo off
rem boa.cmd - BOA's command-line entry point on Windows: boa <subcommand> [args] (boa help lists them).
rem First, without Python, it checks BOA's prerequisites: git 2.31+ and Python 3.11+ (BOA_PYTHON of the config
rem beside this launcher, else the first working python3, python or py on PATH). If one is missing or too old it
rem changes nothing, says what is missing and where to get it, and exits 3: the agent installs it only with the
rem user's consent, then runs boa again. Otherwise it runs: <python> -I -B <this dir>\..\tools\boa.py <args>.
rem Written without labels (its one goto names a label that does not exist, see the last line), so it runs the same
rem with LF or CRLF line endings, and without delayed expansion, so a ! in a path or an argument is kept.
rem Known limit: when the calling cmd session itself runs with delayed expansion on (cmd /V:ON or the registry default),
rem the arguments are expanded in that setting after endlocal, so a ! in an argument is lost there.
setlocal EnableExtensions DisableDelayedExpansion
set "BOA_HERE=%~dp0"
set "PY="
set "FOUND="
set "CAND="
if exist "%BOA_HERE%..\config.env" for /f "usebackq tokens=1,* delims==" %%a in ("%BOA_HERE%..\config.env") do if "%%a"=="BOA_PYTHON" if not defined CAND set "CAND=%%~b"
if defined CAND set "CAND=%CAND:'=%"
if defined CAND "%CAND%" -I -c "import json, sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=%CAND%"
for %%n in (python3 python py) do if not defined PY for /f "delims=" %%p in ('where %%n 2^>nul') do if not defined PY "%%p" -I -c "import json, sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=%%p"
for %%n in (python3 python py) do if not defined PY for /f "delims=" %%p in ('where %%n 2^>nul') do set "FOUND=1"
set "GITV="
set "GITOK="
for /f "tokens=3" %%v in ('git --version 2^>nul') do set "GITV=%%v"
if defined GITV for /f "tokens=1,2 delims=." %%a in ("%GITV%") do if %%a GTR 2 set "GITOK=1"
if defined GITV for /f "tokens=1,2 delims=." %%a in ("%GITV%") do if %%a EQU 2 if %%b GEQ 31 set "GITOK=1"
set "BAD="
if not defined PY set "BAD=1"
if not defined GITOK set "BAD=1"
if defined BAD echo boa: BOA's prerequisites are not met; nothing was done. 1>&2
if not defined PY if defined FOUND echo   missing: Python 3.11 or newer (found: a python that is too old or does not run) 1>&2
if not defined PY if not defined FOUND echo   missing: Python 3.11 or newer (found: none) 1>&2
if not defined GITOK if defined GITV echo   missing: git 2.31 or newer (found: %GITV%) 1>&2
if not defined GITOK if not defined GITV echo   missing: git 2.31 or newer (found: none) 1>&2
if defined BAD echo   on Windows: Python from https://www.python.org/downloads/, Git for Windows from https://git-scm.com/downloads 1>&2
if defined BAD echo   Your agent can install them for you with your consent (and the rights to do it), then run boa again. 1>&2
if defined BAD exit /b 3
rem One line, read whole before it runs: %PY%, %BOA_HERE% and the arguments are expanded before endlocal (nothing is
rem left set in the caller's session). The goto to a label that does not exist ends this batch file's context (cmd
rem never reads this file again: boa uninstall deletes it while it runs) and the rest of the line still runs (the
rem goto's own error is silenced and then overwritten). The tool is the last command, so its exit code is the
rem launcher's, also through cmd /c (an `exit /b` with no number returns 0 there). The console title is left alone.
endlocal & goto #_undefined_# 2>nul & "%PY%" -I -B "%BOA_HERE%..\tools\boa.py" %*
