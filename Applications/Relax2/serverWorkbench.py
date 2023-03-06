################################################################################
#
#   Author:     David Schote (david.schote@ovgu.de)
#   Date:       11/27/2019
#
#   Workbench file for server tests
#
################################################################################

import sys
import struct
import time
import numpy as np
import matplotlib.pyplot as plt

from TCPsocket import socket, connected, unconnected
from dataHandler import data
from assembler import assembler

#-------------------------------------------------------------------------------
#   Functions
#-------------------------------------------------------------------------------
def conn_to_server(ip_addr):
    socket.connectToHost(ip_addr, 1001)
    socket.waitForConnected(1000)

    if socket.state() == connected :
        print("Connection to host esteblished.")
    elif socket.state() == unconnected:
        print("Conncection to host failed.")
        return False
    else:
        print("TCP socket in state : ", socket.state())
        return socket.state()

#-------------------------------------------------------------------------------
#   Definitions
#-------------------------------------------------------------------------------
ip = '192.168.1.130'
seq = 'sequence/FID.txt'#'sequence/img/2dSE.txt'

npe = 1
at = -10
freq = 11.289

grad_offset = 0
x_grad = 0
y_grad = 1
z_grad = 2
z2_grad = 3

size = 50000  # total data received (defined by the server code)
buffer = bytearray(8*size)
data = np.frombuffer(buffer, np.complex64)

#-------------------------------------------------------------------------------
#   Code
#-------------------------------------------------------------------------------

# Connect to server
conn_to_server(ip)

# Prepare plot
ax = plt.gca()
ax.grid(True)
plt.show()

if np.sign(grad_offset) < 0: sign = 1
else: sign = 0
# Check send values
print("Sending offset {} with sign {} to gradient {}.".format(abs(grad_offset), sign, x_grad))
# Send test command to set X gradient to grad_offset
#socket.write(struct.pack('<I', 5 << 28 | x_grad << 24 | sign << 20 | abs(grad_offset)))
#while(True): # Wait until bytes written
#    if not socket.waitForBytesWritten(): break
# Send frequency to server
socket.write(struct.pack('<I', 2 << 28| int(1.0e6 * freq)))
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten(): break
# Semd attemiaton to server
socket.write(struct.pack('<I', 3 << 28 | int(abs(at)/0.25)))
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten(): break

# Send Sequence
socket.write(struct.pack('<I', 4 << 28))
byte_array = assembler.assemble(seq)
socket.write(byte_array)
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten(): break

# Test 2D SE acquisition
#socket.write(struct.pack('<I', 6 << 28 | npe))

# Test FID
socket.write(struct.pack('<I', 1 << 28))

while(True): # Wait until bytes written
    if not socket.waitForBytesWritten(): break

# Perform npe-times readout
for n in range(npe):
    while True: # Read data
        socket.waitForReadyRead()
        datasize = socket.bytesAvailable()
        time.sleep(0.0001)
        if datasize == 8*size:
            print("Readout finished : ", datasize)
            buffer[0:8*size] = socket.read(8*size)
            break
        else: continue

    ax.plot(data[0:2000])

plt.show()
print("Acquisition finished.\n")

time.sleep(1)
