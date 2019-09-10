@echo off


for /r %%i in (*.exe) do (
	
     	echo "Executing %%i" 
        %%~ni.exe
)