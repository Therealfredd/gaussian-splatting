@echo off

set /p directory="Enter the directory: "

for /d %%s in ("%directory%\*") do (
    echo Training model: %%s
    python train.py -s "%%s"
	echo %%s Trained. 
)

echo Training complete.

