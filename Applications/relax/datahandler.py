# import general packages
import sys
import struct
import time
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal

import numpy as np
import pandas as pd
import scipy.io as sp
# just for debugging calculations:
import matplotlib.pyplot as plt

from globalsocket import gsocket
from parameters import params
from assembler import Assembler

class data(QObject):

    # Init signal thats emitted when readout is processed
    readout_finished = pyqtSignal()

    def __init__(self):
        super(data, self).__init__()
        self.initVariables()

        # Read sequence files
        self.seq_fid = 'sequence/FID.txt'
        self.seq_se = 'sequence/SE_te.txt'
        self.seq_ir = 'sequence/IR_ti.txt'
#_______________________________________________________________________________
#   Establish host connection and disconnection

    def connectToHost(self): # Only called once in main class
        try:
            gsocket.connectToHost(params.host, 1001)
            print("Connection to host esteblished.")
            self.set_at(params.at)
            self.set_freq(params.freq)
        except:
            print("Conncection to host failed.")

    def exit_host(self): # Reset called whenever opening a controlcenter
        gsocket.write(struct.pack('<I', 5))
        try:
            gsocket.readyRead.disconnect()
            gsocket.disconnect()
            print("gsocket readyRead disconnected.")
        except:
            return
#_______________________________________________________________________________
#   Functions for initialization of variables

    def initVariables(self):
        # Flags
        self.ir_flag = False
        self.se_flag = False
        self.fid_flag = False

        # Variables
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8*self.size)
        self.data = np.frombuffer(self.buffer, np.complex64)

        # Variables
        self.time = 20
        self.freq_range = 250000
#_______________________________________________________________________________
#   Functions for controlling of host

#   Trigger bits:
#       0:  no trigger
#       1:  transmit
#       2:  set frequency
#       3:  set attenuation
#       4:  upload sequence

    def set_FID(self): # Function to init and set FID -- only acquire call is necessary afterwards

        try: gsocket.readyRead.disconnect()
        except: print("gsocket not (dis-)connected.")

        self.assembler = Assembler()
        byte_array = self.assembler.assemble(self.seq_fid)
        gsocket.write(struct.pack('<I', 4 << 28))
        gsocket.write(byte_array)

        while(True): # Wait until bytes written
            if not gsocket.waitForBytesWritten():
                break

        gsocket.setReadBufferSize(8*self.size)
        gsocket.readyRead.connect(self.readData)
        self.ir_flag = False
        self.se_flag = False
        self.fid_flag = True
        print("\nFID sequence uploaded.")

    def set_SE(self, TE=-1): # Function to modify SE -- call whenever acquiring a SE

        try: gsocket.readyRead.disconnect()
        except: print("gsocket still connected.")

        # Change TE in sequence and push to server
        if TE == -1: TE = params.te
        else: params.te = TE
        self.change_TE(params.te)

        self.assembler = Assembler()
        byte_array = self.assembler.assemble(self.seq_se)
        gsocket.write(struct.pack('<I', 4 << 28))
        gsocket.write(byte_array)

        while(True): # Wait until bytes written
            if not gsocket.waitForBytesWritten():
                break

        gsocket.setReadBufferSize(8*self.size)
        gsocket.readyRead.connect(self.readData)
        self.ir_flag = False
        self.se_flag = True
        self.fid_flag = False
        print("\nSE sequence uploaded with TE = ", TE, " ms.")

    def change_TE(self, TE): # Function for changing TE value in sequence -- called inside set_SE
        # Open sequence and read lines
        f = open(self.seq_se, 'r+')
        lines = f.readlines()
        # Modify TE time in the 8th last line
        lines[-10] = 'PR 3, ' + str(int(TE/2 * 1000 - 112)) + '\t// wait&r\n'
        lines[-6] = 'PR 3, ' + str(int(TE/2 * 1000 - 112)) + '\t// wait&r\n'
        # Close and write/save modified sequence
        f.close()
        with open(self.seq_se, "w") as out_file:
            for line in lines:
                out_file.write(line)

    def set_IR(self, TI=-1):#, REC=100): # Function to modify SE -- call whenever acquiring a SE
        # Defaults: TI = 50ms (time of inversion), REC = 100ms (equilibrium recovery time)
        try: gsocket.readyRead.disconnect()
        except: print("gsocket still connected.")

        # Change TI and REC in sequence and push to server
        if TI == -1: TI = params.te
        else: params.ti = TI
        self.change_IR(params.ti)#,REC)

        self.assembler = Assembler()
        byte_array = self.assembler.assemble(self.seq_ir)
        gsocket.write(struct.pack('<I', 4 << 28))
        gsocket.write(byte_array)

        while(True): # Wait until bytes written
            if not gsocket.waitForBytesWritten():
                break

        gsocket.setReadBufferSize(8*self.size)
        gsocket.readyRead.connect(self.readData)
        self.ir_flag = True
        self.se_flag = False
        self.fid_flag = False
        print("\nIR sequence uploaded with TI = ", TI, " ms.")#" and REC = ", REC, " ms.")

    def change_IR(self, TI):#, REC):
        # Open sequence and read lines
        f = open(self.seq_ir, 'r+')
        lines = f.readlines()
        # Modify TI time in the 8th last line
        lines[-14] = 'PR 3, ' + str(int(TI * 1000 - 198)) + '\t// wait&r\n'
        # Modify REC time in the 11th last line
        #lines[-11] = 'PR 4, ' + str(int(REC*1000)) + '\t// wait&r\n'
        # Close and write/save modified sequence
        f.close()
        with open(self.seq_ir, "w") as out_file:
            for line in lines:
                out_file.write(line)

    def acquire(self): # Trigger an acquisition
        # gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
        gsocket.write(struct.pack('<I', 1 << 28))
        self.t0 = time.time()
        print("\nAcquiring data.")

    def set_freq(self, freq): # Sets parameter and triggers acquisition
        params.freq = freq
        gsocket.write(struct.pack('<I', 2 << 28| int(1.0e6 * freq)))
        print("Set frequency!")

    def set_at(self, at): # Sets parameter and triggers acquisition
        params.at = at
        gsocket.write(struct.pack('<I', 3 << 28 | int(abs(at)/0.25)))
        print("Set attenuation!")
#_______________________________________________________________________________
#   Read and process acquired data from host

    def readData(self): # Read data from server

        # wait for enough data and read to self.buffer
        size = gsocket.bytesAvailable()
        if size == 8*self.size:
            print("Reading data... ", size)
            self.buffer[0:8*self.size] = gsocket.read(8*self.size)
            print(len(self.buffer))
            self.t1 = time.time()
        else: return

        print("Start processing readout.")
        self.process_readout()
        print("Start analyzing data.")
        self.analytics()
        # Emit signal, when data was read
        self.readout_finished.emit()
        print('Finished acquisition in {:.3f} ms'.format((self.t1-self.t0)*1000.0))

    def process_readout(self): # Read buffer part of interest and perform FFT

        # Max. data index and crop data
        self.data_idx = int(self.time * 250)
        self.dclip = self.data[0:self.data_idx]*1000; # Multiply by 1000 to obtain mV
        timestamp = datetime.now()

        # Time domain data
        self.mag_t = np.abs(self.dclip)
        self.imag_t = np.imag(self.dclip)
        self.real_t = np.real(self.dclip)
        self.real_con = np.convolve(self.real_t, np.ones((50,))/50, mode='same')
        self.time_axis = np.linspace(0, self.time, self.data_idx)

        # Frequency domain data
        self.freqaxis = np.linspace(-self.freq_range/2, self.freq_range/2, self.data_idx)   # 5000 points ~ 20ms
        self.fft = np.fft.fftshift(np.fft.fft(np.fft.fftshift(self.dclip), n=self.data_idx, norm='ortho'))   # Normalization through 1/sqrt(n)
        self.fft_mag = abs(self.fft)

        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        params.data = self.dclip
        params.freqaxis = self.freqaxis
        params.fft = self.fft_mag

        # Ampltiude and phase plot
        #fig, ax = plt.subplots(2,1)
        #ax[0].plot(self.time_axis, self.real_t)
        #ax[0].plot(self.time_axis, np.convolve(self.real_t, np.ones((50,))/50, mode='same'))
        #ax[1].plot(self.fft)
        #ax[1].psd(self.dclip, Fs=250, Fc=int(1.0e6 * params.freq))
        #fig.tight_layout(); plt.show()

        print("\tReadout processed.")

    def analytics(self): # calculate output parameters

        # Determine peak/maximum value:
        self.peak_value = round(np.max(self.fft_mag), 2)
        self.max_index = np.argmax(self.fft_mag)

        if self.peak_value > 5: # Peak threshold
            # Declarations
            win = int(self.data_idx/20)
            N = 50
            p_idx = self.max_index

            # Full with half maximum (fwhm):
            # Determine candidates inside peak window by substruction of half peakValue
            candidates = np.abs([x-self.peak_value/2 for x in self.fft_mag[p_idx-win:p_idx+win]])
            # Calculate index difference by findind indices of minima, calculate fwhm in Hz thereafter
            fwhm_idx = np.argmin(candidates[win:])+win-np.argmin(candidates[:win])
            self.fwhm_value = fwhm_idx*(abs(np.min(self.freqaxis))+abs(np.max(self.freqaxis)))/self.data_idx
            # Verification of fwhm calculation
            #plt.plot(candidates)
            #plt.show()

            # Signal to noise ratio (SNR):
            # Determine noise by substruction of moving avg from signal
            movAvg = np.convolve(self.fft_mag, np.ones((N,))/N, mode='same')
            noise = np.subtract(self.fft_mag, movAvg)
            # Calculate sdt. dev. outside a window, that depends on fwhm
            self.snr = round(self.peak_value/np.std([*noise[:p_idx-win], *noise[p_idx+win:]]),2)
            # Verification of snr calculation
            #plt.plot(self.freqaxis, self.fft_mag); plt.plot(self.freqaxis, movAvg);
            #plt.plot([*noise[:p_idx-win], *noise[p_idx+win:]])
            #plt.show()

            # Center frequency calculation:
            self.center_freq = params.freq + ((self.max_index - self.data_idx/2) * self.freq_range / self.data_idx ) / 1.0e6

        else:   # In case peak is under the threshold of 0.5
            self.peak_value = float('nan')
            self.fwhm_value = float('nan')
            self.center_freq = float('nan')
            self.snr = float('nan')

        print("\tData analysed.")
