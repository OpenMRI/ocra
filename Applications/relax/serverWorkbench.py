import sys
import struct
import time
import numpy as np

from TCPsocket import socket, connected, unconnected
from dataHandler import data

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

ip = '172.20.125.200'

conn_to_server(ip)

grad_offset = -100

x_grad = 3
y_grad = 1
z_grad = 2
z2_grad = 3

if np.sign(grad_offset) < 0: sign = 1
else: sign = 0

# Check send values
print("Sending offset {} with sign {} to gradient {}.".format(abs(grad_offset), sign, x_grad))

# Send test command to set X gradient to grad_offset
socket.write(struct.pack('<I', 5 << 28 | x_grad << 24 | sign << 20 | abs(grad_offset)))
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten():
        break

time.sleep(1)

# Test 2D SE acquisition
npe = 32
socket.write(struct.pack('<I', 6 << 28 | npe))
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten():
        break

time.sleep(1)
