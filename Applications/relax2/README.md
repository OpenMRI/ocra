## Installing relax2

To get started with relax2, enter the folder and 
```
poetry install
```
then run with
````
poetry run python3 Relax2_main.py
```

Make sure that the xcb plugin is installed 
```
sudo apt-get install qt5dxcb-plugin
```


## trouble shooting your installation

you might run into this problem:
```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
```

you can debug this with:

```
QT_DEBUG_PLUGINS=1 poetry run python3 Relax2_main.py
```

Likely you will find that the xcb plugin not installed correctly.

To use the latest development version of Relax2.0 you need to update the relax2 folder on your host computer (here a RaspberryPi) and the server and binaries files on the Red Pitaya 125-14 (see server folder README)!!!