#!/bin/bash

if [ -d /sys/kernel/config/device-tree/overlays/full ]; then
    rmdir /sys/kernel/config/device-tree/overlays/full
fi

echo 0 > /sys/class/fpga_manager/fpga0/flags
cp ~/stemlab_125_14_ocra_mri.bit.bin ~/stemlab_125_14_ocra_mri.dtbo /lib/firmware/

mkdir /sys/kernel/config/device-tree/overlays/full
echo -n "stemlab_125_ocra_mri.dtbo" > /sys/kernel/config/device-tree/overlays/full/path
