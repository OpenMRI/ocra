# OCRA: The Open Source Console for Realtime Acquisitions

## General

This repository contains the seedlings for your very own MRI system. This is all this is, just a seedling. Okay, its a little more, it also contains a tool for controlling AC/DC shim coils.

Seriously though, this repository is mostly code generated back in 2017 to demonstrate that an MRI machine can be built using just a [Red Pitaya](https://www.redpitaya.com) as control electronics, significantly lowering the entrance threshold for researchers and hobbyists alike. We are trying to provide code to make this more than that as time allows. Certainly, if you like, your input on any aspect of this project is more than welcome!

If you're interested in learning more about getting started with OCRA, check out [The OCRA github page](https://openmri.github.io/ocra/).

We also have a blog page about some of the hardware at the [The OCRA blog](https://zeugmatographix.org/ocra/2020/07/23/welcome-to-the-ocra-blog/)

Its not straight-forward to build the FPGA bitfiles, at least until we provide better documentation. Until then, please find the bitfiles for the tabletop OCRA MRI setups here:
[Downloadable binaries](https://drive.google.com/drive/folders/1gWpjpM8BfPyvGyobRKDbgHXIaMaJ5J4R?usp=share_link)

## How to update Relax 2.0 on your OCRA Tabletop MRI System (RP125-14, RPi 3B+)

Make a backup of the rawdata, imagedata and protocol folder if necessary.

Remove the old relax2 folder completely and replace it with the newest relax2 folder from github.

Remote access the Red Pitaya via ssh and stop the running server.

Copy the relax_server_dev.c file from the updated relax2/server folder to the Red Pitaya, compile it and restart the server afterwards.

More detailed instructions can be found in the relax2/server/README.txt (chapter 1 and 2).



