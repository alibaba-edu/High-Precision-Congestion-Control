@echo off


for /r %%i in (*.cc) do (
	
     	echo "Building %%i" 
	cl.exe %%i -I "../ns-3-dev/headers" /D "WIN32" /D "NS3_LOG_ENABLE" /EHsc /c /RTC1 /Gd /Oy- /MDd /ZI
        link.exe /MACHINE:x86 %%~ni.obj ^
         "..\ns-3-dev\core\Debug\*.obj" ^
         "..\ns-3-dev\bridge\Debug\*.obj" ^
         "..\ns-3-dev\network\Debug\*.obj" ^
         "..\ns-3-dev\applications\Debug\*.obj" ^
         "..\ns-3-dev\config-store\Debug\*.obj" ^
         "..\ns-3-dev\stats\Debug\*.obj" ^
         "..\ns-3-dev\point-to-point\Debug\*.obj" ^
         "..\ns-3-dev\point-to-point-layout\Debug\*.obj" ^
         "..\ns-3-dev\mobility\Debug\*.obj" ^
         "..\ns-3-dev\propagation\Debug\*.obj" ^
         "..\ns-3-dev\mpi\Debug\*.obj" ^
         "..\ns-3-dev\nix-vector-routing\Debug\*.obj" ^
         "..\ns-3-dev\mesh\Debug\*.obj" ^
         "..\ns-3-dev\netanim\Debug\*.obj" ^
         "..\ns-3-dev\uan\Debug\*.obj" ^
         "..\ns-3-dev\wifi\Debug\*.obj" ^
         "..\ns-3-dev\wimax\Debug\*.obj" ^
         "..\ns-3-dev\winport\Debug\*.obj" ^
         "..\ns-3-dev\energy\Debug\*.obj" ^
         "..\ns-3-dev\spectrum\Debug\*.obj" ^
         "..\ns-3-dev\antenna\Debug\*.obj" ^
         "..\ns-3-dev\lte\Debug\*.obj" ^
         "..\ns-3-dev\flow-monitor\Debug\*.obj" ^
         "..\ns-3-dev\dsr\Debug\*.obj" ^
         "..\ns-3-dev\aodv\Debug\*.obj" ^
         "..\ns-3-dev\dsdn\Debug\*.obj" ^
         "..\ns-3-dev\olsr\Debug\*.obj" ^
         "..\ns-3-dev\buildings\Debug\*.obj" ^
         "..\ns-3-dev\virtual-net-device\Debug\*.obj" ^
         "..\ns-3-dev\tools\Debug\*.obj" ^
	 "..\ns-3-dev\csma\Debug\*.obj" ^
	 "..\ns-3-dev\csma-layout\Debug\*.obj" ^
	 "..\ns-3-dev\internet\Debug\*.obj" /DEBUG  /OUT:%%~ni.exe 
)