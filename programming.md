---
title: Programming
tagline: OCRA MRI
description: Programming pulse sequences
---
## Overview
This is a basic overview

## Instructions
This is a basic table of all the instructions available, and the opcodes associated with it.

Instruction | Opcode | Format | Description |
| ---- |:------:| :-----:| -----|
`NOP` | 0b000000 | -- | Do nothing |
`HALT` | 0b011001 | -- | Halt the sequence |
`DEC Rx` | 0b000001 | A | Decrement register value of `Rx` by 1 |
`INC Rx` | 0b000010 | A | Increment register value of `Rx` by 1 |
`LD64 Rx, addr` | 0b000100 | A | Load 64-bit integer from address `addr` to `Rx` | 
`JNZ Rx, addr` | 0b010000 | A | jump to `addr` if `Rx` != 0 |
`J addr` | 0b010111 | A | Unconditional jump to `addr` |
`PR Rx, delay` | 0b011101 | B | Pulse register `Rx` followed by 40-bit `delay` in clock cycles |
`TXOFFSET offset` | 0b001000 | B | Set offset of Tx (RF) pulse to `offset` |
`GRADOFFSET offset` | 0b001001 | B | Set offset of gradient pulse to `offset` |  
`LITR delay` | 0b000011 | B | Indicate end of TR, followed by 40-bit `delay` |
`RASTCSYNC clkmask` | 0b00101 | C | Reset raster clocks indicated in `clkmask` |

#### NOP
This instruction literally does nothing

#### HALT
This instruction ends the pulse sequence.

#### LD64

#### PR

#### J and JNZ

#### DEC and INC

#### RASTCSYNC
This instruction resets the raster clock of the clock indicated in the mask to start with the current clock cycle. All raster clocks in the OCRA are derived directly from the master clock of the FPGA by a divider, and are therefore ALWAYS synchronous. In order to start a raster clock cycle with a TR for example, the phase of the raster clock needs to reset with the beginning of the TR. This is accomplished by using this instruction at the beginning of the TR.

#### GRADOFFSET and TXOFFSET

#### LITR

## Tutorial

## Old

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
