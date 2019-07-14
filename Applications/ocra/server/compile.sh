#!/bin/bash
# INP = $1
# OUT = $2
arm-linux-gnueabihf-gcc -static -O3 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard $1 -o $2 -lm
scp $2 root@heleus.nmr.mgh.harvard.edu:/root/server/
