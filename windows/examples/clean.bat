@echo off
for %%x in (
        .exe
        .pcap
        .ilk
        .obj
        .pdb
        .routes
        .tr
        .plt
        .flowmonitor
        .idb
       ) do (
         echo Deleting *%%x
         del "*%%x"
         echo.
         echo =-=-=-=-=-=
       )