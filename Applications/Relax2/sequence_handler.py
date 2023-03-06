################################################################################
#
#   Author:     Marcus Prier, David Schote
#   Date:       4/12/2021
#
#   Main Application:
#   Relax 2.0 Main Application
#
################################################################################

import sys
import struct
import time
import os
import math

from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit, brentq
# just for debugging calculations:
import matplotlib.pyplot as plt

from TCPsocket import socket, connected, unconnected
from parameter_handler import params
from assembler import Assembler

class sequence:
    def __init__(self):

        params.loadParam()
        self.initVariables()
        
        self.seq_fid = 'Sequences/Spectroscopy/FID.txt'
        self.seq_se = 'Sequences/Spectroscopy/SE.txt'
        self.seq_ir_fid = 'Sequences/Spectroscopy/IR_FID.txt'
        self.seq_ir_se = 'Sequences/Spectroscopy/IR_SE.txt'
        self.seq_sir_fid = 'Sequences/Spectroscopy/SIR_FID.txt'
        self.seq_sir_se = 'Sequences/Spectroscopy/SIR_SE.txt'
        self.seq_epi = 'Sequences/Spectroscopy/EPI.txt'
        self.seq_epi_se = 'Sequences/Spectroscopy/EPI_SE.txt'
        self.seq_tse = 'Sequences/Spectroscopy/TSE.txt'
        
        self.seq_fid_gs = 'Sequences/Spectroscopy/FID_Gs.txt'
        self.seq_se_gs = 'Sequences/Spectroscopy/SE_Gs.txt'
        self.seq_ir_fid_gs = 'Sequences/Spectroscopy/IR_FID_Gs.txt'
        self.seq_ir_se_gs = 'Sequences/Spectroscopy/IR_SE_Gs.txt'
        self.seq_sir_fid_gs = 'Sequences/Spectroscopy/SIR_FID_Gs.txt'
        self.seq_sir_se_gs = 'Sequences/Spectroscopy/SIR_SE_Gs.txt'
        self.seq_epi_gs = 'Sequences/Spectroscopy/EPI_Gs.txt'
        self.seq_epi_se_gs = 'Sequences/Spectroscopy/EPI_SE_Gs.txt'
        self.seq_tse_gs = 'Sequences/Spectroscopy/TSE_Gs.txt'
        
        self.seq_rf_test = 'Sequences/Spectroscopy/RF_Test.txt'
        self.seq_grad_test = 'Sequences/Spectroscopy/Gradient_Test.txt'
        
        self.seq_2D_gre = 'Sequences/Imaging/2D_GRE.txt'
        self.seq_2D_se = 'Sequences/Imaging/2D_SE.txt'
        self.seq_2D_se_gs = 'Sequences/Imaging/2D_SE_Gs.txt'
        self.seq_2D_ir_se_gs = 'Sequences/Imaging/2D_IR_SE_Gs.txt'
        self.seq_2D_ir_gre = 'Sequences/Imaging/2D_IR_GRE.txt'
        self.seq_2D_ir_se = 'Sequences/Imaging/2D_IR_SE.txt'
        self.seq_2D_tse = 'Sequences/Imaging/2D_TSE.txt'
        self.seq_2D_gre_gs = 'Sequences/Imaging/2D_GRE_Gs.txt'
        self.seq_2D_ir_gre_gs = 'Sequences/Imaging/2D_IR_GRE_Gs.txt'
        self.seq_2D_tse_gs = 'Sequences/Imaging/2D_TSE_Gs.txt'
        self.seq_3D_se_gs = 'Sequences/Imaging/3D_SE_Gs.txt'
        self.seq_3D_tse_gs = 'Sequences/Imaging/3D_TSE_Gs.txt'
        self.seq_2D_epi_se = 'Sequences/Imaging/2D_EPI_SE.txt'
        self.seq_2D_epi = 'Sequences/Imaging/2D_EPI.txt'
        self.seq_2D_se_diff = 'Sequences/Imaging/2D_SE_DIFF.txt'
        self.seq_2D_fc_gre = 'Sequences/Imaging/2D_FC_GRE.txt'
        self.seq_2D_fc_se = 'Sequences/Imaging/2D_FC_SE.txt'
    
    def sequence_upload(self):
    
        self.Gradients_upload()
        self.Frequency_upload()
        self.RFattenuation_upload()
        
        if params.GUImode == 0:
            if params.sequence == 0:
                self.FID_setup()
                self.Sequence_upload()
                self.acquire_spectrum_FID()
            elif params.sequence == 1:
                self.SE_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE()
            elif params.sequence == 2:
                self.IR_FID_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE()
            elif params.sequence == 3:
                self.IR_SE_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE()
            elif params.sequence == 4:
                self.SIR_FID_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE()
            elif params.sequence == 5:
                self.SIR_SE_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE()
            elif params.sequence == 6:
                self.EPI_setup()
                self.Sequence_upload()
                self.acquire_spectrum_EPI()
            elif params.sequence == 7:
                self.EPI_SE_setup()
                self.Sequence_upload()
                self.acquire_spectrum_EPI_SE()
            elif params.sequence == 8:
                self.TSE_setup()
                self.Sequence_upload()
                self.acquire_spectrum_TSE()
            elif params.sequence == 9:
                self.FID_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_FID_Gs()
            elif params.sequence == 10:
                self.SE_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE_Gs()
            elif params.sequence == 11:
                self.IR_FID_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE_Gs()
            elif params.sequence == 12:
                self.IR_SE_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SE_Gs()
            elif params.sequence == 13:
                self.SIR_FID_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SIR_SE_Gs()
            elif params.sequence == 14:
                self.SIR_SE_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_SIR_SE_Gs()
            elif params.sequence == 15:
                self.EPI_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_EPI_Gs()
            elif params.sequence == 16:
                self.EPI_SE_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_EPI_SE_Gs()
            elif params.sequence == 17:
                self.TSE_Gs_setup()
                self.Sequence_upload()
                self.acquire_spectrum_TSE_Gs()
            elif params.sequence == 18:
                print('\033[1m' + 'Not active. Warning: In this sequence TX while RX is programmed! To activate the sequence uncomment the code below in sequence_handler.py.' + '\033[0m')
                self.rf_test_setup()
                self.Sequence_upload()
                self.acquire_rf_test()
            elif params.sequence == 19:
#                 print('\033[1m' + 'Not active. Warning: This sequence will test all gradient channels with pulses. To activate the sequence uncomment the code below in sequence_handler.py.' + '\033[0m')
                print('\033[1m' + 'Pulselength [us] = TR, Amplitude [mA] = Spoiler Amplitude' + '\033[0m')
                self.grad_test_setup()
                self.Sequence_upload()
                self.acquire_grad_test()
            else:
                print('Sequence not defined!')
            
        elif params.GUImode == 1:
            if params.sequence == 0:
                print('\033[1m' + 'Still WIP. Needs further optimization.' + '\033[0m')
                self.Image_GRE_setup()
                self.Sequence_upload()
                self.acquire_image_radial_GRE()
            elif params.sequence == 1:
                print('\033[1m' + 'Still WIP. Needs further optimization.' + '\033[0m')
                self.Image_SE_setup()
                self.Sequence_upload()
                self.acquire_image_radial_SE()
            elif params.sequence == 2:
                print('\033[1m' + 'WIP' + '\033[0m')
                #rad gre half
            elif params.sequence == 3:
                print('\033[1m' + 'WIP' + '\033[0m')
                #rad half se
            elif params.sequence == 4:
                self.Image_GRE_setup()
                self.Sequence_upload()
                self.acquire_image_GRE()
            elif params.sequence == 5:
                self.Image_SE_setup()
                self.Sequence_upload()
                self.acquire_image_SE()
            elif params.sequence == 6:
                self.Image_IR_GRE_setup()
                self.Sequence_upload()
                self.acquire_image_GRE()
            elif params.sequence == 7:
                self.Image_IR_SE_setup()
                self.Sequence_upload()
                self.acquire_image_SE()
            elif params.sequence == 8:
                print('\033[1m' + 'WIP' + '\033[0m')
                #sir gre
            elif params.sequence == 9:
                print('\033[1m' + 'WIP' + '\033[0m')
                #sir se
            elif params.sequence == 10:
                print('\033[1m' + 'Still WIP. Sampling limited in time. Readout timing needs to be adjusted in self.acquire_image_TSE()' + '\033[0m')
                self.Image_TSE_setup()
                self.Sequence_upload()
                self.acquire_image_TSE()
            elif params.sequence == 11:
                print('\033[1m' + 'Still WIP. Readout timing needs to be adjusted in self.acquire_image_EPI().' + '\033[0m')
                self.Image_EPI_setup()
                self.Sequence_upload()
                self.acquire_image_EPI()
            elif params.sequence == 12:
                print('\033[1m' + 'Still WIP. Readout timing needs to be adjusted in self.acquire_image_SE_EPI().' + '\033[0m')
                self.Image_EPI_SE_setup()
                self.Sequence_upload()
                self.acquire_image_EPI_SE()
            elif params.sequence == 13:
                self.Image_SE_Diff_setup()
                self.Sequence_upload()
                self.acquire_image_SE_Diff()
            elif params.sequence == 14:
                self.Image_FC_GRE_setup()
                self.Sequence_upload()
                self.acquire_image_GRE()
            elif params.sequence == 15:
                self.Image_FC_SE_setup()
                self.Sequence_upload()
                self.acquire_image_SE()
            elif params.sequence == 16:
                print('\033[1m' + 'WIP' + '\033[0m')
                #rad gre full slice
            elif params.sequence == 17:
                print('\033[1m' + 'WIP' + '\033[0m')
                #rad se full slice
            elif params.sequence == 18:
                print('\033[1m' + 'WIP' + '\033[0m')
                #rad gre half slice
            elif params.sequence == 19:
                print('\033[1m' + 'WIP' + '\033[0m')
                #rad half se slice
            elif params.sequence == 20:
                self.Image_GRE_Gs_setup()
                self.Sequence_upload()
                self.acquire_image_GRE_Gs()
            elif params.sequence == 21:
                self.Image_SE_Gs_setup()
                self.Sequence_upload()
                self.acquire_image_SE_Gs()
            elif params.sequence == 22:
                self.Image_IR_GRE_Gs_setup()
                self.Sequence_upload()
                self.acquire_image_GRE_Gs()
            elif params.sequence == 23:
                self.Image_IR_SE_Gs_setup()
                self.Sequence_upload()
                self.acquire_image_SE_Gs()
            elif params.sequence == 24:
                print('\033[1m' + 'WIP' + '\033[0m')
                #sir gre slice
            elif params.sequence == 25:
                print('\033[1m' + 'WIP' + '\033[0m')
                #sir se slice
            elif params.sequence == 26:
                print('\033[1m' + 'Still WIP. Sampling limited in time. Readout timing needs to be adjusted in self.acquire_image_TSE_Gs().' + '\033[0m')
                self.Image_TSE_Gs_setup()
                self.Sequence_upload()
                self.acquire_image_TSE_Gs()
            elif params.sequence == 27:
                print('\033[1m' + 'WIP' + '\033[0m')
                #epi gre slice
            elif params.sequence == 28:
                print('\033[1m' + 'WIP' + '\033[0m')
                #epi se slice
            elif params.sequence == 29:
                print('\033[1m' + 'WIP' + '\033[0m')
                #diff slice
            elif params.sequence == 30:
                print('\033[1m' + 'WIP' + '\033[0m')
                #fc gre slice
            elif params.sequence == 31:
                print('\033[1m' + 'WIP' + '\033[0m')
                #fc se slice
            elif params.sequence == 32:
                print('\033[1m' + 'WIP' + '\033[0m')
                #3d fft
            elif params.sequence == 33:
                self.Image_3D_SE_Gs_setup()
                self.Sequence_upload()
                self.acquire_image_3D_SE_Gs()
            elif params.sequence == 34:
                self.Image_3D_TSE_Gs_setup()
                self.Sequence_upload()
                self.acquire_image_3D_TSE_Gs()
            
            else:
                print('Sequence not defined!')
                
        if params.GUImode == 4:
            if params.sequence == 0:
                self.Image_GRE_setup()
                self.Sequence_upload()
                self.acquire_projection_GRE()
            elif params.sequence == 1:
                self.Image_SE_setup()
                self.Sequence_upload()
                self.acquire_projection_SE()
            elif params.sequence == 2:
                self.Image_GRE_setup()
                self.Sequence_upload()
                self.acquire_projection_GRE_angle()
            elif params.sequence == 3:
                self.Image_SE_setup()
                self.Sequence_upload()
                self.acquire_projection_SE_angle() 
            else:
                print('Sequence not defined!')
        
    def conn_client(self):
        socket.connectToHost(params.ip, 1001)
        socket.waitForConnected(1000)

        if socket.state() == connected :
            print('Connection to server esteblished.')
            return True
        elif socket.state() == unconnected:
            print('Conncection to server failed.')
            return False
        else:
            print('TCP socket in state : ', socket.state())
            return socket.state()

    def disconn_client(self):
        try:
            socket.disconnectFromHost()
        except: pass
        if socket.state() == unconnected :
            print('Disconnected from server.')
        else: print('Connection to server still established.')


    def initVariables(self):
        self.buffer = bytearray(8 * params.samples)
        self.data = np.frombuffer(self.buffer, np.complex64)

        self.freq_old = 0
        self.att_old = 0

    def Frequency_upload(self):
        if params.frequency != self.freq_old:
            socket.write(struct.pack('<IIIIIIIIII', 2, 0, 0, 0, 0, 0, 0, 0, 0, int(1.0e6 * params.frequency)))
            print('Set frequency!')
            self.freq_old = params.frequency
        
    def RFattenuation_upload(self):
        #if params.RFattenuation != self.att_old:
        socket.write(struct.pack('<IIIIIIIIII', 3, 0, 0, 0, 0, 0, 0, 0, 0, int(abs(-31.75)/0.25)))
        socket.write(struct.pack('<IIIIIIIIII', 3, 0, 0, 0, 0, 0, 0, 0, 0, int(abs(params.RFattenuation)/0.25)))
        print('Set attenuation!')
        #self.att_old = params.RFattenuation
        
    def Gradients_upload(self):
        if params.grad[0] != None:
            if np.sign(params.grad[0]) < 0: sign = 1
            else: sign = 0
            socket.write(struct.pack('<IIIIIIIIII', 5, 0, 0, 0, 0, 0, 0, 0, 0, sign << 24 | abs(params.grad[0])))
        if params.grad[1] != None:
            if np.sign(params.grad[1]) < 0: sign = 1
            else: sign = 0
            socket.write(struct.pack('<IIIIIIIIII', 5, 0, 0, 0, 0, 0, 0, 0, 1, sign << 24 | abs(params.grad[1])))
        if params.grad[2] != None:
            if np.sign(params.grad[2]) < 0: sign = 1
            else: sign = 0
            socket.write(struct.pack('<IIIIIIIIII', 5, 0, 0, 0, 0, 0, 0, 0, 2, sign << 24 | abs(params.grad[2])))
        if params.grad[3] != None:
            if np.sign(params.grad[3]) < 0: sign = 1
            else: sign = 0
            socket.write(struct.pack('<IIIIIIIIII', 5, 0, 0, 0, 0, 0, 0, 0, 3, sign << 24 | abs(params.grad[3])))

        while(True):
            if not socket.waitForBytesWritten():
                break
        print('Set shims!')
        
    # Free Induction Decay sequence    
    def FID_setup(self):
        if int(params.TE * 1000 - params.flippulselength/2 - params.TS * 1000 / 2) < 0:
            params.TE = (params.flippulselength/2 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_fid, 'r+')
        lines = f.readlines()
        lines[-13] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength/2 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_fid, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_fid
        
        print("FID setup complete!")
    
    #Spin Echo Sequence
    def SE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 20 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_se, 'r+')
        lines = f.readlines()
        lines[-28] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-26] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-23] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_se
        
        print("SE setup complete!")
        
    # Inversion Recovery Free Induction Decay sequence    
    def IR_FID_setup(self):
        if int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2) < 0:
            params.TI = (params.RFpulselength + 10 + 100 + params.flippulselength / 2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE * 1000 - params.flippulselength/2 - params.TS * 1000 / 2) < 0:
            params.TE = (params.flippulselength/2 + params.TS * 1000 / 2) / 1000 
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_ir_fid, 'r+')
        lines = f.readlines()
        lines[-18] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-16] = 'PR 3, ' + str(int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2)) + '\t// Pause\n'
        lines[-13] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength/2 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_ir_fid, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_ir_fid
        
        print("IR FID setup complete!")
    
    # Inversion Recovery Spin Echo sequence    
    def IR_SE_setup(self):  
        if int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2) < 0:
            params.TI = (params.RFpulselength + 10 + 100 + params.flippulselength / 2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 20 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_ir_se, 'r+')
        lines = f.readlines()
        lines[-33] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2)) + '\t// Pause\n'
        lines[-28] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-26] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-23] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_ir_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_ir_se
        
        print("IR SE setup complete!")
        
    # Free Induction Decay sequence    
    def SIR_FID_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - 100 - params.flippulselength/2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 20 + 100 + params.flippulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms') 
        self.TFID = 1
        if int(self.TFID * 1000 - params.flippulselength/2 - params.TS * 1000 / 2) < 0:
            self.TFID = (params.flippulselength/2 + params.TS * 1000 / 2) / 1000
            print('T FID set to:', self.TFID, 'ms')    
            
        f = open(self.seq_sir_fid, 'r+')
        lines = f.readlines()
        lines[-33] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-28] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-23] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-19] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-16] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - 100 - params.flippulselength/2)) + '\t// Pause\n'
        lines[-13] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        #lines[-11] = 'PR 3, ' + str(int(params.TE * 1000 - params.RFpulselength + 10 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-11] = 'PR 3, ' + str(int(self.TFID * 1000 - params.flippulselength/2 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_sir_fid, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_sir_fid
        
        print("SIR FID setup complete!")

    #Spin Echo Sequence
    def SIR_SE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 20 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_sir_se, 'r+')
        lines = f.readlines()
        lines[-48] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-46] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-43] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-38] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-34] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-31] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - 100 - params.flippulselength/2)) + '\t// Pause\n'
        lines[-28] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-26] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-23] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_sir_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_sir_se
        
        print("SIR SE setup complete!")
        
    def EPI_setup(self):
        if int(params.TE * 1000 - params.flippulselength / 2 - 50 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200) < 0:
            params.TE = (params.flippulselength / 2 + 50 + 200 + params.GROpretime + 400 + params.TS * 1000 + 400 + params.TS * 1000 + 200) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_epi, 'r+')
        lines = f.readlines()
        lines[-30] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-28] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength / 2 - 50 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200)) + '\t// Pause\n'
        lines[-25] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-19] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-16] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_epi, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_epi
        
        print("EPI setup complete!")
        
    def EPI_SE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 60 + 200 + params.GROpretime + 400 + params.TS * 1000 + 400 + params.TS * 1000 + 200) / 1000 *2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_epi_se, 'r+')
        lines = f.readlines()
        lines[-45] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-43] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-40] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-35] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-28] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200)) + '\t// Pause\n'
        lines[-25] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-19] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-16] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_epi_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_epi_se
        
        print("EPI (SE) setup complete!")
        
    #Turbo Spin Echo Sequence
    def TSE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 20 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_tse, 'r+')
        lines = f.readlines()
        lines[-76] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-74] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-71] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-66] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-62] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-59] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-58] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-57] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-54] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-50] = 'PR 6, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-46] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-43] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-42] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-41] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-38] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-34] = 'PR 6, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-30] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-27] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-26] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-25] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-22] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 6, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_tse, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_tse
        
        print("TSE setup complete!")
        
    def FID_Gs_setup(self):
        if int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 20 - params.TS * 1000 / 2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 20 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_fid_gs, 'r+')
        lines = f.readlines()
        lines[-18] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_fid_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_fid_gs
        
        print("FID (slice) setup complete!")
    
    #2D Spin Echo (Slice Select) Sequence   
    def SE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 30 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 40 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_se_gs, 'r+')
        lines = f.readlines()
        lines[-33] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-29] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-26] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-23] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_se_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_se_gs
        
        print("SE (slice) setup complete!")
        
    def IR_FID_Gs_setup(self):
        if int(params.TI * 1000 - 4*params.RFpulselength - 20 - 200 - 4*params.flippulselength/2) < 0:
            params.TI = (4*params.RFpulselength + 20 + 200 + 4*params.flippulselength/2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 20 - params.TS * 1000 / 2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 20 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_ir_fid_gs, 'r+')
        lines = f.readlines()
        lines[-25] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-23] = 'PR 3, ' + str(int(params.TI * 1000 - 4*params.RFpulselength - 20 - 200 - 4*params.flippulselength/2)) + '\t// Pause\n'
        lines[-18] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_ir_fid_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_ir_fid_gs
        
        print("IR FID (slice) setup complete!")
        
    def IR_SE_Gs_setup(self):
        if int(params.TI * 1000 - 4*params.RFpulselength - 20 - 200 - 4*params.flippulselength/2) < 0:
            params.TI = (4*params.RFpulselength + 20 + 200 + 4*params.flippulselength/2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 30 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 40 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_ir_se_gs, 'r+')
        lines = f.readlines()
        lines[-40] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-38] = 'PR 3, ' + str(int(params.TI * 1000 - 4*params.RFpulselength - 20 - 200 - 4*params.flippulselength/2)) + '\t// Pause\n'
        lines[-33] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-29] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-26] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-23] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_ir_se_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_ir_se_gs
        
        print("IR SE (slice) setup complete!")
        
    def SIR_FID_Gs_setup(self):
        if int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 20 - params.TS * 1000 / 2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 20 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        self.TFID = 1
        if int(self.TFID * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 20 - params.TS * 1000 / 2) < 0:
            self.TFID = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 20 + params.TS * 1000 / 2) / 1000
            print('T FID set to:', self.TFID, 'ms') 
        
        f = open(self.seq_sir_fid_gs, 'r+')
        lines = f.readlines()
        lines[-40] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-38] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-35] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-30] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-26] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-23] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - 200 - 4*params.flippulselength/2)) + '\t// Pause\n'
        lines[-18] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-11] = 'PR 3, ' + str(int(self.TFID * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 20 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_sir_fid_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_sir_fid_gs
        
        print("SIR FID (slice) setup complete!")
        
    def SIR_SE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 30 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 40 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_sir_se_gs, 'r+')
        lines = f.readlines()
        lines[-55] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-53] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-50] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-45] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-41] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-38] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - 200 - 4*params.flippulselength/2)) + '\t// Pause\n'
        lines[-33] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-29] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-26] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-23] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_sir_se_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_sir_se_gs
        
        print("SIR SE (slice) setup complete!")
        
    def EPI_Gs_setup(self):
        if int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 60 + 200 + params.GROpretime + 400 + params.TS * 1000 + 400 + params.TS * 1000 + 200) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_epi_gs, 'r+')
        lines = f.readlines()
        lines[-35] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-28] = 'PR 3, ' + str(int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200)) + '\t// Pause\n'
        lines[-25] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-19] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-16] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_epi_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_epi_gs
        
        print("EPI (slice) setup complete!")
        
    #2D EPI SE (Slice Select) Sequence   
    def EPI_SE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 4*params.RFpulselength - 200 - params.crushertime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200) < 0:
            params.TE = (4*params.RFpulselength + 200 + params.crushertime + 200 + 60 + 200 + params.GROpretime + 400 + params.TS * 1000 + 400 + params.TS * 1000 + 200) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 40 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_epi_se_gs, 'r+')
        lines = f.readlines()
        lines[-50] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-46] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-43] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-40] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-35] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-28] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.RFpulselength - 200 - params.crushertime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200)) + '\t// Pause\n'
        lines[-25] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-19] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-16] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_epi_se_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_epi_se_gs
        
        print("EPI SE (slice) setup complete!")
        
    def TSE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 30 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 40 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_tse_gs, 'r+')
        lines = f.readlines()
        lines[-81] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-77] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-74] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-71] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-66] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-62] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-59] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-58] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-57] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 10 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-54] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-50] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-46] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-43] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-42] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-41] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 10 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-38] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-34] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-30] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-27] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-26] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-25] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 10 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-22] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-18] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-14] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-11] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 30 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-10] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_tse_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_tse_gs
        
        print("TSE (slice) setup complete!")

    def rf_test_setup(self):
        f = open(self.seq_rf_test, 'r+')
        lines = f.readlines()
        lines[-6] = 'PR 6, ' + str(int(4*params.flippulselength)) + '\t// Sampling window\n'
        f.close()
        with open(self.seq_rf_test, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_rf_test
        
        print("RF test sequence setup complete!")
        
        
    #2D Gradient Echo Sequence   
    def grad_test_setup(self):
#         if int(params.TE * 1000 - params.flippulselength / 2 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
#             params.TE = (params.flippulselength / 2 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000
#             print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_grad_test, 'r+')
        lines = f.readlines()
        lines[-7] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
        lines[-10] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
        lines[-13] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
        lines[-16] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
        lines[-22] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
        lines[-25] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
        lines[-28] = 'PR 3, ' + str(int(params.TR)) + '\t// Grad pulse length\n'
#         lines[-19] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength / 2 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
#         lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
#         lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
#         lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_grad_test, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_grad_test
        
        print("Gradient test sequence setup complete!")

    #2D Gradient Echo Sequence   
    def Image_GRE_setup(self):
        if int(params.TE * 1000 - params.flippulselength / 2 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (params.flippulselength / 2 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_2D_gre, 'r+')
        lines = f.readlines()
        lines[-21] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength / 2 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_gre, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_gre
        
        print("2D GRE setup complete!")
    
    # 2D Spin Echo Sequence
    def Image_SE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_se, 'r+')
        lines = f.readlines()
        lines[-36] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-34] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-26] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-22] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_se
        
        print("2D SE setup complete!")
    
    # 2D Inversion Recovery GRE Sequence
    def Image_IR_GRE_setup(self):         
        if int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2) < 0:
            params.TI = (params.RFpulselength + 10 + 100 + params.flippulselength / 2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE * 1000 - params.flippulselength / 2 - 10 - 30 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (params.flippulselength / 2 + 10 + 30 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
            
        f = open(self.seq_2D_ir_gre, 'r+')
        lines = f.readlines()
        lines[-26] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-24] = 'PR 3, ' + str(int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2)) + '\t// Pause\n'
        lines[-21] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength / 2 - 10 - 30 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_ir_gre, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_ir_gre
        
        print("2D IR GRE setup complete!")
    
    # 2D Inversion Recovery SE Sequence    
    def Image_IR_SE_setup(self):        
        if int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2) < 0:
            params.TI = (params.RFpulselength - 10 - 100 - params.flippulselength / 2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_ir_se, 'r+')
        lines = f.readlines()
        lines[-41] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-39] = 'PR 3, ' + str(int(params.TI * 1000 - params.RFpulselength - 10 - 100 - params.flippulselength / 2)) + '\t// Pause\n'
        lines[-36] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-34] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-26] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-22] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_ir_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_ir_se
        
        print("2D IR SE setup complete!")
        
    #2D Gradient Echo (Slice Select) Sequence   
    def Image_GRE_Gs_setup(self):
        if int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 45 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 45 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_2D_gre_gs, 'r+')
        lines = f.readlines()
        lines[-26] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-22] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 45 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_gre_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_gre_gs
        
        print("2D GRE (slice) setup complete!")
    
    #2D Spin Echo (Slice Select) Sequence   
    def Image_SE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 45 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 45 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_2D_se_gs, 'r+')
        lines = f.readlines()
        lines[-41] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-37] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-34] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 45 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-26] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-22] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_se_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_se_gs
        
        print("2D SE (slice) setup complete!")
        
    def Image_IR_GRE_Gs_setup(self):
        if int(params.TI * 1000 - 2*4*params.RFpulselength/2 - 20 - 100 - 100 - 4*params.flippulselength/2) < 0:
            params.TI = (2*4*params.RFpulselength/2 + 20 + 100 + 100 + 4*params.flippulselength/2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_2D_ir_gre_gs, 'r+')
        lines = f.readlines()
        lines[-33] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.TI * 1000 - 2*4*params.RFpulselength/2 - 20 - 100 - 100 - 4*params.flippulselength/2)) + '\t// Pause\n'
        lines[-26] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-22] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_ir_gre_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_ir_gre_gs
        
        print("2D IR GRE (slice) setup complete!")
        
    def Image_IR_SE_Gs_setup(self):
        if int(params.TI * 1000 - 2*4*params.RFpulselength/2 - 20 - 100 - 100 - 4*params.flippulselength/2) < 0:
            params.TI = (2*4*params.RFpulselength/2 + 20 + 100 + 100 + 4*params.flippulselength/2) / 1000
            print('TI to short!! TI set to:', params.TI, 'ms')
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 40 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_ir_se_gs, 'r+')
        lines = f.readlines()
        lines[-48] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-46] = 'PR 3, ' + str(int(params.TI * 1000 - 2*4*params.RFpulselength/2 - 20 - 100 - 100 - 4*params.flippulselength/2)) + '\t// Pause\n'
        lines[-41] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-37] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-34] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-26] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-22] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_ir_se_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_ir_se_gs
        
        print("2D IR SE (slice) setup complete!")
        
    def Image_3D_SE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 40 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 40 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_3D_se_gs, 'r+')
        lines = f.readlines()
        lines[-41] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-37] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-34] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 40 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-26] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-22] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_3D_se_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_3D_se_gs
        
        print("3D FFT SE (slab) setup complete!")
        
    def Image_3D_TSE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 55 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 55 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 45 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 45 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_3D_tse_gs, 'r+')
        lines = f.readlines()
        lines[-140] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-136] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-133] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 45 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-130] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-125] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-121] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-118] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-115] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-112] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-106] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-103] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 55 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-100] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-95] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-91] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-88] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 50 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-85] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-79] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-73] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-70] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 50 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-67] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-62] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-58] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-55] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 50 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-52] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-46] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-40] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-37] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 50 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-34] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-29] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-25] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 55 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-19] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_3D_tse_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_3D_tse_gs
        
        print("3D FFT TSE (slab) setup complete!")
        
    #2D Turbo Spin Echo Sequence
    def Image_TSE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 55 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 55 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_tse, 'r+')
        lines = f.readlines()
        lines[-132] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-130] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-127] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-122] = 'PR 6, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-118] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-115] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 45 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-112] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-109] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-103] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-100] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 50 - params.RFpulselength)) + '\t// Pause\n'
        lines[-97] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-93] = 'PR 6, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-89] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length l89\n'
        lines[-86] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 45 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-83] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-77] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-71] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-68] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 55 - params.RFpulselength)) + '\t// Pause\n'
        lines[-65] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-61] = 'PR 6, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse l61\n'
        lines[-57] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-54] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 55 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-51] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-45] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-39] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-36] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 50 - params.RFpulselength)) + '\t// Pause\n'
        lines[-33] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-29] = 'PR 6, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-25] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 55 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-19] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_tse, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_tse
        
        print("2D TSE setup complete!")
        
    # 2D Turbo Spin Echo (Slice Select) Sequence
    def Image_TSE_Gs_setup(self):
        if int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 55 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (2*4*params.RFpulselength/2 + 200 + params.crushertime + 200 + 55 + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
        if int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 45 - 2*4*params.RFpulselength/2) < 0:
            params.TE = (4*params.flippulselength/2 + 400 + params.GSposttime + 200 + 200 + params.crushertime + 200 + 45 + 2*4*params.RFpulselength/2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_tse_gs, 'r+')
        lines = f.readlines()
        lines[-140] = 'PR 5, ' + str(4*params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-136] = 'PR 3, ' + str(int(params.GSposttime)) + '\t// Slice rephaser length\n'
        lines[-133] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 4*params.flippulselength/2 - 400 - params.GSposttime - 200 - 200 - params.crushertime - 200 - 45 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-130] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-125] = 'PR 5, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-121] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-118] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 40 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-115] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-112] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-106] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-103] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 55 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-100] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-95] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-91] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-88] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 50 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-85] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-79] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-73] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-70] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 50 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-67] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-62] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-58] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-55] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 50 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-52] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-46] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-40] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-37] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - params.TS * 1000 / 2 - 400 - params.GROpretime - 200 - 200 - params.crushertime - 200 - 50 - 2*4*params.RFpulselength/2)) + '\t// Pause\n'
        lines[-34] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-29] = 'PR 6, ' + str(2*4*params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-25] = 'PR 4, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TE / 2 * 1000 - 2*4*params.RFpulselength/2 - 200 - params.crushertime - 200 - 55 - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-19] = 'PR 4, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_tse_gs, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_tse_gs
        
        print("2D TSE (slice select) setup complete!")
        
    def Image_EPI_setup(self):
        if int(params.TE * 1000 - params.flippulselength / 2 - 200 - 600 - 200 - 170 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200) < 0:
            params.TE = (params.flippulselength / 2 + 200 + 600 + 200 + 70 + 200 + params.GROpretime + 400 + params.TS * 1000 + 400 + params.TS * 1000 + 200) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_epi, 'r+')
        lines = f.readlines()
        lines[-35] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(600) + '\t// Phase length\n'
        lines[-28] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength / 2 - 200 - 600 - 200 - 70 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200)) + '\t// Pause\n'
        lines[-25] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-19] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-16] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_epi, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_epi
        
        print("2D EPI setup complete!")
        
    def Image_EPI_SE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 -200) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 60 + 200 + params.GROpretime + 400 + params.TS * 1000 + 400 + params.TS * 1000 + 200) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_epi_se, 'r+')
        lines = f.readlines()
        lines[-51] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-49] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - 600 - 200 - 200 - params.crushertime - 200 - 50 - params.RFpulselength)) + '\t// Pause\n'
        lines[-46] = 'PR 3, ' + str(600) + '\t// Phase length\n'
        lines[-40] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-35] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-28] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 60 - 200 - params.GROpretime - 400 - params.TS * 1000 - 400 - params.TS * 1000 - 200)) + '\t// Pause\n'
        lines[-25] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-22] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-19] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-16] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_epi_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_epi_se
        
        print("2D EPI SE setup complete!")
        
    def Image_SE_Diff_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 80 - 800 - 2 * params.diffusiontime - 200 - params.GROpretime - 400 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 80 + 800 + 2 * params.diffusiontime + 200 + params.GROpretime + 400 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_se_diff, 'r+')
        lines = f.readlines()
        lines[-54] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-52] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 10 - 800 - 2 * params.diffusiontime - 200 - params.crushertime - 200 - 50 - params.RFpulselength)) + '\t// Pause\n'
        lines[-49] = 'PR 3, ' + str(int(params.diffusiontime)) + '\t// Diff length\n'
        lines[-46] = 'PR 3, ' + str(int(params.diffusiontime)) + '\t// Diff length\n'
        lines[-40] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-35] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-31] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-25] = 'PR 3, ' + str(int(params.diffusiontime)) + '\t// Diff length\n'
        lines[-22] = 'PR 3, ' + str(int(params.diffusiontime)) + '\t// Diff length\n'
        lines[-19] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 80 - 800 - 2 * params.diffusiontime - 200 - params.GROpretime - 400 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROpretime)) + '\t// Readout prephaser length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_se_diff, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_se_diff
        
        print("2D Diffusion (SE) setup complete!")
        
        #2D Flow Compensated Gradient Echo Sequence   
    def Image_FC_GRE_setup(self):
        if int(params.TE * 1000 - params.flippulselength / 2 - 10 - 200 - params.GROfcpretime1 - 400 - params.GROfcpretime2 - 400 - 35 - params.TS * 1000 / 2) < 0:
            params.TE = (params.flippulselength / 2 + 10 + 200 + params.GROfcpretime1 + 400 + params.GROfcpretime2 + 400 + 35 + params.TS * 1000 / 2) / 1000
            print('TE to short!! TE set to:', params.TE, 'ms')
        
        f = open(self.seq_2D_fc_gre, 'r+')
        lines = f.readlines()
        lines[-27] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-25] = 'PR 3, ' + str(int(params.TE * 1000 - params.flippulselength / 2 - 10 - 200 - params.GROfcpretime1 - 400 - params.GROfcpretime2 - 400 - 35 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-22] = 'PR 3, ' + str(int(params.GROfcpretime1)) + '\t// Readout FC prephaser 1 length\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROfcpretime2)) + '\t// Readout FC prephaser 2 length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_fc_gre, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_fc_gre
        
        print("2D FC GRE setup complete!")
        
    # 2D Flow Compensated Spin Echo Sequence
    def Image_FC_SE_setup(self):
        if int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 200 - params.GROfcpretime1 - 400 - params.GROfcpretime2 - 400 - 55 - params.TS * 1000 / 2) < 0:
            params.TE = (params.RFpulselength + 200 + params.crushertime + 200 + 200 + params.GROfcpretime1 + 400 + params.GROfcpretime2 + 400 + 55 + params.TS * 1000 / 2) / 1000 * 2
            print('TE to short!! TE set to:', params.TE, 'ms')
            
        f = open(self.seq_2D_fc_se, 'r+')
        lines = f.readlines()
        lines[-42] = 'PR 5, ' + str(params.flippulselength) + '\t// Flip RF Pulse\n'
        lines[-40] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.flippulselength/2 - 200 - params.crushertime - 200 - 30 - params.RFpulselength)) + '\t// Pause\n'
        lines[-37] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-32] = 'PR 5, ' + str(2 * params.RFpulselength) + '\t// 180deg RF Pulse\n'
        lines[-28] = 'PR 3, ' + str(int(params.crushertime)) + '\t// Crusher length\n'
        lines[-25] = 'PR 3, ' + str(int(params.TE / 2 * 1000 - params.RFpulselength - 200 - params.crushertime - 200 - 200 - params.GROfcpretime1 - 400 - params.GROfcpretime2 - 400 - 55 - params.TS * 1000 / 2)) + '\t// Pause\n'
        lines[-22] = 'PR 3, ' + str(int(params.GROfcpretime1)) + '\t// Readout FC prephaser 1 length\n'
        lines[-16] = 'PR 3, ' + str(int(params.GROfcpretime2)) + '\t// Readout FC prephaser 2 length\n'
        lines[-13] = 'PR 4, ' + str(int(params.TS*1000)) + '\t// Sampling window\n'
        lines[-7] = 'PR 4, ' + str(int(params.spoilertime)) + '\t// Spoiler length\n'
        f.close()
        with open(self.seq_2D_fc_se, "w") as out_file:
            for line in lines:
                out_file.write(line)
                
        params.sequencefile = self.seq_2D_fc_se
        
        print("2D FC SE setup complete!")
        
    def Sequence_upload(self):
        self.assembler = Assembler()
        byte_array = self.assembler.assemble(params.sequencefile)
        
        time.sleep(0.1)
        
        socket.write(struct.pack('<IIIIIIIIII', 4, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        socket.write(byte_array)

        while(True):
            if not socket.waitForBytesWritten():
                break

        socket.setReadBufferSize(8*params.samples)
        
        print("Sequence uploaded!")

    def acquire_spectrum_FID(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 14, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, 0, params.spoileramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_SE(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 15, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, 0, params.spoileramplitude << 16 | params.crusheramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_EPI(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.EPIdelay = int((params.TS + 0.41) * 250)
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,4*self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 25, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GROamplitude, params.spoileramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,0:self.data_idx] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            self.spectrumdata[n,self.data_idx:2*self.data_idx] = self.data[self.data_idx+self.sampledelay+self.EPIdelay:self.sampledelay+self.EPIdelay:-1]*1200
            self.spectrumdata[n,2*self.data_idx:3*self.data_idx] = self.data[self.sampledelay+2*self.EPIdelay:self.data_idx+self.sampledelay+2*self.EPIdelay]*1200
            self.spectrumdata[n,3*self.data_idx:4*self.data_idx] = self.data[self.data_idx+self.sampledelay+3*self.EPIdelay:self.sampledelay+3*self.EPIdelay:-1]*1200
            
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, 4*params.TS, 4*self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,4*self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((4*self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_EPI_SE(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.EPIdelay = int((params.TS + 0.41) * 250)
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,4*self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 26, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GROamplitude, params.spoileramplitude << 16| params.crusheramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,0:self.data_idx] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            self.spectrumdata[n,self.data_idx:2*self.data_idx] = self.data[self.data_idx+self.sampledelay+self.EPIdelay:self.sampledelay+self.EPIdelay:-1]*1200
            self.spectrumdata[n,2*self.data_idx:3*self.data_idx] = self.data[self.sampledelay+2*self.EPIdelay:self.data_idx+self.sampledelay+2*self.EPIdelay]*1200
            self.spectrumdata[n,3*self.data_idx:4*self.data_idx] = self.data[self.data_idx+self.sampledelay+3*self.EPIdelay:self.sampledelay+3*self.EPIdelay:-1]*1200
           
            
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, 4*params.TS, 4*self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,4*self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((4*self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_TSE(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.TEdelay = int(params.TE * 250)
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,4*self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 15, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, 0, params.spoileramplitude << 16 | params.crusheramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,0:self.data_idx] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            self.spectrumdata[n,self.data_idx:2*self.data_idx] = -self.data[self.sampledelay+self.TEdelay:self.data_idx+self.sampledelay+self.TEdelay]*1200
            self.spectrumdata[n,2*self.data_idx:3*self.data_idx] = self.data[self.sampledelay+2*self.TEdelay:self.data_idx+self.sampledelay+2*self.TEdelay]*1200
            self.spectrumdata[n,3*self.data_idx:4*self.data_idx] = -self.data[self.sampledelay+3*self.TEdelay:self.data_idx+self.sampledelay+3*self.TEdelay]*1200
            
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, 4*params.TS, 4*self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,4*self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((4*self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_FID_Gs(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 18, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GSamplitude, params.spoileramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_SE_Gs(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 19, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GSamplitude, params.spoileramplitude << 16 | params.crusheramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_SIR_SE_Gs(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 27, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GSamplitude, params.spoileramplitude << 16 | params.crusheramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_EPI_Gs(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.EPIdelay = int((params.TS + 0.41) * 250)
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,4*self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 28, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GROamplitude << 16 | params.GSamplitude, params.spoileramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,0:self.data_idx] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            self.spectrumdata[n,self.data_idx:2*self.data_idx] = self.data[self.data_idx+self.sampledelay+self.EPIdelay:self.sampledelay+self.EPIdelay:-1]*1200
            self.spectrumdata[n,2*self.data_idx:3*self.data_idx] = self.data[self.sampledelay+2*self.EPIdelay:self.data_idx+self.sampledelay+2*self.EPIdelay]*1200
            self.spectrumdata[n,3*self.data_idx:4*self.data_idx] = self.data[self.data_idx+self.sampledelay+3*self.EPIdelay:self.sampledelay+3*self.EPIdelay:-1]*1200
            
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, 4*params.TS, 4*self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,4*self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((4*self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_EPI_SE_Gs(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.EPIdelay = int((params.TS + 0.41) * 250)
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,4*self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 29, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GROamplitude << 16 | params.GSamplitude, params.spoileramplitude << 16 | params.crusheramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,0:self.data_idx] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            self.spectrumdata[n,self.data_idx:2*self.data_idx] = self.data[self.data_idx+self.sampledelay+self.EPIdelay:self.sampledelay+self.EPIdelay:-1]*1200
            self.spectrumdata[n,2*self.data_idx:3*self.data_idx] = self.data[self.sampledelay+2*self.EPIdelay:self.data_idx+self.sampledelay+2*self.EPIdelay]*1200
            self.spectrumdata[n,3*self.data_idx:4*self.data_idx] = self.data[self.data_idx+self.sampledelay+3*self.EPIdelay:self.sampledelay+3*self.EPIdelay:-1]*1200
            
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, 4*params.TS, 4*self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,4*self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((4*self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_spectrum_TSE_Gs(self):
        print("Acquire spectrum...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.TEdelay = int(params.TE * 250)
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,4*self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 19, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.GSamplitude, params.spoileramplitude << 16 | params.crusheramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,0:self.data_idx] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            self.spectrumdata[n,self.data_idx:2*self.data_idx] = -self.data[self.sampledelay+self.TEdelay:self.data_idx+self.sampledelay+self.TEdelay]*1200
            self.spectrumdata[n,2*self.data_idx:3*self.data_idx] = self.data[self.sampledelay+2*self.TEdelay:self.data_idx+self.sampledelay+2*self.TEdelay]*1200
            self.spectrumdata[n,3*self.data_idx:4*self.data_idx] = -self.data[self.sampledelay+3*self.TEdelay:self.data_idx+self.sampledelay+3*self.TEdelay]*1200
            
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, 4*params.TS, 4*self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,4*self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((4*self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Spectrum acquired!")
        
    def acquire_rf_test(self):
        print("Run RF test sequence...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 20, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, 0, 0))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("RF test sequence finished!")
        
    def acquire_grad_test(self):
        print("Run gradient test sequence...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', 33, 0, 0, 0, 0, 0, 0, 0, 0, params.spoileramplitude))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Gradient test sequence finished!")
        
        
  
    def acquire_projection_GRE(self):
        print("Acquire projection(s)...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.ax = 3
        
        for m in range(params.projaxis.shape[0]):
            if params.projaxis[m] == 1:
                self.ax = m
            else:
                self.ax = 3
            
            if self.ax == 3:
                print('Projection Axis: -')
                if os.path.isfile(params.datapath + '_' + str(m) + '.txt') == True:
                    os.remove(params.datapath + '_' + str(m) + '.txt')

            if self.ax != 3:
                if self.ax == 0: print('Projection Axis: X')
                if self.ax == 1: print('Projection Axis: Y')
                if self.ax == 2: print('Projection Axis: Z')
                
                if params.average == 0: self.avecount = 1
                else: self.avecount = params.averagecount
        
                self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
                for n in range(self.avecount):
                    print('Average: ',n+1,'/',self.avecount)
        
                    socket.write(struct.pack('<IIIIIIIIII', self.ax << 16 | 16, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.spoileramplitude << 16, params.Gproj[self.ax]))

                    while(True):
                        if not socket.waitForBytesWritten(): break
                        time.sleep(0.0001)
            
                    while True:
                        socket.waitForReadyRead()
                        datasize = socket.bytesAvailable()
                        time.sleep(0.0001)
                        if datasize == 8*params.samples:
                            print("Readout finished : ", int(datasize/8), "Samples")
                            self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                            break
                        else: continue
        
                    self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
                    if params.average == 1:
                        time.sleep(params.TR/1000)
            
                params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
                self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
                self.datatxt1[0,:] = params.timeaxis[:]
                self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
                self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
                self.datatxt2 = np.transpose(self.datatxt1)
                np.savetxt(params.datapath + '_' + str(m) + '.txt', self.datatxt2)
            
                time.sleep(params.TR/1000)
            
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Projection(s) acquired!")
        
    def acquire_projection_SE(self):
        print("Acquire projection(s)...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.ax = 3
        
        for m in range(params.projaxis.shape[0]):
            if params.projaxis[m] == 1:
                self.ax = m
            else:
                self.ax = 3
            
            if self.ax == 3:
                print('Projection Axis: -')
                if os.path.isfile(params.datapath + '_' + str(m) + '.txt') == True:
                    os.remove(params.datapath + '_' + str(m) + '.txt')

            if self.ax != 3:
                if self.ax == 0: print('Projection Axis: X')
                if self.ax == 1: print('Projection Axis: Y')
                if self.ax == 2: print('Projection Axis: Z')
                
                if params.average == 0: self.avecount = 1
                else: self.avecount = params.averagecount
        
                self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
                for n in range(self.avecount):
                    print('Average: ',n+1,'/',self.avecount)
        
                    socket.write(struct.pack('<IIIIIIIIII', self.ax << 16 | 17, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.spoileramplitude << 16 | params.crusheramplitude, params.Gproj[self.ax]))

                    while(True):
                        if not socket.waitForBytesWritten(): break
                        time.sleep(0.0001)
            
                    while True:
                        socket.waitForReadyRead()
                        datasize = socket.bytesAvailable()
                        time.sleep(0.0001)
                        if datasize == 8*params.samples:
                            print("Readout finished : ", int(datasize/8), "Samples")
                            self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                            break
                        else: continue
        
                    self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
                    if params.average == 1:
                        time.sleep(params.TR/1000)
            
                params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
                self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
                self.datatxt1[0,:] = params.timeaxis[:]
                self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
                self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
                self.datatxt2 = np.transpose(self.datatxt1)
                np.savetxt(params.datapath + '_' + str(m) + '.txt', self.datatxt2)
            
                time.sleep(params.TR/1000)
            
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Projection(s) acquired!")
        
    def acquire_projection_GRE_angle(self):
        print("Acquire projection...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.ax = 3
        
        if params.imageorientation == 0:
            self.GRO1 = params.Gproj[0]
            self.GRO2 = params.Gproj[1]
            print('Image plane: XY, Angle: ' + str(params.projectionangle) + '°')
        elif params.imageorientation == 1:
            self.GRO1 = params.Gproj[1]
            self.GRO2 = params.Gproj[2]
            print('Image plane: YZ, Angle: ' + str(params.projectionangle) + '°')
        elif params.imageorientation == 2:
            self.GRO1 = params.Gproj[2]
            self.GRO2 = params.Gproj[0]
            print('Image plane: ZX, Angle: ' + str(params.projectionangle) + '°')
                
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 31, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.spoileramplitude << 16 | params.projectionangleradmod100, self.GRO2 << 16 | self.GRO1))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
            
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Projection acquired!")
        
    def acquire_projection_SE_angle(self):
        print("Acquire projection...")
        
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.ax = 3
        
        if params.imageorientation == 0:
            self.GRO1 = params.Gproj[0]
            self.GRO2 = params.Gproj[1]
            print('Image plane: XY, Angle: ' + str(params.projectionangle) + '°')
        elif params.imageorientation == 1:
            self.GRO1 = params.Gproj[1]
            self.GRO2 = params.Gproj[2]
            print('Image plane: YZ, Angle: ' + str(params.projectionangle) + '°')
        elif params.imageorientation == 2:
            self.GRO1 = params.Gproj[2]
            self.GRO2 = params.Gproj[0]
            print('Image plane: ZX, Angle: ' + str(params.projectionangle) + '°')
                
        if params.average == 0: self.avecount = 1
        else: self.avecount = params.averagecount
        
        self.spectrumdata = np.matrix(np.zeros((self.avecount,self.data_idx), dtype = np.complex64))
        
        for n in range(self.avecount):
            print('Average: ',n+1,'/',self.avecount)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 30, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, params.projectionangleradmod100, params.spoileramplitude << 16 | params.crusheramplitude, self.GRO2 << 16 | self.GRO1))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
        
            self.spectrumdata[n,:] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
            if params.average == 1:
                time.sleep(params.TR/1000)
            
        params.timeaxis = np.linspace(0, params.TS, self.data_idx)
        
        self.datatxt1 = np.matrix(np.zeros((self.avecount+1,self.data_idx), dtype = np.complex64))
        self.datatxt1[0,:] = params.timeaxis[:]
        self.datatxt1[1:self.avecount+1,:] = self.spectrumdata[:,:]
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,self.avecount+1), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
            
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Projection acquired!")
        
    def acquire_image_GRE(self):
        print("Acquire image...")

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 8, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16, params.GPEstep, params.GROamplitude << 16 | params.nPE, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(params.nPE):
            print(n+1,'/',params.nPE)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[n, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]    
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_SE(self):
        print("Acquire image...")

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 9, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16 | params.crusheramplitude, params.GPEstep, params.GROamplitude << 16 | params.nPE, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(params.nPE):
            print(n+1,'/',params.nPE)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[n, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]    
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_GRE_Gs(self):
        print("Acquire image...")

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 10, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16, params.GSamplitude << 16 | params.GPEstep, params.GROamplitude << 16 | params.nPE, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(params.nPE):
            print(n+1,'/',params.nPE)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[n, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]    
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_SE_Gs(self):
        print("Acquire image...")

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 11, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16 | params.crusheramplitude, params.GSamplitude << 16 | params.GPEstep, params.GROamplitude << 16 | params.nPE, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(params.nPE):
            print(n+1,'/',params.nPE)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[n, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]    
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_3D_SE_Gs(self):
        print("Acquire image...") 

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.array(np.zeros((params.SPEsteps, params.nPE, self.data_idx), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 12, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, params.spoileramplitude << 16 | params.crusheramplitude, params.SPEsteps << 16 | params.GSPEstep, params.GSamplitude << 16 | params.GPEstep, params.GROamplitude << 16 | params.nPE, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
                
        for m in range(params.SPEsteps):    
            for n in range(params.nPE):
                print(n+1+m*params.nPE,'/',params.nPE*params.SPEsteps)
                while True:
                    socket.waitForReadyRead()
                    datasize = socket.bytesAvailable()
                    time.sleep(0.0001)
                    if datasize == 8*params.samples:
                        print("Readout finished : ",int(datasize/8), "Samples")
                        self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                        break
                    else: continue
                self.kspace[m,n, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]    
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.array(np.zeros((params.SPEsteps, params.nPE, self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx, params.nPE * params.SPEsteps), dtype = np.complex64))
        for m in range(params.SPEsteps):
            self.datatxt2[:,m*params.nPE:m*params.nPE+params.nPE] = np.transpose(self.datatxt1[m,:,:])
        np.savetxt(params.datapath + '_3D_' + str(params.SPEsteps) + '.txt', self.datatxt2)
        
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_3D_TSE_Gs(self):
        print("Acquire image...")
        
        self.nsteps = int(params.nPE / 4)
        print(self.nsteps)

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.TEdelay = int(params.TE * 250)
        
        self.kspacetemp = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
        self.kspace = np.array(np.zeros((params.SPEsteps, params.nPE, self.data_idx), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 32, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, params.SPEsteps << 16 | params.GSPEstep, params.spoileramplitude << 16 | params.crusheramplitude, params.GSamplitude << 16 | params.GPEstep, params.GROamplitude << 16 | self.nsteps, params.TR))         

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
                
        for m in range(params.SPEsteps):    
            for n in range(self.nsteps):
                print(n+1+m*self.nsteps,'/',self.nsteps*params.SPEsteps)
                while True:
                    socket.waitForReadyRead()
                    datasize = socket.bytesAvailable()
                    time.sleep(0.0001)
                    if datasize == 8*params.samples:
                        print("Readout finished : ",int(datasize/8), "Samples")
                        self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                        break
                    else: continue
                self.kspacetemp[n, :] = self.data[self.sampledelay:self.data_idx+self.sampledelay]
                self.kspacetemp[n+self.nsteps, :] = -self.data[self.sampledelay+self.TEdelay:self.data_idx+self.sampledelay+self.TEdelay]
                self.kspacetemp[n+2*self.nsteps, :] = self.data[self.sampledelay+2*self.TEdelay:self.data_idx+self.sampledelay+2*self.TEdelay]
                self.kspacetemp[n+3*self.nsteps, :] = -self.data[self.sampledelay+3*self.TEdelay:self.data_idx+self.sampledelay+3*self.TEdelay]
            
            self.kspace[m,0:int(self.nsteps/2), :] = self.kspacetemp[int(3*self.nsteps):int(3*self.nsteps+self.nsteps/2), :]
            self.kspace[m,int(self.nsteps/2):int(self.nsteps), :] = self.kspacetemp[int(2*self.nsteps):int(2*self.nsteps+self.nsteps/2), :]
            self.kspace[m,int(self.nsteps):int(self.nsteps+self.nsteps/2), :] = self.kspacetemp[int(self.nsteps):int(self.nsteps+self.nsteps/2), :]
            self.kspace[m,int(self.nsteps+self.nsteps/2):int(2*self.nsteps+self.nsteps/2), :] = self.kspacetemp[0:self.nsteps, :]
            self.kspace[m,int(2*self.nsteps+self.nsteps/2):int(3*self.nsteps), :] = self.kspacetemp[int(self.nsteps+self.nsteps/2):int(2*self.nsteps), :]
            self.kspace[m,int(3*self.nsteps):int(3*self.nsteps+self.nsteps/2), :] = self.kspacetemp[int(2*self.nsteps+self.nsteps/2):int(3*self.nsteps), :]
            self.kspace[m,int(3*self.nsteps+self.nsteps/2):int(4*self.nsteps), :] = self.kspacetemp[int(3*self.nsteps+self.nsteps/2):int(4*self.nsteps), :]
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.array(np.zeros((params.SPEsteps, params.nPE, self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx, params.nPE * params.SPEsteps), dtype = np.complex64))
        for m in range(params.SPEsteps):
            self.datatxt2[:,m*params.nPE:m*params.nPE+params.nPE] = np.transpose(self.datatxt1[m,:,:])
        np.savetxt(params.datapath + '_3D_' + str(params.SPEsteps) + '.txt', self.datatxt2)
        
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_TSE(self):
        print("Acquire image...")

        self.nsteps = int(params.nPE / 4)
        print(self.nsteps)
            
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.TEdelay = int(params.TE * 250)
        
        self.kspacetemp = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
#         self.kspace2 = np.matrix(np.zeros((self.nsteps, 10000), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 21, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16 | params.crusheramplitude, params.GPEstep, params.GROamplitude << 16 | self.nsteps, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(self.nsteps):
            print(n+1,'/',self.nsteps)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspacetemp[n, :] = self.data[self.sampledelay:self.data_idx+self.sampledelay]
            self.kspacetemp[n+self.nsteps, :] = -self.data[self.sampledelay+self.TEdelay:self.data_idx+self.sampledelay+self.TEdelay]
            self.kspacetemp[n+2*self.nsteps, :] = self.data[self.sampledelay+2*self.TEdelay:self.data_idx+self.sampledelay+2*self.TEdelay]
            self.kspacetemp[n+3*self.nsteps, :] = -self.data[self.sampledelay+3*self.TEdelay:self.data_idx+self.sampledelay+3*self.TEdelay]
                
#             self.kspace2[n, :] = self.data[0:10000]  
            
        self.kspace[0:int(self.nsteps/2), :] = self.kspacetemp[int(3*self.nsteps):int(3*self.nsteps+self.nsteps/2), :]
        self.kspace[int(self.nsteps/2):int(self.nsteps), :] = self.kspacetemp[int(2*self.nsteps):int(2*self.nsteps+self.nsteps/2), :]
        self.kspace[int(self.nsteps):int(self.nsteps+self.nsteps/2), :] = self.kspacetemp[int(self.nsteps):int(self.nsteps+self.nsteps/2), :]
        self.kspace[int(self.nsteps+self.nsteps/2):int(2*self.nsteps+self.nsteps/2), :] = self.kspacetemp[0:self.nsteps, :]
        self.kspace[int(2*self.nsteps+self.nsteps/2):int(3*self.nsteps), :] = self.kspacetemp[int(self.nsteps+self.nsteps/2):int(2*self.nsteps), :]
        self.kspace[int(3*self.nsteps):int(3*self.nsteps+self.nsteps/2), :] = self.kspacetemp[int(2*self.nsteps+self.nsteps/2):int(3*self.nsteps), :]
        self.kspace[int(3*self.nsteps+self.nsteps/2):int(4*self.nsteps), :] = self.kspacetemp[int(3*self.nsteps+self.nsteps/2):int(4*self.nsteps), :]
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
            
#         self.datatxt1 = np.matrix(np.zeros((params.nPE,10000), dtype = np.complex64))
#         self.datatxt1 = self.kspace2
#         self.datatxt2 = np.matrix(np.zeros((10000,params.nPE), dtype = np.complex64))
#         self.datatxt2 = np.transpose(self.datatxt1)
#         np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        print("Image acquired!")
        
    def acquire_image_TSE_Gs(self):
        print("Acquire image...")

        self.nsteps = int(params.nPE / 4)
        print(self.nsteps)
            
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.TEdelay = int(params.TE * 250)
        
        self.kspacetemp = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
#         self.kspace2 = np.matrix(np.zeros((self.nsteps, 10000), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 23, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16 | params.crusheramplitude, params.GSamplitude << 16 | params.GPEstep, params.GROamplitude << 16 | self.nsteps, params.TR))         

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(self.nsteps):
            print(n+1,'/',self.nsteps)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspacetemp[n, :] = self.data[self.sampledelay:self.data_idx+self.sampledelay]
            self.kspacetemp[n+self.nsteps, :] = -self.data[self.sampledelay+self.TEdelay:self.data_idx+self.sampledelay+self.TEdelay]
            self.kspacetemp[n+2*self.nsteps, :] = self.data[self.sampledelay+2*self.TEdelay:self.data_idx+self.sampledelay+2*self.TEdelay]
            self.kspacetemp[n+3*self.nsteps, :] = -self.data[self.sampledelay+3*self.TEdelay:self.data_idx+self.sampledelay+3*self.TEdelay]
                
#             self.kspace2[n, :] = self.data[0:10000]  
            
        self.kspace[0:int(self.nsteps/2), :] = self.kspacetemp[int(3*self.nsteps):int(3*self.nsteps+self.nsteps/2), :]
        self.kspace[int(self.nsteps/2):int(self.nsteps), :] = self.kspacetemp[int(2*self.nsteps):int(2*self.nsteps+self.nsteps/2), :]
        self.kspace[int(self.nsteps):int(self.nsteps+self.nsteps/2), :] = self.kspacetemp[int(self.nsteps):int(self.nsteps+self.nsteps/2), :]
        self.kspace[int(self.nsteps+self.nsteps/2):int(2*self.nsteps+self.nsteps/2), :] = self.kspacetemp[0:self.nsteps, :]
        self.kspace[int(2*self.nsteps+self.nsteps/2):int(3*self.nsteps), :] = self.kspacetemp[int(self.nsteps+self.nsteps/2):int(2*self.nsteps), :]
        self.kspace[int(3*self.nsteps):int(3*self.nsteps+self.nsteps/2), :] = self.kspacetemp[int(2*self.nsteps+self.nsteps/2):int(3*self.nsteps), :]
        self.kspace[int(3*self.nsteps+self.nsteps/2):int(4*self.nsteps), :] = self.kspacetemp[int(3*self.nsteps+self.nsteps/2):int(4*self.nsteps), :]
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
            
#         self.datatxt1 = np.matrix(np.zeros((params.nPE,10000), dtype = np.complex64))
#         self.datatxt1 = self.kspace2
#         self.datatxt2 = np.matrix(np.zeros((10000,params.nPE), dtype = np.complex64))
#         self.datatxt2 = np.transpose(self.datatxt1)
#         np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        print("Image acquired!")
        
    def acquire_image_EPI(self):
        print("Acquire image...")
            
        self.nsteps = int(params.nPE / 4)
        #print(self.nsteps)
            
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int((params.sampledelay) * 250) #Filterdelay 350µs
        print("sampledelay", self.sampledelay)
        self.sampledelay2 = int((params.sampledelay + params.TS + 0.4 + 0.04) * 250)
        print("sampledelay2", self.sampledelay2)
        self.sampledelay3 = int((params.sampledelay + 2 * params.TS + 0.8) * 250)
        print("sampledelay3", self.sampledelay3)
        self.sampledelay4 = int((params.sampledelay + 3 * params.TS + 1.2 + 0.08) * 250)
        print("sampledelay4", self.sampledelay4)
        
        #self.kspacetemp = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
        self.kspace2 = np.matrix(np.zeros((self.nsteps, 10000), dtype = np.complex64))
        

            
            #socket.write(struct.pack('<IIIIIIIIII', 6, 0, 0, 0, 0, params.Gdiffamplitude, 1 << 16, params.GSamplitude << 16 | params.GPEstep, params.GROamplitude << 16 | self.nsteps, params.TR))
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 24, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16, params.GPEstep, params.GROamplitude << 16 | self.nsteps, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(self.nsteps):
            print(n+1,'/',self.nsteps)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[n*4, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]
            self.kspace[n*4+1, :] = -self.data[self.data_idx + self.sampledelay2 : self.sampledelay2 : -1]
            self.kspace[n*4+2, :] = self.data[self.sampledelay3 : self.data_idx + self.sampledelay3]
            self.kspace[n*4+3, :] = -self.data[self.data_idx + self.sampledelay4 : self.sampledelay4 : -1]
                
            self.kspace2[n, :] = self.data[0:10000]  

        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
            
#         self.datatxt1 = np.matrix(np.zeros((params.nPE,10000), dtype = np.complex64))
#         self.datatxt1 = self.kspace2
#         self.datatxt2 = np.matrix(np.zeros((10000,params.nPE), dtype = np.complex64))
#         self.datatxt2 = np.transpose(self.datatxt1)
#         np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_EPI_SE(self):
        print("Acquire image...")
            
        self.nsteps = int(params.nPE / 4)
        #print(self.nsteps)
            
        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int((params.sampledelay) * 250) #Filterdelay 350µs
        self.EPIdelay = int((params.TS + 0.41) * 250)
        
#         self.kspacetemp = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
        self.kspace = np.matrix(np.zeros((params.nPE, self.data_idx), dtype = np.complex64))
#         self.kspace2 = np.matrix(np.zeros((self.nsteps, 10000), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 22, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, params.spoileramplitude << 16 | params.crusheramplitude, params.GPEstep, params.GROamplitude << 16 | self.nsteps, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(self.nsteps):
            print(n+1,'/',self.nsteps)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[n*4, :] = self.data[self.sampledelay:self.data_idx+self.sampledelay]
            self.kspace[n*4+1, :] = self.data[self.data_idx+self.sampledelay+self.EPIdelay:self.sampledelay+self.EPIdelay:-1]
            self.kspace[n*4+2, :] = self.data[self.sampledelay+2*self.EPIdelay:self.data_idx+self.sampledelay+2*self.EPIdelay]
            self.kspace[n*4+3, :] = self.data[self.data_idx+self.sampledelay+3*self.EPIdelay:self.sampledelay+3*self.EPIdelay:-1]
            
#             self.spectrumdata[n,0:self.data_idx] = self.data[self.sampledelay:self.data_idx+self.sampledelay]*1200
#             self.spectrumdata[n,self.data_idx:2*self.data_idx] = self.data[self.data_idx+self.sampledelay+self.EPIdelay:self.sampledelay+self.EPIdelay:-1]*1200
#             self.spectrumdata[n,2*self.data_idx:3*self.data_idx] = self.data[self.sampledelay+2*self.EPIdelay:self.data_idx+self.sampledelay+2*self.EPIdelay]*1200
#             self.spectrumdata[n,3*self.data_idx:4*self.data_idx] = self.data[self.data_idx+self.sampledelay+3*self.EPIdelay:self.sampledelay+3*self.EPIdelay:-1]*1200
                
#             self.kspace2[n, :] = self.data[0:10000]  

        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
            
#         self.datatxt1 = np.matrix(np.zeros((params.nPE,10000), dtype = np.complex64))
#         self.datatxt1 = self.kspace2
#         self.datatxt2 = np.matrix(np.zeros((10000,params.nPE), dtype = np.complex64))
#         self.datatxt2 = np.transpose(self.datatxt1)
#         np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_SE_Diff(self):
        print("Acquire image...")

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.matrix(np.zeros((2*params.nPE, self.data_idx), dtype = np.complex64))
            
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 13, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, params.spoileramplitude << 16 | params.crusheramplitude, 0, params.GPEstep, params.GROamplitude << 16 | params.nPE, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(params.nPE):
            print(n+1,'/',params.nPE*2)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[n, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]
                
        socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 13, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100,params.spoileramplitude << 16 | params.crusheramplitude, params.Gdiffamplitude, params.GPEstep, params.GROamplitude << 16 | params.nPE, params.TR))

        while(True):
            if not socket.waitForBytesWritten(): break
            time.sleep(0.0001)
        for n in range(params.nPE):
            print(n+1+params.nPE,'/',params.nPE*2)
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ",int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
            self.kspace[params.nPE+n, :] = self.data[self.sampledelay : self.data_idx + self.sampledelay]  
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_radial_GRE(self):
        print("Acquire image...")

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.matrix(np.zeros((self.data_idx, self.data_idx), dtype = np.complex64))
        self.radialangles = np.arange(0, 180, params.radialanglestep)
        
        if params.imageorientation == 0:
            self.GRO1 = params.Gproj[0]
            self.GRO2 = params.Gproj[1]
        elif params.imageorientation == 1:
            self.GRO1 = params.Gproj[1]
            self.GRO2 = params.Gproj[2]
        elif params.imageorientation == 2:
            self.GRO1 = params.Gproj[2]
            self.GRO2 = params.Gproj[0]
        
        self.radialanglecount = self.radialangles.shape[0]

        for n in range(self.radialanglecount):
            print(n+1,'/',self.radialanglecount)
            self.radialangleradmod100 = int((math.radians(self.radialangles[n]) % (2*np.pi))*100)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 31, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, 0, params.spoileramplitude << 16 | self.radialangleradmod100, self.GRO2 << 16 | self.GRO1))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
                
            for n in range(self.data_idx):
                self.kspace[int(self.data_idx/2 + math.sin(self.radialangleradmod100/100)*(n-self.data_idx/2)), int(self.data_idx/2 + math.cos(self.radialangleradmod100/100)*(n-self.data_idx/2))] = self.data[self.sampledelay+n]
            
            time.sleep(params.TR/1000)
        
   
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
    def acquire_image_radial_SE(self):
        print("Acquire image...")

        self.data_idx = int(params.TS * 250) #250 Samples/ms
        self.sampledelay = int(params.sampledelay * 250) #Filterdelay 350µs
        self.kspace = np.matrix(np.zeros((self.data_idx, self.data_idx), dtype = np.complex64))
        self.radialangles = np.arange(0, 180, params.radialanglestep)

        if params.imageorientation == 0:
            self.GRO1 = params.Gproj[0]
            self.GRO2 = params.Gproj[1]
        elif params.imageorientation == 1:
            self.GRO1 = params.Gproj[1]
            self.GRO2 = params.Gproj[2]
        elif params.imageorientation == 2:
            self.GRO1 = params.Gproj[2]
            self.GRO2 = params.Gproj[0]
        
        self.radialanglecount = self.radialangles.shape[0]
        
        for n in range(self.radialanglecount):
            print(n+1,'/',self.radialanglecount)
            self.radialangleradmod100 = int((math.radians(self.radialangles[n]) % (2*np.pi))*100)
        
            socket.write(struct.pack('<IIIIIIIIII', params.imageorientation << 16 | 30, params.flippulseamplitude, params.flippulselength << 16 | params.RFpulselength, params.frequencyoffset, params.frequencyoffsetsign << 16 | params.phaseoffsetradmod100, 0, 0, self.radialangleradmod100, params.spoileramplitude << 16 | params.crusheramplitude, self.GRO2 << 16 | self.GRO1))

            while(True):
                if not socket.waitForBytesWritten(): break
                time.sleep(0.0001)
            
            while True:
                socket.waitForReadyRead()
                datasize = socket.bytesAvailable()
                time.sleep(0.0001)
                if datasize == 8*params.samples:
                    print("Readout finished : ", int(datasize/8), "Samples")
                    self.buffer[0:8*params.samples] = socket.read(8*params.samples)
                    break
                else: continue
                
            for n in range(self.data_idx):
                self.kspace[int(self.data_idx/2 + math.sin(self.radialangleradmod100/100)*(n-self.data_idx/2)), int(self.data_idx/2 + math.cos(self.radialangleradmod100/100)*(n-self.data_idx/2))] = self.data[self.sampledelay+n]
            
            time.sleep(params.TR/1000)
        
   
            
        params.kspace = self.kspace
        
        self.datatxt1 = np.matrix(np.zeros((params.nPE,self.data_idx), dtype = np.complex64))
        self.datatxt1 = params.kspace
        self.datatxt2 = np.matrix(np.zeros((self.data_idx,params.nPE), dtype = np.complex64))
        self.datatxt2 = np.transpose(self.datatxt1)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%m/%d/%Y, %H:%M:%S')
        
        print("Image acquired!")
        
        


seq = sequence()
