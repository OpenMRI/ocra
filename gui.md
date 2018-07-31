---
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

## Sockets  
The Python GUI communicates with the server on the Red Pitaya via an abstraction known as a [socket](https://www.wikiwand.com/en/Network_socket). A socket is an internal endpoint for sending or receiving data over a computer network. The client and server are both processes. In the client-server model, each process (i.e., the client and the server) establishes its own socket. The server socket resides at a particular IP address and, if used with TCP (as we do), requires a port number. The client socket needs to perform the following functions:
1. Create a socket
2. Connect the socket to the address of the server
3. Send and receive data with the functions read() and write()  

The server socket does the following:
1. Create a socket
2. Bind the socket to an address and port 3. Listen for a client on the port
4. Accept a connection to a client
5. Send and receive data

Our sockets use the reliable, stream-based TCP (Transmission Control Protocol) protocol to communicate over the network. On the client side, we used the software package PyQt’s `QTCPSocket()`, which provides useful abstractions. On the server side, we used the functions and abstractions defined in C’s native `socket.h` header file. In data transfer, the key functions were to `read()` and `write()` to the buffer.

## Setup  
In order to communicate with the Red Pitaya, you need to run the server program on it. First, ssh into the Red Pitaya. You need to have a static IP address set on it (follow the [Red Pitaya documentation](http://redpitaya.readthedocs.io/en/latest/quickStart/connect/connect.html).
```
ssh root@[IP address]
```
 Then, cat the bitfile:  
 ```
 cat pulsed_nmr_planB_05192018.bit >/dev/xdevcfg
 ```
 Now run the server:
 ```
 ./server/mri_lab_rt 60 32200
 ```
(or whatever folder the server program is located in). The first argument, `60`, is the length of the 90 degree hard RF pulse in samples. The second argument, `32200` is the amplitude of the pulse (arbitrary units).  The program is `mri_lab_rt.c` in the `server` folder. We provide a pre-compiled binary, but you can also compile it yourself with the command:  
```
arm-linux-gnueabihf-gcc -static -O3 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard /path/to/input.c -o output_file -lm

```  
Once you have the server running, the GUI can connect to it. If using the anaconda environment, activate it:  
Windows: `activate ocra_env`  
macOS and Linux: `source activate ocra_env`  

 Now run the GUI script:  
 ```
 python runMRI.py
 ```
You should see the following page:  
<img src="{{ site.github.url }}/assets/images/gui/welcome_page.png" alt="gui_welcome" width="700px"/>

Make sure that you are running python3 (any version of 3 should work, 3.4 and 3.6 have been tested). In order to use any of the GUIs, you need to connect to the server by entering the IP address. Press the `Configuration` button, then enter the IP address of the Red Pitaya. If the connection is successful, you will see the following window:  

<img src="{{ site.github.url }}/assets/images/gui/config_page.png" alt="gui_config" width="300px"/>
 
## FID GUI  
In this GUI, you can acquire FIDs, find the center frequency, and adjust the B0 field via first-order shims. A labeled screenshot is shown below.    
<img src="{{ site.github.url }}/assets/images/gui/fid_gui_labeled.png" alt="fid_labeled" width="700px"/>

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
<img src="{{ site.github.url }}/assets/images/gui/se_gui.png" alt="se_gui" width="700px"/>  

## Signals GUI  
The Signals GUI is an integrated GUI to test out sequences. Sequences are written in a custom Assembly-like language, which is described in the Sequence Programming section. Sequences are saved as `.txt` files and uploaded via the GUI. The GUI is pictured below.  
<img src="{{ site.github.url }}/assets/images/gui/signals_gui.png" alt="signals_gui" width="700px"/>  

There are the same time domain plot, frequency domain plot, and shim control panel as in the FID and spin echo GUIs. 
Additionally, there is a Sequence control panel. Here, you can upload sequences and adjust parameters (e.g. TE). 
There are some example sequences provided in the `sequence` folder. Full descriptions of the sequences are in the
Sequence Programming section.

## 2D Imaging GUI  
In this GUI, you can acquire 2D images, using one of our sequences or your own custom sequence. You can select the desired image size from a dropdown bar. The GUI updates the acquired kspace data and reconstructed image in real-time. A labeled screenshot is shown below.  
<img src="{{ site.github.url }}/assets/images/gui/2d_gui_labeled.png" alt="2d_gui" width="700px"/>  
As in the other GUIs, press the "Start" button to start the connection to the server. Then, select a sequence type from the dropdown bar (e.g. "Spin Echo", "Gradient Echo") and upload a sequence. The provided sequences are `.txt` files in the `sequence` folder, described in the Sequence Programming section.  
Then, select a matrix size. The image must be square and ranges from `4x4` to `256x256`. Note that saving the data becomes much slower as the image size increases. Press the `Acquire` button to acquire the image. The kspace data and reconstructed image will refresh in real-time.

In this GUI, the shims are loaded from previous settings and cannot be modified. The center frequency can be adjusted.

## 3D Imaging GUI  
In this GUI, you can acquire 3D images of a desired size. However, real-time reconstruction is not integrated and must be done outside of the GUI, e.g. via MATLAB. The GUI saves each partition as a different `.mat` file with the filename `acq_data_N.mat`, where `N` is the partition number. For instance, if there are 4 partitions, there will be 4 saved `.mat` files - `acq_data_1.mat` through `acq_data_4.mat`. You can change the filename via the `fnameprefix` attribute. A screenshot of the GUI is shown below.  
<img src={{ site.github.url }}/assets/images/gui/3d_gui.png alt="3d_gui" width="700px"/>  

## Real-time Rotation GUI  
This GUI is a simple demonstration of motion correction for a phantom with two tubes of water. If the phantom is inserted at an arbitrary angle, the console will correct the orientation  of the gradients such that the two tubes are horizontal in the image of the phantom. The GUI is pictured below.  
<img src="{{ site.github.url }}/assets/images/gui/rt_proj_gui.png" alt="rt_proj_gui" width="700px"/>  
The client (GUI) sends the current angle of the projection to the server, and the server rotates the gradients via multiplication with a rotation matrix. This is shown in the diagram below.  
<img src="{{ site.github.url }}/assets/images/gui/rt_feedback.png" alt="rt_feedback" width="700px"/>   
Then, the client performs a binary search to find the projection at which the two tubes collapse into one (the 0&deg; projection in the diagram below):  
<img src="{{ site.github.url }}/assets/images/gui/projections2.png" alt="projections" width="300px"/>  
The binary search is as follows: if the current max is greater than the previous max, increase the angle. If the current max
is less than the previous max, decrease the angle and decrease the step size. If the step size is less than the tolerance, return
the max angle. The angle at which the two tubes are horizontal is 90&deg; offset from the 0&deg; angle.  
To use the GUI, press Start. Select from the dropdown bar whether you want to acquire a 1D projection or a 2D image (spin echo, 64x64, TE=10ms). You can turn the dial to adjust the angle or use the arrowkeys. Press the "Find angle" button to perform the binary search and find the max angle. The value for the max angle will appear in the box next to the word "Max" once the search terminates.  

## Sequence Programming  
Pulse sequences are written in an Assembly-like language. Fundamentally, the language specifies events (e.g. turning on an amplifier gating signal) by writing to and reading from registers. At the lowest level, the FPGA determines the event type by an 8-bit number written to a register, where event is specified by one bit. The pulse bits are described in the table below:

| Bit        | Description |
|:----:|:-------------:|
| 0 | Tx Pulse |
| 1 | Rx Pulse |
| 2 | Grad Pulse |
| 4 | Tx Gate |
| 5 | Rx Gate |  

The unspecified bits are unused. These bit patterns can be grouped into four groups specific to execution:   
1. Wait
2. Fire RF pulse
3. Fire Gradient pulse
4. Fire RF and gradient pulses  


Each of these functions can be carried out with the receiver on and the receiver off, thus yielding 8 total possible groups. The bit RX_PULSE has inverted logic, so when it is on, the receiver is off. This is summarized in the table below. Here, `OR` refers to the bitwise OR operation.  

| Command       | Hex code         | Description  |
| :-------------: |:-------------:| :-----:|
| RX_PULSE      | 0x2 | All off/wait |
| 0x0     | 0x0      |   Only receiver on |
| TX_GATE `OR` TX_PULSE `OR` RX_PULSE | 0x13      | RF pulse |
| TX_GATE `OR` TX_PULSE | 0x11      | RF pulse with receiver on |
| GRAD_PULSE `OR` RX_PULSE | 0x6     | Gradient pulse |
| GRAD_PULSE | 0x4      | Gradient pulse with receiver on |
| TX_GATE `OR` TX_PULSE `OR` GRAD_PULSE `OR` RX_PULSE | 0x17      | RF and gradient pulse |
| TX_GATE `OR` TX_PULSE `OR` GRAD_PULSE|  0x15      | RF and gradient pulse with receiver on |  
  
  
The assembly-like language specifies low-level operations on registers. The language is specified by 64-bit words. However, because the bus between the ARM CPU and RAM is 32 bits, these words must be specified in two 32-bit integers. The bit order is little-Endian, meaning that the first 32-bit integer is the operand, and the second 32-bit integer contains the opcode. Like Assembly, there are commands to `JMP` to an address in memory, `LD64` a 64-bit integer into memory, and `PR` pulse a register for a certain amount of time. Each command is specified by a 6-bit opcode. The full list of commands is shown below.  


Instruction | Opcode | Format | Description |
| :----: |:------:| :-----:| :-----:|
NOP | 0b000000 | -- | Do nothing |
HALT | 0b011001 | -- | Halt the sequence |
DEC Rx | 0b000001 | A | Decrement register value by 1 |
INC Rx | 0b000010 | A | Increment register value by 1 |
LD64 Rx, Addr | 0b000100 | A | Load 64-bit integer from address Addr to Rx | 
JNZ Rx, Addr | 0b010000 | A | Jump to Addr if Rx! = 0 |
J Addr | 0b010111 | A | Jump to Addr |
PR Rx, Delay | 0b011101 | B | Pulse register Rx after 40-bit Delay |
TXOFFSET Offset | 0b001000 | B | Set offset of Tx (RF) pulse to Offset |
GRADOFFSET Offset | 0b001001 | B | Set offset of gradient pulse to Offset |  

There are two formats for instructions: Format A and Format B. In both formats, the highest 6 bits are used for the opcode. In Format A, bits 36:32 specify the register to operate on, while the lower 32 bits specify an address in memory. In Format B, bits 44:40 specify the register, and the lower 40 bits specify a constant. Formats A and B are illustrated below.  

Format A:  
<img src="{{ site.github.url }}/assets/images/gui/format_a.png" alt="format_a" width="700px"/>  

Format B:  
<img src="{{ site.github.url }}/assets/images/gui/format_b.png" alt="format_b" width="700px"/>  

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

You can upload sequences to either the Signals GUI or the 2D Imaging GUI.


