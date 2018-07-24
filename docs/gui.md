---
layout: page
title: Python GUIs
tagline: OCRA MRI
description: Python GUIs for OCRA
---
## Python GUIs
We've created an educational Graphical User Interface (GUI) in Python intended to teach students about MRI. The GUIs are very similar in design to the [Tabletop GUIs](https://tabletop.martinos.org/index.php/Hardware:SourceCode), 
which are in MATLAB. The GUI is composed of a series of GUIs, each of which has its own function. These are:
* FID
* Spin Echo
* Signals
* 1D Projection
* 2D Imaging
* 3D Imaging
* Real-time Rotation

On this page, we provide a description of each GUI and how to use it.  
## FID GUI  
In this GUI, you can acquire FIDs, find the center frequency, and adjust the B0 field via first-order shims. A labeled screenshot is shown below.    
<>  
All GUIs share a time-domain plot, frequency domain plot, and control panel. In the control panel, you 
can start and stop the connection to the server with the "Start" and "Stop" buttons.  

Press the "Acquire" button below the Start and Stop buttons to acquire data. You can adjust the center frequency manually, 
by pressing the arrows or entering a number in the text box, or automatically - the box below the manual adjustment 
finds the center frequency automatically. By pressing "Apply", you can set the center frequency to the found peak. 

Finally, the remainder of the control panel is devoted to shims. There are three first order shims in the Tabletop system: x, y, and z.
The values of the shims can be adjusted via the sliders or the arrows next to the text box. The GUI calculates the peak of the FFT magnitude and 
FWHM to help determine the goodness of the shim. Once an optimal shim is found, you can save it by clicking on the "save shims" button, 
where it will be saved for this session. The saved values will be automatically loaded in the other GUIs. 
To have your saved shims appear on startup, modify the `gradient_offsets` attribute in the script `basicpara.py`. This is a list of three integers
for each shim in the format `[shim_x, shim_y, shim_z]`. You can also change the center frequency on startup by changing the `freq` attribute.

## Spin Echo GUI  
The Spin Echo GUI is very similar to the FID GUI, except that it acquires spin echoes instead of FIDs. A screenshot is shown below:  

<>  



## Signals GUI  
The Signals GUI is an integrated GUI to test out sequences. Sequences are written in a custom Assembly-like language, which is described in the 
Sequence Programming section. Sequences are saved as `.txt` files and uploaded via the GUI.  

There are the same time domain plot, frequency domain plot, and shim control panel as in the FID and spin echo GUIs. 
Additionally, there is a Sequence control panel. Here, you can upload sequences and adjust parameters (e.g. TE). 
There are some example sequences provided in the `sequence` folder. Full descriptions of the sequences are in the
Sequence Programming section.

## 2D Imaging GUI  
In this GUI, you can acquire 2D images, using one of our sequences or your own custom sequence.  

## 3D Imaging GUI  
## Real-time Rotation GUI  
## Sequence Programming  

We provide a number of example sequences. In the `basic` folder, there is a sequence for spin echo (`se_default.txt`) and FID (`fid_default.txt`). 
The spin echo sequence has a TE of 10ms.  

In the `img` folder, there are a number of sequences for different image acquisitions. Use the `txt` file 
that is not prepended with `hex` - for instance, in the `0 se` folder, use `se.txt`, not `se_hex.txt`. The `hex`
txt file is an automatically generated file with the commands in hexadecimal, used for debugging. We provide the following sequences:  
* Spin echo image (TE=10ms) - `0 se/se.txt`
* Gradient echo image (TE=1.7ms) - `1 gre/gre.txt`
* Slice-selective gradient echo image (TE=1.7ms) -`3 gre_slice/gre_slice.txt`
* Turbo spin echo (TE=10ms, ETL=2) - `4 tse/tse_etl2.txt`  
* EPI (Gradient echo) - `5 epi/epi_gre_64.txt`
* EPI (Spin echo) - `5 epi/epi_se_64.txt`
* Spiral (Gradient echo) - `7 spiral/spiral_gre.txt`
* Spiral (Spin echo) - `7 spiral/spiral_se.txt`


