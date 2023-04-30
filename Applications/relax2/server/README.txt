1.) Remote access the Red Pitaya

The Red Pitaya (RP) needs to be connected with the host (here in use with a Raspberry Pi) via Ethernet.

Connect the RP with an ethernet cable directly to the Raspberry Pi.

Open a terminal on the Raspberry Pi and type:

arp

This will show all connected IPs. The Red Pitaya should be one of them.

If it shows no connections take a look at the cable connection and make sure the Red Pitaya is powered and booted up correctly (all Red Pitaya LEDs are yellow).

To remote access the Red Pitaya via ssh type:

ssh root@192.168.1.84 (general command: ssh root@[IP])


2.) Changing the server

Info:
- If not done, the relax2 folder needs to be updated before this (replace it with the newest one).
- The server can be found in the relax2/server folder and is called relax_server_dev.c

First you need to close the running server.

Open a terminal and connect via ssh. For that type in the terminal:

ssh root@192.168.1.84 (general command: ssh root@[IP])

This terminal is now the ssh (remote control) terminal for the Red Pitaya.

Stop the server on the Red Pitaya with the ssh terminal command:

/etc/init.d/relax_serverd stop

Open a second (parallel) terminal (this will be the Raspberry side) and copy the server from the Raspberry to the Red Pitaya with the command:

scp /home/pi/relax2/server/relax_server_dev.c root@192.168.1.84: (general command: scp [path]relax_server_dev.c root@[IP]:)

To compile the server, type the following command in the Red Pitaya ssh terminal:

arm-poky-linux-gnueabi-gcc –static –O3 –march=armv7-a –mcpu=cortex-a9 -
mtune=cortex-a9 –mfpu=neon –mfloat-abi=hard relax_server_dev.c –o
relax_server_dev –lm

(general command: arm-poky-linux-gnueabi-gcc –static –O3 –march=armv7-a –mcpu=cortex-a9 –
mtune=cortex-a9 –mfpu=neon –mfloat-abi=hard [NewServerFile] –o [NewServerBin] -lm

(It’s letter O by –O3, not number 0; (for “Optimization”))

When the compilation is finished restart the (new) server on the Red Pitaya. Type the start command in the ssh terminal:

/etc/init.d/relax_serverd start


3.) Manual start of the server

Manual start the server over the ssh terminal allows to see the fprint commands in the terminal.

Frist stop the autostarted server. Connect via ssh:

ssh root@192.168.1.84 (general command: ssh root@[IP])

Then type:

/etc/init.d/relax_serverd stop

Start the manual server with:

/home/root/relax_server_dev


4.) Copy the server autostart script to the RP

Connect to the RP via ssh and stop the relax_serverd script.

ssh root@192.168.1.84 (general command: ssh root@[IP])

Then type:

/etc/init.d/relax_serverd stop

In a second terminal (Raspberry side) copy the script to the RP.

scp /home/pi/relax2/server/relax_serverd root@192.168.1.84:/etc/init.d/

(general command: scp [path]relax_serverd root@[IP]:/etc/init.d/)

Type the start command in the ssh terminal:

/etc/init.d/relax_serverd start

5.) Changing the Red Pitaya binaries

Download the Bitfiles from the link of the OCRA main README and copy them in the relax2/server folder.

Connect to the RP via ssh and stop the relax_serverd script.

ssh root@192.168.1.84 (general command: ssh root@[IP])

Then type:

/etc/init.d/relax_serverd stop

Remove the old .bin, .dtbo and load_fpga_bit.sh file with:

rm ocra_mri.bit.bin
rm ocra_mri.dtbo
rm load_fpga_bit.sh

In a second terminal (Raspberry side) copy the new files to the Red Pitaya:

scp /home/pi/relax2/server/stemlab_125_14_ocra_mri.bit.bin root@192.168.1.84:
scp /home/pi/relax2/server/stemlab_125_14_ocra_mri.dtbo root@192.168.1.84:
scp /home/pi/relax2/server/load_fpga_bit.sh root@192.168.1.84:

Type the server start command in the ssh terminal:

/etc/init.d/relax_serverd start