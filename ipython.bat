:: ipython.bat
:: Runs IPython like in qtlab.bat, without actually starting QTLab.
::
:: Useful for testing and debugging.

:: Add Console2 to PATH
SET PATH=%CD%\3rd_party\Console2\;%PATH%

:: Check for version of python
:: Enthought Python Distribution

IF EXIST c:\epd27\python.exe (
    SET PYTHON_PATH=c:\epd27
    GOTO mark1
)
:: Anaconda Python Distribution
IF EXIST C:\Anaconda\python.exe (
    SET PYTHON_PATH=C:\Anaconda
    GOTO mark1
)

:: Standard distributions
IF EXIST c:\python27\python.exe (
    SET PYTHON_PATH=c:\python27
    GOTO mark1
)
IF EXIST c:\python26\python.exe (
    SET PYTHON_PATH=c:\python26
    GOTO mark1
)

echo Failed to find python distribution. Update path in qtlabgui.bat

:mark1

:: Run iPython
:: check if version < 0.11
IF EXIST "%PYTHON_PATH%\scripts\ipython.py" (
    start Console -w "IPython" -r "/k %PYTHON_PATH%\python.exe %PYTHON_PATH%\scripts\ipython.py -p sh"
    GOTO EOF
)
:: check if version >= 0.11
IF EXIST "%PYTHON_PATH%\scripts\ipython-script.py" (
    start Console -w "Ipython" -r "/k %PYTHON_PATH%\python.exe %PYTHON_PATH%\scripts\ipython-script.py"
    GOTO EOF
)

::start Console -w C:\Anaconda\pythonw.exe "C:\Anaconda\Scripts/ipython-script.py" qtconsole

echo Failed to run ipython.bat
pause
:EOF
