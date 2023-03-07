To do

At first go to relax2 and do
poetry install
then run with
poetry run python3 Relax2_main.py


Make sure that the xcb plugin is installed 
'''sudo apt-get install qt5dxcb-plugin'''


Trouble shooting

Problem:
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

Debug this with:

QT_DEBUG_PLUGINS=1 poetry run python3 Relax2_main.py

Likely xcb plugin not installed correctly