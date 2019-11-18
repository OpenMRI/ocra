import struct
import time
import sys

from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket
import matplotlib.pyplot as plt
import numpy as np

from assembler import Assembler

socket = QTcpSocket()
connected = QAbstractSocket.ConnectedState
unconnected = QAbstractSocket.UnconnectedState

#_______________________________________________________________________________
#   Functions

# Connect to server
def conn_to_server(socket, ip_addr):
    socket.connectToHost(ip_addr, 1001)
    socket.waitForConnected(1000)
    if socket.state() == connected : print("Connection to host esteblished.")
    elif socket.state() == unconnected:
        print("Conncection to host failed.")
        return False
    else:
        print("TCP socket in state : ", socket.state())
        return socket.state()

# Disconnect from server
def disconn_from_server(socket):
    try: socket.disconnectFromHost()
    except: pass
    if socket.state() == unconnected :
        print("Disconnected from server.")
    else: print("Connection to server still established.")

# Read and plot acquired data
def readout():

    buf_size = 50000
    buffer = bytearray(8*buf_size)
    data = np.frombuffer(buffer, np.complex64)
    kspace_center = 475 # k center time = 1.9*250: echo time is at 1.9ms after acq start

    plt.show()
    kspace_ax = plt.gca()
    n = 0 # index for readout, read data n times (n = npe)

    while n < nnpe:

        datasize = 0

        while True: # Read data
            socket.waitForReadyRead()
            datasize = socket.bytesAvailable()
            print(datasize)
            if datasize == 8*buf_size:
                print("Readout finished : ", datasize)
                buffer[0:8*buf_size] = socket.read(8*buf_size)
                break
            else: continue

        freqaxis = np.linspace(-125000, 125000, 1000)
        mag = np.abs(data)
        pha = np.angle(data)

        k_amp[n, :] = mag[k_center-nnpe/2:k_center+nnpe/2]
        k_pha[n, :] = pha[k_center-nnpe/2:k_center+nnpe/2]

        k_amp_log10 = np.log10(k_amp)

        kspace_ax.imshow(k_amp_log10, cmap='plasma')
        plt.draw()
        plt.pause(0.0000001)

#_______________________________________________________________________________
#   Beginn of the Script

#################################
ip = '172.20.125.80'
seq = 'sequence/SE_workbench.txt'
#################################

npe_idx = 0 # index for number of phase encodings on server
nnpe = 4 # number of phase encodings, related to npe

# Establish connection between client and server
if conn_to_server(socket, ip) == False:
    sys.exit()

# Imaging GUI
socket.write(struct.pack('<I', 5))

# Upload Sequence
socket.write(struct.pack('<I', 3 << 28))
ass = Assembler()
btye_array = ass.assemble(seq)
socket.write(btye_array)
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten():
        print("Sequence uploaded.")
        break

time.sleep(1)

# Set gradient offset to 0
socket.write(struct.pack('<I', 2 << 28 | 5 << 24))
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten(): break

time.sleep(1)

# Start sequence
socket.write(struct.pack('<I', 2 << 28 | 0 << 24 | npe_idx << 7 | 8))
while(True): # Wait until bytes written
    if not socket.waitForBytesWritten(): break
print("Single line phase encoding SE.")

time.sleep(3)



# Readout data
#readout()

# Disconnect from host
disconn_from_server(socket)
