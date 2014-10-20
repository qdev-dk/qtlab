:: qtlabgui.bat
:: Runs QTlab GUI part on Windows

@ECHO OFF

:: If using a separate GTK install (and not the one provided in the
:: pygtk-all-in-one installer), uncomment and adjust the following
:: two lines to point to the appropriate locations
::SET GTK_BASEPATH=%CD%\3rd_party\gtk
::SET PATH=%CD%\3rd_party\gtk\bin;%CD%\3rd_party\gtk\lib;%PATH%

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

:: Run QTlab GUI
start %PYTHON_PATH%\pythonw.exe clients/client_gtk.py --module gui_client --config gui_client.cfg %*

:: Use this for easier debugging
:: start %PYTHON_PATH%\python.exe clients/client_gtk.py --module gui_client --config gui_client.cfg %*
