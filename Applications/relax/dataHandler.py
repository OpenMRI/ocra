# import general packages
import sys
import struct
import time
import paramiko

from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit, brentq
# just for debugging calculations:
import matplotlib.pyplot as plt

from TCPsocket import socket, connected, unconnected
from parameters import params
from assembler import Assembler

#   Trigger table on server when sending byte << 28:
#       0:  no trigger
#       1:  transmit
#       2:  set frequency
#       3:  set attenuation
#       4:  upload sequence
#       5:  set gradient offsets
#       6:  acquire 2D SE image

class data(QObject):

    # Init signal thats emitted when readout is processed
    readout_finished = pyqtSignal()
    t1_finished = pyqtSignal()
    t2_finished = pyqtSignal()
    uploaded = pyqtSignal(bool)

    def __init__(self):
        super(data, self).__init__()
        self.initVariables()

        # Read sequence files
        self.seq_fid = 'sequence/FID.txt'
        self.seq_se = 'sequence/SE_te.txt'
        self.seq_ir = 'sequence/IR_ti.txt'
        self.seq_sir = 'sequence/SIR_ti.txt'

        # Define Gradients
        self.GR_x = 0
        self.GR_y = 1
        self.GR_z = 2
        self.GR_z2 = 3
#_______________________________________________________________________________
#   Establish host connection and disconnection

    def conn_client(self, ip):

        socket.connectToHost(ip, 1001)
        socket.waitForConnected(1000)

        if socket.state() == connected :
            print("Connection to server esteblished.")
        elif socket.state() == unconnected:
            print("Conncection to server failed.")
            return False
        else:
            print("TCP socket in state : ", socket.state())
            return socket.state()

        self.set_at(params.at)
        self.set_freq(params.freq)

        return True

    def disconn_client(self):
        try:
            socket.disconnectFromHost()
        except: pass
        if socket.state() == unconnected :
            print("Disconnected from server.")
        else: print("Connection to server still established.")

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
#   Functions for Setting up sequence

    # Function to set default FID sequence
    def set_FID(self): # Function to init and set FID -- only acquire call is necessary afterwards

        self.assembler = Assembler()
        byte_array = self.assembler.assemble(self.seq_fid)
        socket.write(struct.pack('<I', 4 << 28))
        socket.write(byte_array)

        while(True): # Wait until bytes written
            if not socket.waitForBytesWritten():
                break

        socket.setReadBufferSize(8*self.size)
        self.ir_flag = False
        self.se_flag = False
        self.fid_flag = True
        print("\nFID sequence uploaded.")

    # Function to set default SE sequence
    def set_SE(self, TE=10): # Function to modify SE -- call whenever acquiring a SE

        # Change TE in sequence and push to server
        params.te = TE
        self.change_TE(params.te)#, REC)

        self.assembler = Assembler()
        byte_array = self.assembler.assemble(self.seq_se)
        socket.write(struct.pack('<I', 4 << 28))
        socket.write(byte_array)

        while(True): # Wait until bytes written
            if not socket.waitForBytesWritten(): break

        socket.setReadBufferSize(8*self.size)
        self.ir_flag = False
        self.se_flag = True
        self.fid_flag = False
        print("\nSE sequence uploaded with TE = ", TE, " ms.")

    # Function to change TE in sequence
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

    # Function to set default IR sequence
    def set_IR(self, TI=15):#, REC=1000): # Function to modify SE -- call whenever acquiring a SE

        params.ti = TI
        self.change_IR(params.ti, self.seq_ir)#, REC)

        self.assembler = Assembler()
        byte_array = self.assembler.assemble(self.seq_ir)
        socket.write(struct.pack('<I', 4 << 28))
        socket.write(byte_array)

        while(True): # Wait until bytes written
            if not socket.waitForBytesWritten(): break

        socket.setReadBufferSize(8*self.size)
        self.ir_flag = True
        self.se_flag = False
        self.fid_flag = False
        print("\nIR sequence uploaded with TI = ", TI, " ms.")#" and REC = ", REC, " ms.")

    # Function to change TI in IR sequence
    def change_IR(self, TI, seq):
        f = open(seq, 'r+') # Open sequence and read lines
        lines = f.readlines()
        # Modify TI time in the 8th last line
        lines[-14] = 'PR 3, ' + str(int(TI * 1000 - 198)) + '\t// wait&r\n'
        f.close() # Close and write/save modified sequence
        with open(seq, "w") as out_file:
            for line in lines:
                out_file.write(line)

    # Function to set default SIR sequence
    def set_SIR(self, TI=15):

        params.ti = TI
        self.change_SIR(params.ti, self.seq_sir)

        self.assembler = Assembler()
        byte_array = self.assembler.assemble(self.seq_sir)
        socket.write(struct.pack('<I', 4 << 28))
        socket.write(byte_array)

        while(True): # Wait until bytes written
            if not socket.waitForBytesWritten(): break

        socket.setReadBufferSize(8*self.size)
        print("\nSIR sequence uploaded with TI = ", TI, " ms.")#" and REC = ", REC, " ms.")

    # Function to change TI in SIR sequence
    def change_SIR(self, TI, seq):
        f = open(seq, 'r+') # Open sequence and read lines
        lines = f.readlines()
        # Modify TI time in the 8th last line
        #ines[-14] = 'PR 3, ' + str(int(TI * 1000 - 198)) + '\t// wait&r\n'
        #lines[-18] = 'PR 3, ' + str(int(TI * 1000 - 198)) + '\t// wait&r\n'
        lines[-9] = 'PR 3, ' + str(int(TI * 1000 - 198)) + '\t// wait&r\n'
        lines[-13] = 'PR 3, ' + str(int(TI * 1000 - 198)) + '\t// wait&r\n'
        f.close() # Close and write/save modified sequence
        with open(seq, "w") as out_file:
            for line in lines:
                out_file.write(line)

    # Set uploaded sequence
    def set_uploaded_seq(self, seq):
        print("Set uploaded Sequence.")
        self.assembler = Assembler()
        byte_array = self.assembler.assemble(seq)
        socket.write(struct.pack('<I', 4 << 28))
        socket.write(byte_array)

        while(True): # Wait until bytes written
            if not socket.waitForBytesWritten():
                break

        # Multiple function calls
        socket.setReadBufferSize(8*self.size)
        print(byte_array)
        print("Sequence uploaded to server.")
        self.uploaded.emit(True)

#_______________________________________________________________________________
#   Functions to Control Console

    # Function to triffer acquisition and perform single readout
    def acquire(self):
        t0 = time.time() # calculate time for acquisition
        socket.write(struct.pack('<I', 1 << 28))

        while True: # Read data
            socket.waitForReadyRead()
            datasize = socket.bytesAvailable()
            print(datasize)
            time.sleep(0.01)
            if datasize == 8*self.size:
                print("Readout finished : ", datasize)
                self.buffer[0:8*self.size] = socket.read(8*self.size)
                t1 = time.time() # calculate time for acquisition
                break
            else: continue

        print("Start processing readout.")
        self.process_readout()
        print("Start analyzing data.")
        self.analytics()
        print('Finished acquisition in {:.3f} ms'.format((t1-t0)*1000.0))
        # Emit signal, when data was read
        self.readout_finished.emit()

    # Function to set frequency
    def set_freq(self, freq):
        params.freq = freq
        socket.write(struct.pack('<I', 2 << 28| int(1.0e6 * freq)))
        print("Set frequency!")

    # Function to set attenuation
    def set_at(self, at):
        params.at = at
        socket.write(struct.pack('<I', 3 << 28 | int(abs(at)/0.25)))
        print("Set attenuation!")

    # Function to set gradient offsets
    def set_gradients(self, gx=None, gy=None, gz=None, gz2=None):

        if not gx == None:
            if np.sign(gx) < 0: sign = 1
            else: sign = 0
            socket.write(struct.pack('<I', 5 << 28 | self.GR_x << 24 | sign << 20 | abs(gx)))
        if not gy == None:
            if np.sign(gy) < 0: sign = 1
            else: sign = 0
            socket.write(struct.pack('<I', 5 << 28 | self.GR_y << 24 | sign << 20 | abs(gy)))
        if not gz == None:
            if np.sign(gz) < 0: sign = 1
            else: sign = 0
            socket.write(struct.pack('<I', 5 << 28 | self.GR_z << 24 | sign << 20 | abs(gz)))
        if not gz2 == None:
            if np.sign(gz2) < 0: sign = 1
            else: sign = 0
            #socket.write(struct.pack('<I', 5 << 28 | self.GR_z2 << 24 | sign << 20 | abs(gz2)))

        while(True): # Wait until bytes written
            if not socket.waitForBytesWritten():
                break

        self.acquire()
#_______________________________________________________________________________
#   Process and analyse acquired data

    # Function to process the readout: extract spectrum, real, imag and magnitude data
    def process_readout(self): # Read buffer part of interest and perform FFT

        # Max. data index and crop data
        self.data_idx = int(self.time * 250)
        self.dclip = self.data[0:self.data_idx]*1000.0*40.0; # Multiply by 1000 to obtain mV?
        timestamp = datetime.now()

        # Time domain data
        self.mag_t = np.abs(self.dclip)
        self.imag_t = np.imag(self.dclip)
        self.real_t = np.real(self.dclip)
        self.mag_con = np.convolve(self.mag_t, np.ones((50,))/50, mode='same')
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

    # Function to calculate parameter like snr and peak values
    def analytics(self): # calculate output parameters

        # Determine peak/maximum value:
        self.peak_value = round(np.max(self.fft_mag), 2)
        self.max_index = np.argmax(self.fft_mag)

        if self.peak_value > 0.5: # Peak threshold
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

#_______________________________________________________________________________
#   T1 Measurement

    # Acquires one or multiple T1 values through multiple IR's
    def T1_measurement(self, values, freq, recovery, **kwargs):
        print('T1 Measurement')

        avgPoint = kwargs.get('avgP', 1)
        avgMeas = kwargs.get('avgM', 1)
        seq_type = kwargs.get('seqType', 1)

        self.idxM = 0; self.idxP = 0
        self.T1 = []; self.R2 = []
        self.set_freq(freq)

        while self.idxM < avgMeas:
            print("Measurement : ", self.idxM+1, "/", avgMeas)
            self.measurement = []

            for self.ti in values:
                self.peaks = []

                if seq_type == 'sir':
                    self.set_SIR(self.ti)
                else: self.set_IR(self.ti)

                while self.idxP < avgPoint:
                    print("Datapoint : ", self.idxP+1, "/", avgPoint)
                    time.sleep(recovery/1000)
                    socket.write(struct.pack('<I', 1 << 28))

                    while True: # Readout data
                        socket.waitForReadyRead()
                        datasize = socket.bytesAvailable()
                        print(datasize)
                        time.sleep(0.1)
                        if datasize == 8*self.size:
                            print("IR readout finished : ", datasize)
                            self.buffer[0:8*self.size] = socket.read(8*self.size)
                            break
                        else: continue

                    print("Start processing IR readout.")
                    self.process_readout()
                    print("Start analyzing IR data.")
                    self.analytics()
                    print("Max. mag : ", np.max(self.mag_con))
                    print("sign real : ", np.sign(self.real_con[np.argmax(abs(self.real_con))]))
                    self.peaks.append(np.max(self.mag_con)*np.sign(self.real_con[np.argmin(self.real_con[0:50])]))
                    #self.peaks.append(self.peak_value*np.sign(self.real_con[np.argmin(self.real_con[0:50])]))
                    self.readout_finished.emit()
                    self.idxP += 1

                self.measurement.append(np.mean(self.peaks))
                self.idxP = 0

            # Calculate T1 value and error
            try: p, cov = curve_fit(self.T1_fit, values, self.measurement)
            except: # in case no fit found
                self.T1.append(float('nan'))
                self.R2.append(float('nan'))
                self.x_fit = float('nan')
                self.y_fit = float('nan')
                self.fit_params = float('nan')
                self.t1_finished.emit()
                self.idxM += 1
                continue

            def func(x):
                return p[0] - p[1] * np.exp(-p[2]*x)
            self.T1.append(round(1.44*brentq(func, values[0], values[-1]),2))
            self.R2.append(round(1-(np.sum((self.measurement - self.T1_fit(values, *p))**2)/(np.sum((self.measurement-np.mean(self.measurement))**2))),5))
            self.x_fit = np.linspace(0, int(1.2*values[-1]), 1000)
            self.y_fit = self.T1_fit(self.x_fit, *p)
            self.fit_params = p
            self.t1_finished.emit()
            self.idxM += 1

        return np.nanmean(self.T1), np.nanmean(self.R2)

    # Calculates fit for multiple IR's to determine t0
    def T1_fit(self, x, A, B, C):
        return A - B * np.exp(-C * x)

#_______________________________________________________________________________
#   T2 Measurement

    # Acquires one or multiple T2 values through multiple SE's
    def T2_measurement(self, values, freq, recovery, **kwargs):
        print('T1 Measurement')

        avgPoint = kwargs.get('avgP', 1)
        avgMeas = kwargs.get('avgM', 1)
        self.idxM = 0; self.idxP = 0
        self.T2 = []; self.R2 = []; self.measurement = []

        self.set_freq(freq)

        while self.idxM < avgMeas:
            print("Measurement : ", self.idxM+1, "/", avgMeas)
            self.measurement = []

            for self.te in values:
                self.peaks = []
                self.set_SE(self.te)

                while self.idxP < avgPoint:
                    print("Datapoint : ", self.idxP+1, "/", avgPoint)
                    time.sleep(recovery/1000)
                    socket.write(struct.pack('<I', 1 << 28))

                    while True:
                        socket.waitForReadyRead()
                        datasize = socket.bytesAvailable()
                        print(datasize)
                        time.sleep(0.1)
                        if datasize == 8*self.size:
                            print("IR readout finished : ", datasize)
                            self.buffer[0:8*self.size] = socket.read(8*self.size)
                            break
                        else: continue

                    print("Start processing SE readout.")
                    self.process_readout()
                    print("Start analyzing SE data.")
                    self.analytics()
                    self.peaks.append(np.max(self.mag_con))

                    self.readout_finished.emit()
                    self.idxP += 1

                self.measurement.append(np.mean(self.peaks))
                self.idxP = 0

            # Calculate T2 value and error
            try: p, cov = curve_fit(self.T2_fit, values, self.measurement, bounds=([0, self.measurement[0], 0], [10, 10000, 2]))
            except:
                self.T2.append(float('nan'))
                self.R2.append(float('nan'))
                self.x_fit = float('nan')
                self.y_fit = float('nan')
                self.fit_params = float('nan')
                self.t2_finished.emit()
                self.idxM += 1
                continue
            # Calculation of T2: M(T2) = 0.37*(func(0)) = 0.37(A+B), T2 = -1/C * ln((M(T2)-A)/B)
            self.T2.append(round(-(1/p[2])*np.log(((0.37*(p[0]+p[1]))-p[0])/p[1]), 5))
            self.R2.append(round(1-(np.sum((self.measurement - self.T2_fit(values, *p))**2)/(np.sum((self.measurement-np.mean(self.measurement))**2))),5))
            self.x_fit = np.linspace(0, int(1.2*values[-1]), 1000)
            self.y_fit = self.T2_fit(self.x_fit, *p)
            self.fit_params = p
            self.t2_finished.emit()
            self.idxM += 1

        return np.nanmean(self.T2), np.nanmean(self.R2)

    # Calculates fit for multiple SE's to determine drop of Mxy
    def T2_fit(self, x, A, B, C):
        return A + B * np.exp(-C * x)

#_______________________________________________________________________________
#   2D Image Acquisition
