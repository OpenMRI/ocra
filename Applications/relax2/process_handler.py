################################################################################
#
# Author: Marcus Prier
# Date: 2025
#
################################################################################

import sys
import struct
import time
import os
import shutil

from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

import numpy as np
import math
import json
import matplotlib.pyplot as plt

from scipy.stats import linregress

from TCPsocket import socket, connected, unconnected
from sequence_handler import seq
from parameter_handler import params


class process:
    def __init__(self):

        params.loadParam()
        params.loadData()

    def motor_move(self, motor=None):
        if motor is not None and params.motor_actual_position != params.motor_goto_position:                     
            print('Moving...')
            cmd_movement_s = 'G0 ' + str(params.motor_goto_position) + '\r\n'
            motor.write(cmd_movement_s.encode('utf-8'))

            time.sleep(0.1)
            
            cmd_response_s = 'M118 R0: movement finished\r\n'
            motor.write(cmd_response_s.encode('utf-8'))
            
            response = motor.readline()
            while 'R0: movement finished' not in response.decode('utf8', errors='ignore'):
                response = motor.readline()
            
            params.motor_actual_position = params.motor_goto_position
            print('Moved to ' + str(params.motor_actual_position) + 'mm')
            
    def recalc_gradients(self):
        self.Delta_vpp = params.frequencyrange / (250 * params.TS)
        self.vpp = self.Delta_vpp * params.nPE
        self.receiverBW = self.vpp / 2
        
        if params.imageorientation == 0:
            self.Gxsens = params.gradsens[0]
            self.Gysens = params.gradsens[1]
            self.Gzsens = params.gradsens[2]
        elif params.imageorientation == 1:
            self.Gxsens = params.gradsens[1]
            self.Gysens = params.gradsens[2]
            self.Gzsens = params.gradsens[0]
        elif params.imageorientation == 2:
            self.Gxsens = params.gradsens[2]
            self.Gysens = params.gradsens[0]
            self.Gzsens = params.gradsens[1]
        elif params.imageorientation == 3:
            self.Gxsens = params.gradsens[1]
            self.Gysens = params.gradsens[0]
            self.Gzsens = params.gradsens[2]
        elif params.imageorientation == 4:
            self.Gxsens = params.gradsens[2]
            self.Gysens = params.gradsens[1]
            self.Gzsens = params.gradsens[0]
        elif params.imageorientation == 5:
            self.Gxsens = params.gradsens[0]
            self.Gysens = params.gradsens[2]
            self.Gzsens = params.gradsens[1]

        self.Gx = (4 * np.pi * self.receiverBW) / (2 * np.pi * 42.57 * params.FOV)
        params.GROamplitude = int(self.Gx / self.Gxsens * 1000)
        
        params.Gproj[0] = int(self.Gx / params.gradsens[0] * 1000)
        params.Gproj[1] = int(self.Gx / params.gradsens[1] * 1000)
        params.Gproj[2] = int(self.Gx / params.gradsens[2] * 1000)

        if params.GROamplitude == 0:
            params.GROpretime = 0
            self.GROfcpretime1 = 0
            self.GROfcpretime2 = 0
        else:
            params.GROpretime = int((params.TS * 1000 / 2 * params.GROamplitude + 200 * params.GROamplitude / 2 - 200 * 2 * params.GROamplitude) / (2 * params.GROamplitude) * params.GROpretimescaler)
            params.GROfcpretime1 = int((((200 * params.GROamplitude + params.TS * 1000 * params.GROamplitude) / 2) - 200 * params.GROamplitude) / params.GROamplitude)
            params.GROfcpretime2 = int(((200 * params.GROamplitude + params.TS * 1000 * params.GROamplitude) - 200 * 2 * params.GROamplitude) / (2 * params.GROamplitude) * params.GROpretimescaler)

        self.GPEtime = params.GROpretime + 200
        self.Gystep = (2 * np.pi / params.FOV) / (2 * np.pi * 42.57 * (self.GPEtime / 1000000))
        params.GPEstep = int(self.Gystep / self.Gysens * 1000)

        self.Achrusher = (4 * np.pi) / (2 * np.pi * 42.57 * params.slicethickness)
        self.Gc = self.Achrusher / ((params.crushertime + 200) / 1000000)
        params.crusheramplitude = int(self.Gc / self.Gzsens * 1000)

        self.Aspoiler = (4 * np.pi) / (2 * np.pi * 42.57 * params.slicethickness)
        self.Gs = self.Aspoiler / ((params.spoilertime + 200) / 1000000)
        params.spoileramplitude = int(self.Gs / self.Gzsens * 1000)

        self.Deltaf = 1 / (params.flippulselength) * 1000000

        self.Gz = (2 * np.pi * self.Deltaf) / (2 * np.pi * 42.57 * (params.slicethickness))
        params.GSamplitude = int(self.Gz / self.Gzsens * 1000)

        self.Gz3D = (2 * np.pi / params.slicethickness) / (2 * np.pi * 42.57 * (self.GPEtime / 1000000))
        params.GSPEstep = int(self.Gz3D / self.Gzsens * 1000)
        
        params.saveFileParameter()

    def spectrum_process(self):
        self.procdata = np.genfromtxt(params.datapath + '.txt', dtype=np.complex64)
        self.procdata = np.transpose(self.procdata)
        params.timeaxis = np.real(self.procdata[0, :])
        params.spectrumdata = self.procdata[1:self.procdata.shape[0], :]

        self.data_idx = params.spectrumdata.shape[1]

        params.mag = np.mean(np.abs(params.spectrumdata), axis=0)
        params.real = np.mean(np.real(params.spectrumdata), axis=0)
        params.imag = np.mean(np.imag(params.spectrumdata), axis=0)

        params.freqencyaxis = np.linspace(-params.frequencyrange / 2, params.frequencyrange / 2, self.data_idx)

        print(params.spectrumdata.shape)
        
        self.fft = np.matrix(np.zeros((params.spectrumdata.shape[0], params.spectrumdata.shape[1]), dtype=np.complex64))
        
        for m in range(params.spectrumdata.shape[0]):
            self.fft[m, :] = np.fft.fftshift(np.fft.fft(np.fft.fftshift(params.spectrumdata[m, :]), n=self.data_idx, norm='ortho'))
        
        if params.average_complex == 1: params.spectrumfft = np.transpose(abs(np.mean(self.fft, axis=0)))
        else: params.spectrumfft = np.transpose(np.mean(abs(self.fft), axis=0))

        print('Spectrum data processed!')

    def image_process(self):
        # Load kspace from file
        self.procdata = np.genfromtxt(params.datapath + '.txt', dtype=np.complex64)
        params.kspace = np.transpose(self.procdata)

        self.kspace_centerx = int(params.kspace.shape[1] / 2)
        self.kspace_centery = int(params.kspace.shape[0] / 2)

        print('k-Space shape: ', params.kspace.shape)

        # Undersampling (Option)
        if params.ustime == 1:
            if params.usmethode == 1:
                for n in range(params.kspace.shape[1]):
                    if n % params.ustimeidx != 0:
                        params.kspace[:, n] = 0
            else:
                m = 0
                for n in range(params.kspace.shape[1]):
                    if m < params.ustimeidx:
                        m = m + 1
                    elif m >= params.ustimeidx and m < 2*params.ustimeidx:
                        params.kspace[:, n] = 0
                        m = m + 1
                    else: m = 1

        if params.usphase == 1:
            if params.usmethode == 1:
                for n in range(params.kspace.shape[0]):
                    if n % params.usphaseidx != 0:
                        params.kspace[n, :] = 0
            else:
                m = 0
                for n in range(params.kspace.shape[0]):
                    if m < params.usphaseidx:
                        m = m + 1
                    elif m >= params.usphaseidx and m < 2*params.usphaseidx:
                        params.kspace[n, :] = 0
                        m = m + 1
                    else: m = 1

        if params.cutcirc == 1:
            # Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) <= self.cutc:
                            params.kspace[jj, ii] = 0

            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) >= self.cuto:
                            params.kspace[jj, ii] = 0

        if params.cutrec == 1:
            # Set kSpace to 0 (Option)
            self.cutcx = int(params.kspace.shape[1] / 2 * params.cutcentervalue / 100)
            self.cutcy = int(params.kspace.shape[0] / 2 * params.cutcentervalue / 100)
            self.cutox = int(params.kspace.shape[1] / 2 * params.cutoutsidevalue / 100)
            self.cutoy = int(params.kspace.shape[0] / 2 * params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                params.kspace[self.kspace_centery - self.cutcy:self.kspace_centery + self.cutcy, self.kspace_centerx - self.cutcx:self.kspace_centerx + self.cutcx] = 0

            if params.cutoutside == 1:
                params.kspace[0:self.cutoy, :] = 0
                params.kspace[params.kspace.shape[0] - self.cutoy:params.kspace.shape[0], :] = 0
                params.kspace[:, 0:self.cutox] = 0
                params.kspace[:, params.kspace.shape[1] - self.cutox:params.kspace.shape[1]] = 0

        # Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)

        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full

        params.img = I[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]
        params.img_mag = self.img_mag_full[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]
        params.img_pha = self.img_pha_full[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]

        print('Image data processed!')

    def image_3D_process(self):
        # Load kspace from file
        self.procdata = np.genfromtxt(params.datapath + '.txt', dtype=np.complex64)
        self.kspace_temp = np.transpose(self.procdata)

        params.kspace = np.array(np.zeros((params.SPEsteps, int(self.kspace_temp.shape[0] / params.SPEsteps), int(self.kspace_temp.shape[1])), dtype=np.complex64))

        for n in range(params.SPEsteps):
            self.kspace_temp2 = self.kspace_temp[int(n * self.kspace_temp.shape[0] / params.SPEsteps):int(n * self.kspace_temp.shape[0] / params.SPEsteps + self.kspace_temp.shape[0] / params.SPEsteps), :]

            params.kspace[n, 0:int(self.kspace_temp.shape[0] / params.SPEsteps), :] = self.kspace_temp[int(n * self.kspace_temp.shape[0] / params.SPEsteps):int(n * self.kspace_temp.shape[0] / params.SPEsteps + int(self.kspace_temp.shape[0] / params.SPEsteps)), :]

        self.kspace_centerx = int(params.kspace.shape[2] / 2)
        self.kspace_centery = int(params.kspace.shape[1] / 2)
        self.kspace_centerz = int(params.kspace.shape[0] / 2)

        # Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fftn(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)

        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full

        params.img = I[:, :, self.kspace_centerx - int(params.kspace.shape[1] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[1] / 2 * params.ROBWscaler)]
        params.img_mag = self.img_mag_full[:, :, self.kspace_centerx - int(params.kspace.shape[1] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[1] / 2 * params.ROBWscaler)]
        params.img_pha = self.img_pha_full[:, :, self.kspace_centerx - int(params.kspace.shape[1] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[1] / 2 * params.ROBWscaler)]  # print(params.img_mag.shape)

        print('3D Image data processed!')

    def image_diff_process(self):
        # Load kspace from file
        self.procdata_temp = np.genfromtxt(params.datapath + '.txt', dtype=np.complex64)
        self.procdata = self.procdata_temp[:, 0:int(self.procdata_temp.shape[1] / 2)]
        params.kspace = np.transpose(self.procdata)

        self.kspace_centerx = int(params.kspace.shape[1] / 2)
        self.kspace_centery = int(params.kspace.shape[0] / 2)

        # Undersampling (Option)
        if params.ustime == 1:
            if params.usmethode == 1:
                for n in range(params.kspace.shape[1]):
                    if n % params.ustimeidx != 0:
                        params.kspace[:, n] = 0
            else:
                m = 0
                for n in range(params.kspace.shape[1]):
                    if m < params.ustimeidx:
                        m = m + 1
                    elif m >= params.ustimeidx and m < 2*params.ustimeidx:
                        params.kspace[:, n] = 0
                        m = m + 1
                    else: m = 1

        if params.usphase == 1:
            if params.usmethode == 1:
                for n in range(params.kspace.shape[0]):
                    if n % params.usphaseidx != 0:
                        params.kspace[n, :] = 0
            else:
                m = 0
                for n in range(params.kspace.shape[0]):
                    if m < params.usphaseidx:
                        m = m + 1
                    elif m >= params.usphaseidx and m < 2*params.usphaseidx:
                        params.kspace[n, :] = 0
                        m = m + 1
                    else: m = 1

        if params.cutcirc == 1:
            # Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) <= self.cutc:
                            params.kspace[jj, ii] = 0

            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) >= self.cuto:
                            params.kspace[jj, ii] = 0

        if params.cutrec == 1:
            # Set kSpace to 0 (Option)
            self.cutcx = int(params.kspace.shape[1] / 2 * params.cutcentervalue / 100)
            self.cutcy = int(params.kspace.shape[0] / 2 * params.cutcentervalue / 100)
            self.cutox = int(params.kspace.shape[1] / 2 * params.cutoutsidevalue / 100)
            self.cutoy = int(params.kspace.shape[0] / 2 * params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                params.kspace[self.kspace_centery - self.cutcy:self.kspace_centery + self.cutcy, self.kspace_centerx - self.cutcx:self.kspace_centerx + self.cutcx] = 0

            if params.cutoutside == 1:
                params.kspace[0:self.cutoy, :] = 0
                params.kspace[params.kspace.shape[0] - self.cutoy:params.kspace.shape[0], :] = 0
                params.kspace[:, 0:self.cutox] = 0
                params.kspace[:, params.kspace.shape[1] - self.cutox:params.kspace.shape[1]] = 0

        # Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)

        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full

        params.img = I[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]
        params.img_mag = self.img_mag_full[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]
        params.img_pha = self.img_pha_full[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]

        # Load diff kspace from file
        self.procdata_temp = np.genfromtxt(params.datapath + '.txt', dtype=np.complex64)
        self.procdata = self.procdata_temp[:, int(self.procdata_temp.shape[1] / 2):int(self.procdata_temp.shape[1])]
        self.kspacediff = np.transpose(self.procdata)
        print(self.kspacediff.shape)

        # Undersampling (Option)
        if params.ustime == 1:
            if params.usmethode == 1:
                for n in range(params.kspace.shape[1]):
                    if n % params.ustimeidx != 0:
                        params.kspace[:, n] = 0
            else:
                m = 0
                for n in range(params.kspace.shape[1]):
                    if m < params.ustimeidx:
                        m = m + 1
                    elif m >= params.ustimeidx and m < 2*params.ustimeidx:
                        params.kspace[:, n] = 0
                        m = m + 1
                    else: m = 1

        if params.usphase == 1:
            if params.usmethode == 1:
                for n in range(params.kspace.shape[0]):
                    if n % params.usphaseidx != 0:
                        params.kspace[n, :] = 0
            else:
                m = 0
                for n in range(params.kspace.shape[0]):
                    if m < params.usphaseidx:
                        m = m + 1
                    elif m >= params.usphaseidx and m < 2*params.usphaseidx:
                        params.kspace[n, :] = 0
                        m = m + 1
                    else: m = 1

        if params.cutcirc == 1:
            # Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) <= self.cutc:
                            params.kspace[jj, ii] = 0

            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) >= self.cuto:
                            params.kspace[jj, ii] = 0

        if params.cutrec == 1:
            # Set kSpace to 0 (Option)
            self.cutcx = int(params.kspace.shape[1] / 2 * params.cutcentervalue / 100)
            self.cutcy = int(params.kspace.shape[0] / 2 * params.cutcentervalue / 100)
            self.cutox = int(params.kspace.shape[1] / 2 * params.cutoutsidevalue / 100)
            self.cutoy = int(params.kspace.shape[0] / 2 * params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                params.kspace[self.kspace_centery - self.cutcy:self.kspace_centery + self.cutcy, self.kspace_centerx - self.cutcx:self.kspace_centerx + self.cutcx] = 0

            if params.cutoutside == 1:
                params.kspace[0:self.cutoy, :] = 0
                params.kspace[params.kspace.shape[0] - self.cutoy:params.kspace.shape[0], :] = 0
                params.kspace[:, 0:self.cutox] = 0
                params.kspace[:, params.kspace.shape[1] - self.cutox:params.kspace.shape[1]] = 0

        # Image calculations
        self.k_amp_full = np.abs(self.kspacediff)
        self.k_pha_full = np.angle(self.kspacediff)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspacediff)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)

        self.k_ampdiff = self.k_amp_full
        self.k_phadiff = self.k_pha_full

        self.img_magdiff = self.img_mag_full[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]
        self.img_phadiff = self.img_pha_full[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]

        params.img_mag_diff = params.img_mag - self.img_magdiff
        #params.B1alphamapmasked = np.matrix(np.zeros((params.B1alphamap.shape[1], params.B1alphamap.shape[0])))
        #params.B1alphamapmasked[:, :] = params.B1alphamap[:, :]
        self.img_max = np.max(np.amax(params.img_mag))
        params.img_mag_diff[params.img_mag < self.img_max * params.signalmask] = np.nan

        print('Diffusion Image data processed!')

    def radial_process(self):
        # Load kspace from file
        self.procdata = np.genfromtxt(params.datapath + '.txt', dtype=np.complex64)
        params.kspace = np.transpose(self.procdata)

        self.kspace_centerx = int(params.kspace.shape[1] / 2)
        self.kspace_centery = int(params.kspace.shape[0] / 2)

        print('kspace shape', params.kspace.shape)

        # Undersampling (Option)
        if params.ustime == 1:
            for n in range(params.kspace.shape[1]):
                if n % params.ustimeidx != 0:
                    params.kspace[:, n] = 0

        if params.usphase == 1:
            for n in range(params.kspace.shape[0]):
                if n % params.usphaseidx != 0:
                    params.kspace[n, :] = 0

        if params.cutcirc == 1:
            # Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) <= self.cutc:
                            params.kspace[jj, ii] = 0

            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1] / 2)) ** 2 + (jj * params.kspace.shape[1] / params.kspace.shape[0] - (params.kspace.shape[1] / 2)) ** 2) >= self.cuto:
                            params.kspace[jj, ii] = 0

        if params.cutrec == 1:
            # Set kSpace to 0 (Option)
            self.cutcx = int(params.kspace.shape[1] / 2 * params.cutcentervalue / 100)
            self.cutcy = int(params.kspace.shape[0] / 2 * params.cutcentervalue / 100)
            self.cutox = int(params.kspace.shape[1] / 2 * params.cutoutsidevalue / 100)
            self.cutoy = int(params.kspace.shape[0] / 2 * params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                params.kspace[self.kspace_centery - self.cutcy:self.kspace_centery + self.cutcy, self.kspace_centerx - self.cutcx:self.kspace_centerx + self.cutcx] = 0

            if params.cutoutside == 1:
                params.kspace[0:self.cutoy, :] = 0
                params.kspace[params.kspace.shape[0] - self.cutoy:params.kspace.shape[0], :] = 0
                params.kspace[:, 0:self.cutox] = 0
                params.kspace[:, params.kspace.shape[1] - self.cutox:params.kspace.shape[1]] = 0

        # Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)

        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full

        params.img = I[self.kspace_centery - int(params.nPE / 2 * params.ROBWscaler):self.kspace_centery + int(params.nPE / 2 * params.ROBWscaler), self.kspace_centerx - int(params.nPE / 2 * params.ROBWscaler):self.kspace_centerx + int(params.nPE / 2 * params.ROBWscaler)]
        params.img_mag = self.img_mag_full[self.kspace_centery - int(params.nPE / 2 * params.ROBWscaler):self.kspace_centery + int(params.nPE / 2 * params.ROBWscaler), self.kspace_centerx - int(params.nPE / 2 * params.ROBWscaler):self.kspace_centerx + int(params.nPE / 2 * params.ROBWscaler)]  # [:, int(self.kspace_centerx - ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.kspace_centerx + ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.bandwidth / (params.kspace.shape[0]-1))]
        params.img_pha = self.img_pha_full[self.kspace_centery - int(params.nPE / 2 * params.ROBWscaler):self.kspace_centery + int(params.nPE / 2 * params.ROBWscaler), self.kspace_centerx - int(params.nPE / 2 * params.ROBWscaler):self.kspace_centerx + int(params.nPE / 2 * params.ROBWscaler)]  # [:, int(self.kspace_centerx - ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.kspace_centerx + ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.bandwidth / (params.kspace.shape[0]-1))]

        print(params.img_mag.shape)

        print('Image data processed!')

    def image_stitching_2D_GRE(self, motor=None):
        print('Measuring stitched images 2D GRE...')
        
        if os.path.isdir(params.datapath) != True: os.mkdir(params.datapath)
        else:
            shutil.rmtree(params.datapath)
            os.mkdir(params.datapath)
            
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        params.datapath = params.datapath + '/Image_Stitching'
        
        motor_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
        
        self.estimated_time = params.motor_image_count*params.motor_settling_time*1000 + params.motor_image_count*params.nPE*((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        if params.headerfileformat == 0: params.save_header_file_txt()
        else: params.save_header_file_json()
        
        if params.autorecenter == 1:
            params.motor_goto_position = params.motor_AC_position
            self.motor_move(motor=motor)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Settling for Autocenter...')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep(params.motor_settling_time)
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.frequencyoffset = self.frequencyoffset_temp
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            params.motor_current_image_count = 0
            
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                params.motor_current_image_count = n
                                
                if n > 0 and params.motor_AC_inbetween and (n)%params.motor_AC_inbetween_step == 0:
                    params.motor_goto_position = params.motor_AC_position
                    self.motor_move(motor=motor)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Settling for Autocenter...')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep(params.motor_settling_time)
                    self.frequencyoffset_temp = 0
                    self.frequencyoffset_temp = params.frequencyoffset
                    params.frequencyoffset = 0
                    seq.RXconfig_upload()
                    seq.Gradients_upload()
                    seq.Frequency_upload()
                    seq.RFattenuation_upload()
                    seq.FID_setup()
                    seq.Sequence_upload()
                    seq.acquire_spectrum_FID()
                    proc.spectrum_process()
                    proc.spectrum_analytics()
                    params.frequency = params.centerfrequency
                    params.frequencyoffset = self.frequencyoffset_temp
                    params.saveFileParameter()
                    print('Autorecenter to:', params.frequency)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()

                #time.sleep(params.TR / 1000)
        else:
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()
                
        os.remove(self.datapath_temp + '/Image_Stitching.txt')

        params.datapath = self.datapath_temp

        print('Stitched images acquired!')

    def image_stitching_2D_SE(self, motor=None):
        print('Measuring stitched images 2D SE...')
        
        if os.path.isdir(params.datapath) != True: os.mkdir(params.datapath)
        else:
            shutil.rmtree(params.datapath)
            os.mkdir(params.datapath)
            
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        params.datapath = params.datapath + '/Image_Stitching'
        
        motor_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
        
        self.estimated_time = params.motor_image_count*params.motor_settling_time*1000 + params.motor_image_count*params.nPE*((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        if params.headerfileformat == 0: params.save_header_file_txt()
        else: params.save_header_file_json()
                
        if params.autorecenter == 1:
            params.motor_goto_position = params.motor_AC_position
            self.motor_move(motor=motor)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Settling for Autocenter...')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep(params.motor_settling_time)
            
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.frequencyoffset = self.frequencyoffset_temp
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            params.motor_current_image_count = 0
                        
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                params.motor_current_image_count = n
                
                if n > 0 and params.motor_AC_inbetween and (n)%params.motor_AC_inbetween_step == 0:
                    params.motor_goto_position = params.motor_AC_position
                    self.motor_move(motor=motor)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Settling for Autocenter...')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep(params.motor_settling_time)
                    self.frequencyoffset_temp = 0
                    self.frequencyoffset_temp = params.frequencyoffset
                    params.frequencyoffset = 0
                    seq.RXconfig_upload()
                    seq.Gradients_upload()
                    seq.Frequency_upload()
                    seq.RFattenuation_upload()
                    seq.SE_setup()
                    seq.Sequence_upload()
                    seq.acquire_spectrum_SE()
                    proc.spectrum_process()
                    proc.spectrum_analytics()
                    params.frequency = params.centerfrequency
                    params.frequencyoffset = self.frequencyoffset_temp
                    params.saveFileParameter()
                    print('Autorecenter to:', params.frequency)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()
                
        else:
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()

        os.remove(self.datapath_temp + '/Image_Stitching.txt')

        params.datapath = self.datapath_temp

        print('Stitched images acquired!')
        
    def image_stitching_2D_GRE_slice(self, motor=None):
        print('Measuring stitched images 2D GRE slice...')
        
        if os.path.isdir(params.datapath) != True: os.mkdir(params.datapath)
        else:
            shutil.rmtree(params.datapath)
            os.mkdir(params.datapath)
            
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        params.datapath = params.datapath + '/Image_Stitching'

        motor_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
        
        self.estimated_time = params.motor_image_count*params.motor_settling_time*1000 + params.motor_image_count*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        if params.headerfileformat == 0: params.save_header_file_txt()
        else: params.save_header_file_json()
                
        if params.autorecenter == 1:
            params.motor_goto_position = params.motor_AC_position
            self.motor_move(motor=motor)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Settling for Autocenter...')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep(params.motor_settling_time)
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.frequencyoffset = self.frequencyoffset_temp
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            params.motor_current_image_count = 0
            
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                params.motor_current_image_count = n
                
                if n > 0 and params.motor_AC_inbetween and (n)%params.motor_AC_inbetween_step == 0:
                    params.motor_goto_position = params.motor_AC_position
                    self.motor_move(motor=motor)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Settling for Autocenter...')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep(params.motor_settling_time)
                    self.frequencyoffset_temp = 0
                    self.frequencyoffset_temp = params.frequencyoffset
                    params.frequencyoffset = 0
                    seq.RXconfig_upload()
                    seq.Gradients_upload()
                    seq.Frequency_upload()
                    seq.RFattenuation_upload()
                    seq.FID_Gs_setup()
                    seq.Sequence_upload()
                    seq.acquire_spectrum_FID_Gs()
                    proc.spectrum_process()
                    proc.spectrum_analytics()
                    params.frequency = params.centerfrequency
                    params.frequencyoffset = self.frequencyoffset_temp
                    params.saveFileParameter()
                    print('Autorecenter to:', params.frequency)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()

                #time.sleep(params.TR / 1000)
        else:
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()
                
        os.remove(self.datapath_temp + '/Image_Stitching.txt')

        params.datapath = self.datapath_temp

        print('Stitched slice images acquired!')
        
    def image_stitching_2D_SE_slice(self, motor=None):
        print('Measuring stitched images 2D SE slice...')
        
        if os.path.isdir(params.datapath) != True: os.mkdir(params.datapath)
        else:
            shutil.rmtree(params.datapath)
            os.mkdir(params.datapath)
            
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        params.datapath = params.datapath + '/Image_Stitching'

        motor_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)

        self.estimated_time = params.motor_image_count*params.motor_settling_time*1000 + params.motor_image_count*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        if params.headerfileformat == 0: params.save_header_file_txt()
        else: params.save_header_file_json()
                
        if params.autorecenter == 1:
            params.motor_goto_position = params.motor_AC_position
            self.motor_move(motor=motor)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Settling for Autocenter...')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep(params.motor_settling_time)
            
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.frequencyoffset = self.frequencyoffset_temp
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            params.motor_current_image_count = 0
            
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                params.motor_current_image_count = n
                
                if n > 0 and params.motor_AC_inbetween and (n)%params.motor_AC_inbetween_step == 0:
                    params.motor_goto_position = params.motor_AC_position
                    self.motor_move(motor=motor)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Settling for Autocenter...')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep(params.motor_settling_time)
                    self.frequencyoffset_temp = 0
                    self.frequencyoffset_temp = params.frequencyoffset
                    params.frequencyoffset = 0
                    seq.RXconfig_upload()
                    seq.Gradients_upload()
                    seq.Frequency_upload()
                    seq.RFattenuation_upload()
                    seq.SE_Gs_setup()
                    seq.Sequence_upload()
                    seq.acquire_spectrum_SE_Gs()
                    proc.spectrum_process()
                    proc.spectrum_analytics()
                    params.frequency = params.centerfrequency
                    params.frequencyoffset = self.frequencyoffset_temp
                    params.saveFileParameter()
                    print('Autorecenter to:', params.frequency)
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()

                #time.sleep(params.TR / 1000)
        else:
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()

        os.remove(self.datapath_temp + '/Image_Stitching.txt')

        params.datapath = self.datapath_temp

        print('Stitched slice images acquired!')

    def image_stitching_2D_process(self):
        self.datapath_temp = ''
        self.datapath_temp = params.datapath

        if params.imageorientation == 'XY' or params.imageorientation == 'ZY':
            print('Processing XY or ZY')
            self.imagecrop_image_pixel = int((params.nPE * params.motor_movement_step) / params.FOV)
            self.imagecrop_total_pixel = int(self.imagecrop_image_pixel * params.motor_image_count)
            self.imageexp_total_pixel = (self.imagecrop_image_pixel * (params.motor_image_count - 1) + params.nPE)

            if params.motor_movement_step <= params.FOV:
                params.img_st = np.array(np.zeros((self.imagecrop_total_pixel, params.nPE), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((self.imagecrop_total_pixel, params.nPE)))
                params.img_st_pha = np.array(np.zeros((self.imagecrop_total_pixel, params.nPE)))
            else:
                params.img_st = np.array(np.zeros((self.imageexp_total_pixel, params.nPE), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((self.imageexp_total_pixel, params.nPE)))
                params.img_st_pha = np.array(np.zeros((self.imageexp_total_pixel, params.nPE)))

            for n in range(0, params.motor_image_count):
                if params.motor_movement_step > 0:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                else:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(params.motor_image_count - n))

                print(n+1,'/',params.motor_image_count)

                proc.image_process()

                if params.motor_movement_step <= params.FOV:
                    params.img_st[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :] = params.img[int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel), :]
                    params.img_st_mag[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :] = params.img_mag[int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel), :]
                    params.img_st_pha[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :] = params.img_pha[int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel), :]
                else:
                    params.img_st[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE), :] = params.img[:, :]
                    params.img_st_mag[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE), :] = params.img_mag[:, :]
                    params.img_st_pha[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE), :] = params.img_pha[:, :]
        
        elif params.imageorientation == 'YZ' or params.imageorientation == 'YX':
            print('Processing YZ or YX')
            self.imagecrop_image_pixel = int((params.nPE * params.motor_movement_step) / params.FOV)
            self.imagecrop_total_pixel = int(self.imagecrop_image_pixel * params.motor_image_count)
            self.imageexp_total_pixel = (self.imagecrop_image_pixel * (params.motor_image_count - 1) + params.nPE)

            if params.motor_movement_step <= params.FOV:
                params.img_st = np.array(np.zeros((params.nPE, self.imagecrop_total_pixel), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((params.nPE, self.imagecrop_total_pixel)))
                params.img_st_pha = np.array(np.zeros((params.nPE, self.imagecrop_total_pixel)))
            else:
                params.img_st = np.array(np.zeros((params.nPE, self.imageexp_total_pixel), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((params.nPE, self.imageexp_total_pixel)))
                params.img_st_pha = np.array(np.zeros((params.nPE, self.imageexp_total_pixel)))

            for n in range(0, params.motor_image_count):
                if params.motor_movement_step < 0:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                else:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(params.motor_image_count - n))
                
                print(n+1,'/',params.motor_image_count)
                
                proc.image_process()

                if params.motor_movement_step <= params.FOV:
                    params.img_st[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel)] = params.img[:,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel)]
                    params.img_st_mag[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel)] = params.img_mag[:,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel)]
                    params.img_st_pha[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel)] = params.img_pha[:,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel)]
                else:
                    params.img_st[:,int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE)] = params.img[:, :]
                    params.img_st_mag[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE)] = params.img_mag[:, :]
                    params.img_st_pha[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE)] = params.img_pha[:, :]

        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
            print('Processing ZX or XZ')
            params.img_st = np.array(np.zeros((params.nPE, params.motor_image_count * params.nPE), dtype=np.complex64))
            params.img_st_mag = np.array(np.zeros((params.nPE, params.motor_image_count * params.nPE)))
            params.img_st_pha = np.array(np.zeros((params.nPE, params.motor_image_count * params.nPE)))

            for n in range(0, params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                
                print(n+1,'/',params.motor_image_count)
                
                proc.image_process()

                params.img_st[:, n * params.nPE:int(n * params.nPE + params.nPE)] = params.img[:, :]
                params.img_st_mag[:, n * params.nPE:int(n * params.nPE + params.nPE)] = params.img_mag[:, :]
                params.img_st_pha[:, n * params.nPE:int(n * params.nPE + params.nPE)] = params.img_pha[:, :]

        params.datapath = self.datapath_temp

        print('Image stitching data processed!')

    def image_stitching_3D_slab(self, motor=None):
        print('Measuring stitched images 3D SE slab...')
        
        if os.path.isdir(params.datapath) != True: os.mkdir(params.datapath)
        else:
            shutil.rmtree(params.datapath)
            os.mkdir(params.datapath)
            
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        params.datapath = params.datapath + '/Image_Stitching'
        
        motor_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
        
        self.estimated_time = params.motor_image_count*params.motor_settling_time*1000 + params.motor_image_count*params.SPEsteps*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)

        if params.headerfileformat == 0: params.save_header_file_txt()
        else: params.save_header_file_json()
                
        if params.autorecenter == 1:
            params.motor_goto_position = params.motor_AC_position
            self.motor_move(motor=motor)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Settling for Autocenter...')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep(params.motor_settling_time)
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            params.frequencyoffset = self.frequencyoffset_temp
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            params.motor_current_image_count = 0
            
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                params.motor_current_image_count = n
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n*params.motor_settling_time*1000 - n*params.SPEsteps*params.nPE*((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()

                #time.sleep(params.TR / 1000)
        else:
            for n in range(params.motor_image_count):
                params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                
                params.motor_goto_position = motor_positions[n]
                self.motor_move(motor=motor)
                
                print('Position: ', n + 1, '/', params.motor_image_count)
                
                self.remaining_time = (self.estimated_time - n * params.motor_settling_time - n * params.SPEsteps * params.nPE * ((100 + 2*params.flippulselength + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Position: ' + str(n+1) + '/' + str(params.motor_image_count) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's\nSettling...')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.motor_settling_time*1000)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep(params.motor_settling_time)

                seq.sequence_upload()

                if params.headerfileformat == 0: params.save_header_file_txt()
                else: params.save_header_file_json()

        os.remove(self.datapath_temp + '/Image_Stitching.txt')

        params.datapath = self.datapath_temp

        print('Stitched 3D slabs acquired!')

    def image_stitching_3D_process(self):
        self.datapath_temp = ''
        self.datapath_temp = params.datapath

        if params.imageorientation == 'XY' or params.imageorientation == 'ZY':
            self.imagecrop_image_pixel = int((params.nPE * params.motor_movement_step) / params.FOV)
            self.imagecrop_total_pixel = int(self.imagecrop_image_pixel * params.motor_image_count)
            self.imageexp_total_pixel = (self.imagecrop_image_pixel * (params.motor_image_count - 1) + params.nPE)

            if params.motor_movement_step <= params.FOV:

                params.img_st = np.array(np.zeros((params.SPEsteps, self.imagecrop_total_pixel, params.nPE), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((params.SPEsteps, self.imagecrop_total_pixel, params.nPE)))
                params.img_st_pha = np.array(np.zeros((params.SPEsteps, self.imagecrop_total_pixel, params.nPE)))
            else:
                params.img_st = np.array(
                    np.zeros((params.SPEsteps, self.imageexp_total_pixel, params.nPE), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((params.SPEsteps, self.imageexp_total_pixel, params.nPE)))
                params.img_st_pha = np.array(np.zeros((params.SPEsteps, self.imageexp_total_pixel, params.nPE)))

            for n in range(params.motor_image_count):
                if params.motor_movement_step < 0:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                else:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(params.motor_image_count - n))
                
                print(n+1,'/',params.motor_image_count)
                
                proc.image_3D_process()

                if params.motor_movement_step <= params.FOV:
                    params.img_st[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :] = params.img[:,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel),:]
                    params.img_st_mag[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :] = params.img_mag[:,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel),:]
                    params.img_st_pha[:, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :] = params.img_pha[:,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel),:]
                else:
                    params.img_st[:,int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE),:] = params.img[:, :, :]
                    params.img_st_mag[:,int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE),:] = params.img_mag[:, :, :]
                    params.img_st_pha[:,int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE),:] = params.img_pha[:, :, :]

        elif params.imageorientation == 'YZ' or params.imageorientation == 'YX':
            self.imagecrop_image_pixel = int((params.nPE * params.motor_movement_step) / params.FOV)
            self.imagecrop_total_pixel = int(self.imagecrop_image_pixel * params.motor_image_count)
            self.imageexp_total_pixel = (self.imagecrop_image_pixel * (params.motor_image_count - 1) + params.nPE)

            if params.motor_movement_step <= params.FOV:

                params.img_st = np.array(np.zeros((params.SPEsteps, params.nPE, self.imagecrop_total_pixel), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((params.SPEsteps, params.nPE, self.imagecrop_total_pixel)))
                params.img_st_pha = np.array(np.zeros((params.SPEsteps, params.nPE, self.imagecrop_total_pixel)))
            else:
                params.img_st = np.array(
                    np.zeros((params.SPEsteps, params.nPE, self.imageexp_total_pixel), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((params.SPEsteps, params.nPE, self.imageexp_total_pixel)))
                params.img_st_pha = np.array(np.zeros((params.SPEsteps, params.nPE, self.imageexp_total_pixel)))

            for n in range(params.motor_image_count):
                if params.motor_movement_step > 0:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                else:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(params.motor_image_count - n))
                    
                print(n+1,'/',params.motor_image_count)
                
                proc.image_3D_process()

                if params.motor_movement_step <= params.FOV:
                    params.img_st[:, :, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel)] = params.img[:, :,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel)]
                    params.img_st_mag[:, :, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel)] = params.img_mag[:, :,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel)]
                    params.img_st_pha[:, :, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel)] = params.img_pha[:, :,int(params.nPE / 2 - self.imagecrop_image_pixel / 2):int(params.nPE / 2 - self.imagecrop_image_pixel / 2 + self.imagecrop_image_pixel)]
                else:
                    params.img_st[:, :, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE)] = params.img[:, :, :]
                    params.img_st_mag[:, :, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE)] = params.img_mag[:, :, :]
                    params.img_st_pha[:, :, int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.nPE)] = params.img_pha[:, :, :]

        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
            self.imagecrop_image_pixel = int((params.motor_movement_step * params.SPEsteps) / params.slicethickness)
            self.imagecrop_total_pixel = int(self.imagecrop_image_pixel * params.motor_image_count)
            self.imageexp_total_pixel = (self.imagecrop_image_pixel * (params.motor_image_count - 1) + params.SPEsteps)

            if params.motor_movement_step <= params.slicethickness:
                params.img_st = np.array(np.zeros((self.imagecrop_total_pixel, params.nPE, params.nPE), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((self.imagecrop_total_pixel, params.nPE, params.nPE)))
                params.img_st_pha = np.array(np.zeros((self.imagecrop_total_pixel, params.nPE, params.nPE)))
            else:
                params.img_st = np.array(np.zeros((self.imageexp_total_pixel, params.nPE, params.nPE), dtype=np.complex64))
                params.img_st_mag = np.array(np.zeros((self.imageexp_total_pixel, params.nPE, params.nPE)))
                params.img_st_pha = np.array(np.zeros((self.imageexp_total_pixel, params.nPE, params.nPE)))

            for n in range(params.motor_image_count):
                if params.motor_movement_step > 0:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(n + 1))
                else:
                    params.datapath = (self.datapath_temp + '/Image_Stitching_' + str(params.motor_image_count - n))
                
                print(n+1,'/',params.motor_image_count)
                
                proc.image_3D_process()

                if params.motor_movement_step <= params.slicethickness:
                    params.img_st[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :, :] = params.img[int(params.SPEsteps / 2 - self.imagecrop_image_pixel / 2):int(params.SPEsteps / 2 - self.imagecrop_image_pixel / 2) + self.imagecrop_image_pixel,:, :]
                    params.img_st_mag[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :, :] = params.img_mag[int(params.SPEsteps / 2 - self.imagecrop_image_pixel / 2):int(params.SPEsteps / 2 - self.imagecrop_image_pixel / 2) + self.imagecrop_image_pixel,:, :]
                    params.img_st_pha[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + self.imagecrop_image_pixel), :, :] = params.img_pha[int(params.SPEsteps / 2 - self.imagecrop_image_pixel / 2):int(params.SPEsteps / 2 - self.imagecrop_image_pixel / 2) + self.imagecrop_image_pixel,:, :]
                else:
                    params.img_st[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.SPEsteps), :,:] = params.img[:, :, :]
                    params.img_st_mag[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.SPEsteps), :,:] = params.img_mag[:, :, :]
                    params.img_st_pha[int(n * self.imagecrop_image_pixel):int(n * self.imagecrop_image_pixel + params.SPEsteps), :,:] = params.img_pha[:, :, :]

        params.datapath = self.datapath_temp

        print('3D Image stitching data processed!')

    def spectrum_analytics(self):

        params.peakvalue = round(np.max(params.spectrumfft), 3)
        #print('Signal: ', params.peakvalue)
        self.maxindex = np.argmax(params.spectrumfft)
        self.lowerspectum = params.spectrumfft[1:self.maxindex]
        self.upperspectum = params.spectrumfft[self.maxindex + 1:params.spectrumfft.shape[0]]
        self.absinvhalflowerspectum = abs(self.lowerspectum - params.peakvalue / 2)
        self.absinvhalfupperspectum = abs(self.upperspectum - params.peakvalue / 2)

        self.lowerindex = np.argmin(self.absinvhalflowerspectum)
        self.upperindex = np.argmin(self.absinvhalfupperspectum) + self.maxindex

        params.FWHM = int(round((self.upperindex - self.lowerindex) * (params.frequencyrange / params.spectrumfft.shape[0])))

        self.lowerlowerindex = self.maxindex - ((self.maxindex - self.lowerindex) * 5)
        self.upperupperindex = self.maxindex + ((self.upperindex - self.maxindex) * 5)

        self.noisevector = np.concatenate((params.spectrumfft[0:self.lowerlowerindex],params.spectrumfft[self.upperupperindex:params.spectrumfft.shape[0]]))
        params.noise = round(np.mean(self.noisevector), 3)
        #print('Noise: ', params.noise)

        params.SNR = round(params.peakvalue / params.noise, 1)
        if np.isnan(params.SNR) == True:
            params.SNR = 0.001
        #print('SNR: ', params.SNR)

        params.centerfrequency = round(params.frequency + ((self.maxindex - params.spectrumfft.shape[0] / 2) * params.frequencyrange / params.spectrumfft.shape[0]) / 1.0e6, 6)

        params.inhomogeneity = int(round(params.FWHM / params.centerfrequency))

        #print('B0 inhomogeneity: ', params.inhomogeneity, 'ppm')
        print('Data analysed!')

    def image_analytics(self):
        self.img_max = np.max(params.img_mag)

        self.img_phantomcut = np.matrix(np.zeros((params.img_mag.shape[0], params.img_mag.shape[1])))
        self.img_phantomcut[:, :] = params.img_mag[:, :]
        self.img_phantomcut[self.img_phantomcut < self.img_max / 2] = np.nan
        params.peakvalue = round(np.mean(self.img_phantomcut[np.isnan(self.img_phantomcut) == False]), 3)
        #print('Signal: ', params.peakvalue)

        self.img_noisecut = np.matrix(np.zeros((params.img_mag.shape[0], params.img_mag.shape[1])))
        self.img_noisecut[:, :] = params.img_mag[:, :]
        self.img_noisecut[self.img_noisecut >= self.img_max * params.signalmask] = np.nan
        params.noise = round(np.mean(self.img_noisecut[np.isnan(self.img_noisecut) == False]), 3)
        #print('Noise: ', params.noise)

        params.SNR = round(params.peakvalue / params.noise, 1)
        if np.isnan(params.SNR) == True:
            params.SNR = 0.001
        #print('SNR: ', params.SNR)
            
    def image_3D_analytics(self):
        self.img_max = np.max(params.img_mag)

        self.img_phantomcut = np.array(np.zeros((params.img_mag.shape[0], params.img_mag.shape[1], params.img_mag.shape[2])))
        self.img_phantomcut[:, :, :] = params.img_mag[:, :, :]
        self.img_phantomcut[self.img_phantomcut < self.img_max / 2] = np.nan
        params.peakvalue = round(np.mean(self.img_phantomcut[np.isnan(self.img_phantomcut) == False]), 3)
        #print('Signal: ', params.peakvalue)

        self.img_noisecut = np.array(np.zeros((params.img_mag.shape[0], params.img_mag.shape[1], params.img_mag.shape[2])))
        self.img_noisecut[:, :, :] = params.img_mag[:, :, :]
        self.img_noisecut[self.img_noisecut >= self.img_max * params.signalmask] = np.nan
        params.noise = round(np.mean(self.img_noisecut[np.isnan(self.img_noisecut) == False]), 3)
        #print('Noise: ', params.noise)

        params.SNR = round(params.peakvalue / params.noise, 1)
        if np.isnan(params.SNR) == True:
            params.SNR = 0.001
        #print('SNR: ', params.SNR)
            
    def image_stitching_analytics(self):
        self.img_st_max = np.max(params.img_st_mag)

        self.img_st_phantomcut = np.array(np.zeros((params.img_st_mag.shape[0], params.img_st_mag.shape[1])))
        self.img_st_phantomcut[:, :] = params.img_st_mag[:, :]
        self.img_st_phantomcut[self.img_st_phantomcut < self.img_st_max / 2] = np.nan
        params.peakvalue = round(np.mean(self.img_st_phantomcut[np.isnan(self.img_st_phantomcut) == False]), 3)
        #print('Signal: ', params.peakvalue)

        self.img_st_noisecut = np.array(np.zeros((params.img_st_mag.shape[0], params.img_st_mag.shape[1])))
        self.img_st_noisecut[:, :] = params.img_st_mag[:, :]
        self.img_st_noisecut[self.img_st_noisecut >= self.img_st_max * params.signalmask] = np.nan
        params.noise = round(np.mean(self.img_st_noisecut[np.isnan(self.img_st_noisecut) == False]), 3)
        #print('Noise: ', params.noise)

        params.SNR = round(params.peakvalue / params.noise, 1)
        if np.isnan(params.SNR) == True:
            params.SNR = 0.001
        #print('SNR: ', params.SNR)
            
    def image_stitching_3D_analytics(self):
        self.img_st_max = np.max(params.img_st_mag)

        self.img_st_phantomcut = np.array(np.zeros((params.img_st_mag.shape[0], params.img_st_mag.shape[1], params.img_st_mag.shape[2])))
        self.img_st_phantomcut[:, :, :] = params.img_st_mag[:, :, :]
        self.img_st_phantomcut[self.img_st_phantomcut < self.img_st_max / 2] = np.nan
        params.peakvalue = round(np.mean(self.img_st_phantomcut[np.isnan(self.img_st_phantomcut) == False]), 3)
        #print('Signal: ', params.peakvalue)

        self.img_st_noisecut = np.array(np.zeros((params.img_st_mag.shape[0], params.img_st_mag.shape[1], params.img_st_mag.shape[2])))
        self.img_st_noisecut[:, :, :] = params.img_st_mag[:, :, :]
        self.img_st_noisecut[self.img_st_noisecut >= self.img_st_max * params.signalmask] = np.nan
        params.noise = round(np.mean(self.img_st_noisecut[np.isnan(self.img_st_noisecut) == False]), 3)
        #print('Noise: ', params.noise)

        params.SNR = round(params.peakvalue / params.noise, 1)
        if np.isnan(params.SNR) == True:
            params.SNR = 0.001
        #print('SNR: ', params.SNR)
            
    def Autocentertool(self):
        print('Finding signals...')
        
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.GUImode_temp = 0
            self.GUImode_temp = params.GUImode
            self.sequence_temp = 0
            self.sequence_temp = params.sequence
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            
            params.GUImode = 0
            params.sequence = 1
            params.TS = 10
            params.TE = 12
            params.TR = 1000
            params.slicethickness = 15
            params.frequencyoffset = 0
            
            proc.recalc_gradients()
            
        self.freq_temp = 0
        self.freq_temp = params.frequency

        self.ACidx = round(abs((params.ACstop * 1.0e6 - params.ACstart * 1.0e6)) / (params.ACstepwidth)) + 1
        self.ACsteps = np.linspace(params.ACstart, params.ACstop, self.ACidx)
        params.ACvalues = np.matrix(np.zeros((2, self.ACidx)))
        self.ACpeakvalues = np.zeros(self.ACidx)
        
        self.estimated_time = self.ACidx * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)

        for n in range(self.ACidx):
            print(n + 1, '/', self.ACidx)
            self.ACsteps[n] = round(self.ACsteps[n], 6)
            params.frequency = self.ACsteps[n]
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.ACsteps[n] = params.centerfrequency
            self.ACpeakvalues[n] = params.peakvalue
            
            self.remaining_time = (self.estimated_time - n * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
            self.remaining_time_h = math.floor(self.remaining_time / (3600))
            self.remaining_time_min = math.floor(self.remaining_time / 60)
            self.remaining_time_s = int(self.remaining_time % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(self.ACidx) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.ACvalues[0, :] = self.ACsteps
        params.ACvalues[1, :] = self.ACpeakvalues
        params.Reffrequency = self.ACsteps[np.argmax(self.ACpeakvalues)]

        np.savetxt('tooldata/Autocenter_Tool_Data.txt', np.transpose(params.ACvalues))
        
        if params.toolautosequence == 1:
            params.GUImode = self.GUImode_temp
            params.sequence = self.sequence_temp
            params.TS = self.TS_temp
            params.TE = self.TE_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            
            proc.recalc_gradients()

        params.frequency = self.freq_temp
        params.datapath = self.datapath_temp

    def Flipangletool(self):
        print('Finding flipangles...')
        
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.GUImode_temp = 0
            self.GUImode_temp = params.GUImode
            self.sequence_temp = 0
            self.sequence_temp = params.sequence
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            
            params.GUImode = 0
            params.sequence = 1
            params.TS = 10
            params.TE = 12
            params.TR = 1000
            params.slicethickness = 15
            params.frequencyoffset = 0
            
            proc.recalc_gradients()

        self.RFattenuation_temp = 0
        self.RFattenuation_temp = params.RFattenuation

        self.FAsteps = np.linspace(params.FAstart, params.FAstop, params.FAsteps)
        params.FAvalues = np.matrix(np.zeros((2, params.FAsteps)))
        self.FApeakvalues = np.zeros(params.FAsteps)

        params.RFattenuation = -31.75
        seq.sequence_upload()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Reset attenunator')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)
        
        self.estimated_time = params.FAsteps * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)

        for n in range(params.FAsteps):
            print(n + 1, '/', params.FAsteps)
            self.FAsteps[n] = int(self.FAsteps[n] / 0.25) * 0.25
            print(self.FAsteps[n])
            params.RFattenuation = self.FAsteps[n]
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.FApeakvalues[n] = params.peakvalue
            
            self.remaining_time = (self.estimated_time - n * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
            self.remaining_time_h = math.floor(self.remaining_time / (3600))
            self.remaining_time_min = math.floor(self.remaining_time / 60)
            self.remaining_time_s = int(self.remaining_time % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.FAsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.FAvalues[0, :] = self.FAsteps
        params.FAvalues[1, :] = self.FApeakvalues

        params.RefRFattenuation = self.FAsteps[np.argmax(self.FApeakvalues)]

        np.savetxt('tooldata/Flipangle_Tool_Data.txt', np.transpose(params.FAvalues))
        
        if params.toolautosequence == 1:
            params.GUImode = self.GUImode_temp
            params.sequence = self.sequence_temp
            params.TS = self.TS_temp
            params.TE = self.TE_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            
            proc.recalc_gradients()

        params.RFattenuation = self.RFattenuation_temp
        params.datapath = self.datapath_temp

    def Shimtool(self):
        print('Finding shims...')
        
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.GUImode_temp = 0
            self.GUImode_temp = params.GUImode
            self.sequence_temp = 0
            self.sequence_temp = params.sequence
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            
            params.GUImode = 0
            params.sequence = 10
            params.slicethickness = 15
            params.frequencyoffset = 0
            
            if params.ToolAutoShimMode == 0:
                params.TS = 20
                params.TE = 24
                params.TR = 1000
            else:
                params.TS = 30
                params.TE = 33
                params.TR = 4000
                
            proc.recalc_gradients()

        self.frequency_temp = 0
        self.frequency_temp = params.frequency
        self.shim_temp = [0, 0, 0, 0]
        self.shim_temp[:] = params.grad[:]

        self.STsteps = np.linspace(params.ToolShimStart, params.ToolShimStop, params.ToolShimSteps)
        self.STsteps = self.STsteps.astype(int)

        params.STvalues = np.matrix(np.zeros((5, params.ToolShimSteps)))
        params.STvalues[0, :] = self.STsteps

        seq.sequence_upload()
        proc.spectrum_process()
        proc.spectrum_analytics()
        params.frequency = params.centerfrequency
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        if params.ToolShimChannel[0] == 1:
            self.STpeakvaluesX = np.zeros(params.ToolShimSteps)
            params.grad[0] = self.STsteps[0]

            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('X Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            self.estimated_time = params.ToolShimSteps * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)

            for n in range(params.ToolShimSteps):
                print(n + 1, '/', params.ToolShimSteps)
                params.grad[0] = self.STsteps[n]
                params.frequency = params.centerfrequency

                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesX[n] = params.peakvalue
                
                self.remaining_time = (self.estimated_time - n * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
            
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('X Measuring... ' + str(n+1) + '/' + str(params.ToolShimSteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep((params.TR-100)/1000)
                time.sleep(0.1)

            params.STvalues[1, :] = self.STpeakvaluesX

            params.frequency = self.frequency_temp
            params.grad[0] = self.shim_temp[0]

        if params.ToolShimChannel[1] == 1:
            self.STpeakvaluesY = np.zeros(params.ToolShimSteps)
            params.grad[1] = self.STsteps[0]

            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Y Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            self.estimated_time = params.ToolShimSteps * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)

            for n in range(params.ToolShimSteps):
                print(n + 1, '/', params.ToolShimSteps)
                params.grad[1] = self.STsteps[n]
                params.frequency = params.centerfrequency

                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesY[n] = params.peakvalue
                
                self.remaining_time = (self.estimated_time - n * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
            
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Y Measuring... ' + str(n+1) + '/' + str(params.ToolShimSteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep((params.TR-100)/1000)
                time.sleep(0.1)

            params.STvalues[2, :] = self.STpeakvaluesY

            params.frequency = self.frequency_temp
            params.grad[1] = self.shim_temp[1]

        if params.ToolShimChannel[2] == 1:
            self.STpeakvaluesZ = np.zeros(params.ToolShimSteps)
            params.grad[2] = self.STsteps[0]

            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Z Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            self.estimated_time = params.ToolShimSteps * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)

            for n in range(params.ToolShimSteps):
                print(n + 1, '/', params.ToolShimSteps)
                params.frequency = params.centerfrequency
                params.grad[2] = self.STsteps[n]

                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesZ[n] = params.peakvalue
                
                self.remaining_time = (self.estimated_time - n * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
            
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Z Measuring... ' + str(n+1) + '/' + str(params.ToolShimSteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep((params.TR-100)/1000)
                time.sleep(0.1)

            params.STvalues[3, :] = self.STpeakvaluesZ

            params.frequency = self.frequency_temp
            params.grad[2] = self.shim_temp[2]

        if params.ToolShimChannel[3] == 1:
            self.STpeakvaluesZ2 = np.zeros(params.ToolShimSteps)
            params.grad[3] = self.STsteps[0]

            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Z² Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            
            self.estimated_time = params.ToolShimSteps * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)

            for n in range(params.ToolShimSteps):
                print(n + 1, '/', params.ToolShimSteps)
                params.frequency = params.centerfrequency
                params.grad[3] = self.STsteps[n]

                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesZ2[n] = params.peakvalue
                
                self.remaining_time = (self.estimated_time - n * ((100 + params.flippulselength/2 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)) / 1000
                self.remaining_time_h = math.floor(self.remaining_time / (3600))
                self.remaining_time_min = math.floor(self.remaining_time / 60)
                self.remaining_time_s = int(self.remaining_time % 60)
            
                if params.measurement_time_dialog == 1:
                    msg_box = QMessageBox()
                    msg_box.setText('Z² Measuring... ' + str(n+1) + '/' + str(params.ToolShimSteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                    msg_box.button(QMessageBox.Ok).hide()
                    msg_box.exec()
                else: time.sleep((params.TR-100)/1000)
                time.sleep(0.1)

            params.STvalues[4, :] = self.STpeakvaluesZ2

            params.frequency = self.frequency_temp
            params.grad[3] = self.shim_temp[3]
            
        if params.toolautosequence == 1:
            params.GUImode = self.GUImode_temp
            params.sequence = self.sequence_temp
            params.TS = self.TS_temp
            params.TE = self.TE_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            
            proc.recalc_gradients()
            
        params.datapath = self.datapath_temp

        np.savetxt('tooldata/Shim_Tool_Data.txt', np.transpose(params.STvalues))

    def FieldMapB0(self):
        print('Measuring B0 field...')

        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.TE_temp = 0
        self.TE_temp = params.TE
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        
        params.GUImode = 1
        params.sequence = 4
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            self.nPE_temp = 0
            self.nPE_temp = params.nPE
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            params.TS = 4
            params.TE = 4
            params.TR = 6000
            params.slicethickness = 15
            params.frequencyoffset = 0
            params.nPE = 64
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
                    
            proc.recalc_gradients()
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp
        
        params.TE = 2 * params.TE
        params.datapath = 'rawdata/Tool_Image_rawdata'  

        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB0_S2_raw = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S2 = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S2_raw[:, :] = params.img_pha[:, :]
        self.FieldMapB0_S2[:, :] = params.img_pha[:, :]

        for kk in range(20):

            for jj in range(int(self.FieldMapB0_S2.shape[1] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[1] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] - 2 * math.pi

            for jj in range(int(self.FieldMapB0_S2.shape[0] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[0] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] - 2 * math.pi

        time.sleep(params.TR / 1000)
        
        params.TE = self.TE_temp
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp
            
        params.datapath = 'rawdata/Tool_Image_rawdata'

        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB0_S1_raw = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S1 = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S1_raw = params.img_pha
        self.FieldMapB0_S1 = params.img_pha

        for kk in range(20):

            for jj in range(int(self.FieldMapB0_S1.shape[1] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[1] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[0] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[0] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] - 2 * math.pi

        params.B0DeltaB0map = (self.FieldMapB0_S2 - self.FieldMapB0_S1) / (2 * math.pi * 42.577 * ((2 * params.TE - params.TE)) / 1000)
        params.B0DeltaB0mapmasked = np.matrix(np.zeros((params.B0DeltaB0map.shape[1], params.B0DeltaB0map.shape[0])))
        params.B0DeltaB0mapmasked[:, :] = params.B0DeltaB0map[:, :]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B0DeltaB0mapmasked[params.img_mag < self.img_max * params.signalmask] = np.nan

        self.FieldMapB0_pha_raw = np.concatenate((self.FieldMapB0_S1_raw, self.FieldMapB0_S2_raw), axis=0)
        np.savetxt('tooldata/FieldMap_B0_Phase_Raw_Data.txt', self.FieldMapB0_pha_raw)
        self.FieldMapB0_pha = np.concatenate((self.FieldMapB0_S1, self.FieldMapB0_S2), axis=0)
        np.savetxt('tooldata/FieldMap_B0_Phase_Data.txt', self.FieldMapB0_pha)
        self.B0DeltaB0maps = np.concatenate((params.img_mag, params.B0DeltaB0map, params.B0DeltaB0mapmasked), axis=0)
        np.savetxt('tooldata/FieldMap_B0_deltat1ms_Mag_Map_MapMasked_Data.txt', self.B0DeltaB0maps)
        
        if params.toolautosequence == 1:
            params.TS = self.TS_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            params.nPE = self.nPE_temp
            params.FOV = self.FOV_temp
            
            proc.recalc_gradients()

        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.datapath = self.datapath_temp

    def FieldMapB0Slice(self):
        print('Measuring B0 (Slice) field...')

        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.TE_temp = 0
        self.TE_temp = params.TE
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        
        params.GUImode = 1
        params.sequence = 20
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            self.nPE_temp = 0
            self.nPE_temp = params.nPE
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            params.TS = 4
            params.TE = 4
            params.TR = 6000
            params.slicethickness = 4
            params.frequencyoffset = 0
            params.nPE = 64
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
                    
            proc.recalc_gradients()
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp
        
        params.TE = 2 * params.TE
        params.datapath = 'rawdata/Tool_Image_rawdata'

        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB0_S2_raw = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S2 = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S2_raw[:, :] = params.img_pha[:, :]
        self.FieldMapB0_S2[:, :] = params.img_pha[:, :]

        for kk in range(20):

            for jj in range(int(self.FieldMapB0_S2.shape[1] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(elf.FieldMapB0_S2.shape[1] / 2) + jj + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[1] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj - 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[0] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S2.shape[1] / 2) - jj + ii + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[0] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S2.shape[1] / 2) + jj - ii + 1] - 2 * math.pi

        time.sleep(params.TR / 1000)
        
        params.TE = self.TE_temp
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp
            
        params.datapath = 'rawdata/Tool_Image_rawdata'

        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB0_S1_raw = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S1 = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0])))
        self.FieldMapB0_S1_raw = params.img_pha
        self.FieldMapB0_S1 = params.img_pha

        for kk in range(20):

            for jj in range(int(self.FieldMapB0_S1.shape[1] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj + ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[1] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii - 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj - ii + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj - 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[0] / 2) - 2):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) + jj + 1, int(self.FieldMapB0_S1.shape[1] / 2) - jj + ii + 1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[0] / 2) - 1):
                for ii in range(1 + jj * 2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii - 1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0] / 2) - jj - 1, int(self.FieldMapB0_S1.shape[1] / 2) + jj - ii + 1] - 2 * math.pi

        params.B0DeltaB0map = (self.FieldMapB0_S2 - self.FieldMapB0_S1) / (2 * math.pi * 42.577 * ((2 * params.TE - params.TE)) / 1000)
        params.B0DeltaB0mapmasked = np.matrix(np.zeros((params.B0DeltaB0map.shape[1], params.B0DeltaB0map.shape[0])))
        params.B0DeltaB0mapmasked[:, :] = params.B0DeltaB0map[:, :]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B0DeltaB0mapmasked[params.img_mag < self.img_max * params.signalmask] = np.nan

        self.FieldMapB0_pha_raw = np.concatenate((self.FieldMapB0_S1_raw, self.FieldMapB0_S2_raw), axis=1)
        np.savetxt('tooldata/FieldMap_B0_Phase_Raw_Data.txt', self.FieldMapB0_pha_raw)
        self.FieldMapB0_pha = np.concatenate((self.FieldMapB0_S1, self.FieldMapB0_S2), axis=1)
        np.savetxt('tooldata/FieldMap_B0_Phase_Data.txt', self.FieldMapB0_pha)
        self.B0DeltaB0maps = np.concatenate((params.img_mag, params.B0DeltaB0map, params.B0DeltaB0mapmasked), axis=1)
        np.savetxt('tooldata/FieldMap_B0_deltat1ms_Mag_Map_MapMasked_Data.txt', self.B0DeltaB0maps)
        
        if params.toolautosequence == 1:
            params.TS = self.TS_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            params.nPE = self.nPE_temp
            params.FOV = self.FOV_temp
            
            proc.recalc_gradients()

        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.datapath = self.datapath_temp

    def FieldMapB1(self):
        print('Measuring B1 field...')
        
        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.datapath_temp = ''    
        self.datapath_temp = params.datapath
        self.flipangleamplitude_temp = 0
        self.flipangleamplitude_temp = params.flipangleamplitude
        
        params.GUImode = 1
        params.sequence = 4
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            self.nPE_temp = 0
            self.nPE_temp = params.nPE
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            params.flipangleamplitude = 35
            params.TS = 4
            params.TE = 4
            params.TR = 6000
            params.slicethickness = 15
            params.frequencyoffset = 0
            params.nPE = 64
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
                    
            proc.recalc_gradients()
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp
        
        params.datapath = 'rawdata/Tool_Image_rawdata'
            
        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB1_S1 = np.matrix(np.zeros((params.img_mag.shape[1], params.img_mag.shape[0])))
        self.FieldMapB1_S1[:, :] = params.img_mag[:, :]

        time.sleep(params.TR / 1000)
        
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp

        params.flipangleamplitude = params.flipangleamplitude * 2
        params.datapath = 'rawdata/Tool_Image_rawdata'

        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB1_S2 = np.matrix(np.zeros((params.img_mag.shape[1], params.img_mag.shape[0])))
        self.FieldMapB1_S2[:, :] = params.img_mag[:, :]

        params.flipangleamplitude = self.flipangleamplitude_temp

        params.B1alphamap = np.arccos(self.FieldMapB1_S2 / (2 * self.FieldMapB1_S1)) * params.flipangleamplitude
        params.B1alphamapmasked = np.matrix(np.zeros((params.B1alphamap.shape[1], params.B1alphamap.shape[0])))
        params.B1alphamapmasked[:, :] = params.B1alphamap[:, :]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B1alphamapmasked[params.img_mag < self.img_max * params.signalmask] = np.nan

        self.FieldMapB1_mag = np.concatenate((self.FieldMapB1_S1, self.FieldMapB1_S2), axis=1)
        np.savetxt('tooldata/FieldMap_B1_Phase_Data.txt', self.FieldMapB1_mag)
        self.B1alphamaps = np.concatenate((params.img_mag, params.B1alphamap, params.B1alphamapmasked), axis=1)
        np.savetxt('tooldata/FieldMap_B1_alpha' + str(params.flipangleamplitude) + 'deg_Mag_Map_MapMasked_Data.txt', self.B1alphamaps)

        if params.toolautosequence == 1:
            params.TS = self.TS_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            params.nPE = self.nPE_temp
            params.FOV = self.FOV_temp
            
            proc.recalc_gradients()
        
        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.datapath = self.datapath_temp

    def FieldMapB1Slice(self):
        print('Measuring B1 (Slice) field...')

        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.datapath_temp = ''    
        self.datapath_temp = params.datapath
        self.flipangleamplitude_temp = 0
        self.flipangleamplitude_temp = params.flipangleamplitude
        
        params.GUImode = 1
        params.sequence = 20
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            self.nPE_temp = 0
            self.nPE_temp = params.nPE
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            params.flipangleamplitude = 35
            params.TS = 4
            params.TE = 4
            params.TR = 6000
            params.slicethickness = 4
            params.frequencyoffset = 0
            params.nPE = 64
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
                    
            proc.recalc_gradients()
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp

        params.datapath = 'rawdata/Tool_Image_rawdata'

        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB1_S1 = np.matrix(np.zeros((params.img_mag.shape[1], params.img_mag.shape[0])))
        self.FieldMapB1_S1[:, :] = params.img_mag[:, :]

        time.sleep(params.TR / 1000)
        
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp

        params.flipangleamplitude = params.flipangleamplitude * 2
        params.datapath = 'rawdata/Tool_Image_rawdata'

        seq.sequence_upload()
        proc.image_process()
        
        params.flipangleamplitude = self.flipangleamplitude_temp

        self.FieldMapB1_S2 = np.matrix(np.zeros((params.img_mag.shape[1], params.img_mag.shape[0])))
        self.FieldMapB1_S2[:, :] = params.img_mag[:, :]

        params.B1alphamap = np.arccos(self.FieldMapB1_S2 / (2 * self.FieldMapB1_S1)) * params.flipangleamplitude
        params.B1alphamapmasked = np.matrix(np.zeros((params.B1alphamap.shape[1], params.B1alphamap.shape[0])))
        params.B1alphamapmasked[:, :] = params.B1alphamap[:, :]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B1alphamapmasked[params.img_mag < self.img_max * params.signalmask] = np.nan

        self.FieldMapB1_mag = np.concatenate((self.FieldMapB1_S1, self.FieldMapB1_S2), axis=1)
        np.savetxt('tooldata/FieldMap_B1_Phase_Data.txt', self.FieldMapB1_mag)
        self.B1alphamaps = np.concatenate((params.img_mag, params.B1alphamap, params.B1alphamapmasked), axis=1)
        np.savetxt('tooldata/FieldMap_B1_alpha' + str(params.flipangleamplitude) + 'deg_Mag_Map_MapMasked_Data.txt', self.B1alphamaps)

        if params.toolautosequence == 1:
            params.TS = self.TS_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            params.nPE = self.nPE_temp
            params.FOV = self.FOV_temp
            
            proc.recalc_gradients()

        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.datapath = self.datapath_temp

    def FieldMapGradient(self):
        print('Gradient tool started...')

        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        
        params.GUImode = 1
        params.sequence = 5
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            self.nPE_temp = 0
            self.nPE_temp = params.nPE
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            params.TS = 4
            params.TE = 12
            params.TR = 2000
            params.slicethickness = 15
            params.frequencyoffset = 0
            params.nPE = 64
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
                    
            proc.recalc_gradients()
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to :', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp
        
        params.datapath = 'rawdata/Tool_Image_rawdata'
                    
        seq.sequence_upload()    
        proc.image_process()
        
        if params.toolautosequence == 1:
            params.TS = self.TS_temp
            params.TE = self.TE_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            params.nPE = self.nPE_temp
            params.FOV = self.FOV_temp
            
            proc.recalc_gradients()

        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.datapath = self.datapath_temp

    def FieldMapGradientSlice(self):
        print('Gradient (Slice) tool started...')

        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.datapath_temp = ''
        self.datapath_temp = params.datapath
        
        params.GUImode = 1
        params.sequence = 21
        params.datapath = 'rawdata/Tool_Spectrum_rawdata'
        
        if params.toolautosequence == 1:
            self.TS_temp = 0
            self.TS_temp = params.TS
            self.TE_temp = 0
            self.TE_temp = params.TE
            self.TR_temp = 0
            self.TR_temp = params.TR
            self.slicethickness_temp = 0
            self.slicethickness_temp = params.slicethickness
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            self.nPE_temp = 0
            self.nPE_temp = params.nPE
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            params.TS = 4
            params.TE = 12
            params.TR = 4000
            params.slicethickness = 4
            params.frequencyoffset = 0
            params.nPE = 64
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
                    
            proc.recalc_gradients()
        
        if params.autorecenter == 1:
            self.frequencyoffset_temp = 0
            self.frequencyoffset_temp = params.frequencyoffset
            params.frequencyoffset = 0
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            params.frequencyoffset = self.frequencyoffset_temp

        params.datapath = 'rawdata/Tool_Image_rawdata'

        seq.sequence_upload()
        proc.image_process()
        
        if params.toolautosequence == 1:
            params.TS = self.TS_temp
            params.TE = self.TE_temp
            params.TR = self.TR_temp
            params.slicethickness = self.slicethickness_temp
            params.frequencyoffset = self.frequencyoffset_temp
            params.nPE = self.nPE_temp
            params.FOV = self.FOV_temp
            
            proc.recalc_gradients()

        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.datapath = self.datapath_temp

    def T1measurement_IR_FID(self):
        print('Measuring T1 (FID)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1values = np.matrix(np.zeros((2, params.TIsteps)))
        self.T1peakvalues = np.zeros(params.TIsteps)
        
        self.estimated_time = 0
        for n in range(params.TIsteps):
            self.estimated_time = self.estimated_time + ((100 + params.flippulselength + self.T1steps[n]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            
        self.T1steps[0] = round(self.T1steps[0], 1)
        params.TI = self.T1steps[0]
        seq.IR_FID_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_FID()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TIsteps):
            print(n + 1, '/', params.TIsteps)
            self.T1steps[n] = round(self.T1steps[n], 1)
            params.TI = self.T1steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.IR_FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T1peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + params.flippulselength + self.T1steps[m]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TIsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.T1values[0, :] = self.T1steps
        params.T1values[1, :] = self.T1peakvalues

        params.TI = self.TI_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TIsteps, 2)))
        self.datatxt1 = np.transpose(params.T1values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T1 (FID) Data aquired!')

    def T1measurement_IR_SE(self):
        print('Measuring T1 (SE)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1values = np.matrix(np.zeros((2, params.TIsteps)))
        self.T1peakvalues = np.zeros(params.TIsteps)
        
        self.estimated_time = 0
        for n in range(params.TIsteps):
            self.estimated_time = self.estimated_time + ((100 + params.flippulselength + self.T1steps[n]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            
        self.T1steps[0] = round(self.T1steps[0], 1)
        params.TI = self.T1steps[0]
        seq.IR_SE_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TIsteps):
            print(n + 1, '/', params.TIsteps)
            self.T1steps[n] = round(self.T1steps[n], 1)
            params.TI = self.T1steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.IR_SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T1peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + params.flippulselength + self.T1steps[m]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TIsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.T1values[0, :] = self.T1steps
        params.T1values[1, :] = self.T1peakvalues

        params.TI = self.TI_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TIsteps, 2)))
        self.datatxt1 = np.transpose(params.T1values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T1 (SE) Data aquired!')

    def T1measurement_IR_FID_Gs(self):
        print('Measuring T1 (Slice, FID)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1values = np.matrix(np.zeros((2, params.TIsteps)))
        self.T1peakvalues = np.zeros(params.TIsteps)
        
        self.estimated_time = 0
        for n in range(params.TIsteps):
            self.estimated_time = self.estimated_time + ((100 + 4*params.flippulselength + self.T1steps[n]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            
        self.T1steps[0] = round(self.T1steps[0], 1)
        params.TI = self.T1steps[0]
        seq.IR_FID_Gs_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_FID_Gs()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TIsteps):
            print(n + 1, '/', params.TIsteps)
            self.T1steps[n] = round(self.T1steps[n], 1)
            params.TI = self.T1steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.IR_FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T1peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + 4*params.flippulselength + self.T1steps[m]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TIsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.T1values[0, :] = self.T1steps
        params.T1values[1, :] = self.T1peakvalues

        params.TI = self.TI_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TIsteps, 2)))
        self.datatxt1 = np.transpose(params.T1values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T1 (Slice, FID) Data aquired!')

    def T1measurement_IR_SE_Gs(self):
        print('Measuring T1 (Slice, SE)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1values = np.matrix(np.zeros((2, params.TIsteps)))
        self.T1peakvalues = np.zeros(params.TIsteps)
        
        self.estimated_time = 0
        for n in range(params.TIsteps):
            self.estimated_time = self.estimated_time + ((100 + 4*params.flippulselength + self.T1steps[m]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            
        self.T1steps[0] = round(self.T1steps[0], 1)
        params.TI = self.T1steps[0]
        seq.IR_SE_Gs_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE_Gs()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TIsteps):
            print(n + 1, '/', params.TIsteps)
            self.T1steps[n] = round(self.T1steps[n], 1)
            params.TI = self.T1steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.IR_SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T1peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + 4*params.flippulselength + self.T1steps[m]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
                self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TIsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.T1values[0, :] = self.T1steps
        params.T1values[1, :] = self.T1peakvalues

        params.TI = self.TI_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TIsteps, 2)))
        self.datatxt1 = np.transpose(params.T1values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T1 (Slice, SE) Data aquired!')

    def T1process(self):
        print('Calculating T1...')
        self.procdata = np.genfromtxt(params.datapath + '.txt')
        params.T1values = np.transpose(self.procdata)

        params.T1xvalues = np.zeros(params.T1values.shape[1])
        params.T1yvalues1 = np.zeros(params.T1values.shape[1])
        params.T1yvalues2 = np.zeros(params.T1values.shape[1])
        params.T1xvalues[:] = params.T1values[0, :]
        params.T1yvalues1[:] = params.T1values[1, :]
        params.T1yvalues2[:] = params.T1values[1, :]

        self.minindex = np.argmin(params.T1yvalues1)
        if self.minindex >= 1:
            params.T1yvalues2[0:self.minindex] = -params.T1yvalues1[0:self.minindex]
        self.T1ymax = np.max(params.T1yvalues2)

        params.T1yvalues2[:] = np.log(self.T1ymax - params.T1yvalues2)
        params.T1yvalues2[np.isinf(params.T1yvalues2)] = np.nan

        params.T1linregres = linregress(params.T1xvalues[np.isnan(params.T1yvalues2) == False], params.T1yvalues2[np.isnan(params.T1yvalues2) == False])
        params.T1regyvalues2 = params.T1linregres.slope * params.T1xvalues + params.T1linregres.intercept
        params.T1 = round(-(1 / params.T1linregres.slope), 2)
        params.T1regyvalues1 = abs(self.T1ymax - np.exp(params.T1regyvalues2))

        print('T1 calculated!')

    def T1measurement_Image_IR_GRE(self):
        print('Measuring T1 (2D GRE)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1stepsimg = np.zeros((params.TIsteps))
        params.T1img_mag = np.array(np.zeros((params.TIsteps, params.nPE, params.nPE)))

        for n in range(params.TIsteps):
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

            print(n + 1, '/', params.TIsteps)
            params.T1stepsimg[n] = round(self.T1steps[n], 1)
            params.TI = params.T1stepsimg[n]
            seq.Image_IR_GRE_setup()
            seq.Sequence_upload()
            seq.acquire_image_GRE()
            proc.image_process()
            params.T1img_mag[n, :, :] = params.img_mag[:, :]
            time.sleep(params.TR / 1000)

        params.TI = self.TI_temp
        params.saveFileData()

        self.datatxt1 = np.zeros((params.T1stepsimg.shape[0]))
        self.datatxt1 = np.transpose(params.T1stepsimg)
        np.savetxt(params.datapath + '_Image_TI_steps.txt', self.datatxt1)

        self.datatxt2 = np.matrix(np.zeros((params.T1img_mag.shape[1], params.T1img_mag.shape[0] * params.T1img_mag.shape[2])))
        for m in range(params.T1img_mag.shape[0]):
            self.datatxt2[:, m * params.T1img_mag.shape[2]:m * params.T1img_mag.shape[2] + params.T1img_mag.shape[2]] = params.T1img_mag[m, :, :]
        np.savetxt(params.datapath + '_Image_Magnitude.txt', self.datatxt2)

        print('T1 (2D GRE) Data aquired!')

    def T1measurement_Image_IR_SE(self):
        print('Measuring T1 (2D SE)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1stepsimg = np.zeros((params.TIsteps))
        params.T1img_mag = np.array(np.zeros((params.TIsteps, params.nPE, params.nPE)))

        for n in range(params.TIsteps):
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

            print(n + 1, '/', params.TIsteps)
            params.T1stepsimg[n] = round(self.T1steps[n], 1)
            params.TI = params.T1stepsimg[n]
            seq.Image_IR_SE_setup()
            seq.Sequence_upload()
            seq.acquire_image_SE()
            proc.image_process()
            params.T1img_mag[n, :, :] = params.img_mag[:, :]
            time.sleep(params.TR / 1000)

        params.TI = self.TI_temp
        params.saveFileData()

        self.datatxt1 = np.zeros((params.T1stepsimg.shape[0]))
        self.datatxt1 = np.transpose(params.T1stepsimg)
        np.savetxt(params.datapath + '_Image_TI_steps.txt', self.datatxt1)

        self.datatxt2 = np.matrix(np.zeros((params.T1img_mag.shape[1], params.T1img_mag.shape[0] * params.T1img_mag.shape[2])))
        for m in range(params.T1img_mag.shape[0]):
            self.datatxt2[:, m * params.T1img_mag.shape[2]:m * params.T1img_mag.shape[2] + params.T1img_mag.shape[2]] = params.T1img_mag[m, :, :]
        np.savetxt(params.datapath + '_Image_Magnitude.txt', self.datatxt2)

        print('T1 (2D SE) Data aquired!')

    def T1measurement_Image_IR_GRE_Gs(self):
        print('Measuring T1 (Slice, 2D GRE)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1stepsimg = np.zeros((params.TIsteps))
        params.T1img_mag = np.array(np.zeros((params.TIsteps, params.nPE, params.nPE)))

        for n in range(params.TIsteps):
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

            print(n + 1, '/', params.TIsteps)
            params.T1stepsimg[n] = round(self.T1steps[n], 1)
            params.TI = params.T1stepsimg[n]
            seq.Image_IR_GRE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_image_GRE_Gs()
            proc.image_process()
            params.T1img_mag[n, :, :] = params.img_mag[:, :]
            time.sleep(params.TR / 1000)

        params.TI = self.TI_temp
        params.saveFileData()

        self.datatxt1 = np.zeros((params.T1stepsimg.shape[0]))
        self.datatxt1 = np.transpose(params.T1stepsimg)
        np.savetxt(params.datapath + '_Image_TI_steps.txt', self.datatxt1)

        self.datatxt2 = np.matrix(
            np.zeros((params.T1img_mag.shape[1], params.T1img_mag.shape[0] * params.T1img_mag.shape[2])))
        for m in range(params.T1img_mag.shape[0]):
            self.datatxt2[:, m * params.T1img_mag.shape[2]:m * params.T1img_mag.shape[2] + params.T1img_mag.shape[2]] = params.T1img_mag[m, :, :]
        np.savetxt(params.datapath + '_Image_Magnitude.txt', self.datatxt2)

        print('T1 (Slice, 2D GRE) Data aquired!')

    def T1measurement_Image_IR_SE_Gs(self):
        print('Measuring T1 (Slice, 2D SE)...')

        self.TI_temp = 0
        self.TI_temp = params.TI

        self.T1steps = np.linspace(params.TIstart, params.TIstop, params.TIsteps)
        params.T1stepsimg = np.zeros((params.TIsteps))
        params.T1img_mag = np.array(np.zeros((params.TIsteps, params.nPE, params.nPE)))

        for n in range(params.TIsteps):
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

            print(n + 1, '/', params.TIsteps)
            params.T1stepsimg[n] = round(self.T1steps[n], 1)
            params.TI = params.T1stepsimg[n]
            seq.Image_IR_SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_image_SE_Gs()
            proc.image_process()
            params.T1img_mag[n, :, :] = params.img_mag[:, :]
            time.sleep(params.TR / 1000)

        params.TI = self.TI_temp
        params.saveFileData()

        self.datatxt1 = np.zeros((params.T1stepsimg.shape[0]))
        self.datatxt1 = np.transpose(params.T1stepsimg)
        np.savetxt(params.datapath + '_Image_TI_steps.txt', self.datatxt1)

        self.datatxt2 = np.matrix(np.zeros((params.T1img_mag.shape[1], params.T1img_mag.shape[0] * params.T1img_mag.shape[2])))
        for m in range(params.T1img_mag.shape[0]):
            self.datatxt2[:, m * params.T1img_mag.shape[2]:m * params.T1img_mag.shape[2] + params.T1img_mag.shape[2]] = params.T1img_mag[m, :, :]
        np.savetxt(params.datapath + '_Image_Magnitude.txt', self.datatxt2)

        print('T1 (Slice, 2D SE) Data aquired!')

    def T1imageprocess(self):
        print('Calculating T1 map...')

        self.procdata = np.genfromtxt(params.datapath + '_Image_TI_steps.txt')
        params.T1stepsimg = np.transpose(self.procdata)

        self.procdata = np.genfromtxt(params.datapath + '_Image_Magnitude.txt')
        params.T1img_mag = np.array(np.zeros((int(self.procdata.shape[1] / self.procdata.shape[0]), self.procdata.shape[0], self.procdata.shape[0])))

        for n in range(int(self.procdata.shape[1] / self.procdata.shape[0])):
            params.T1img_mag[n, :, :] = self.procdata[:, n * self.procdata.shape[0]:n * self.procdata.shape[0] + self.procdata.shape[0]]
        params.T1imgvalues = np.matrix(np.zeros((params.T1img_mag.shape[1], params.T1img_mag.shape[2])))

        for n in range(params.T1img_mag.shape[1]):
            for m in range(params.T1img_mag.shape[2]):

                params.T1xvalues = np.zeros(params.T1stepsimg.shape[0])
                params.T1yvalues1 = np.zeros(params.T1stepsimg.shape[0])
                params.T1yvalues2 = np.zeros(params.T1stepsimg.shape[0])
                params.T1xvalues[:] = params.T1stepsimg[:]
                params.T1yvalues1[:] = params.T1img_mag[:, n, m]
                params.T1yvalues2[:] = params.T1img_mag[:, n, m]

                self.minindex = np.argmin(params.T1yvalues1)
                if self.minindex >= 1:
                    params.T1yvalues2[0:self.minindex - 1] = -params.T1yvalues1[0:self.minindex - 1]
                self.T1ymax = np.max(params.T1yvalues2)

                params.T1yvalues2[:] = np.log(self.T1ymax - params.T1yvalues2)
                params.T1yvalues2[np.isinf(params.T1yvalues2)] = np.nan

                params.T1linregres = linregress(params.T1xvalues[np.isnan(params.T1yvalues2) == False], params.T1yvalues2[np.isnan(params.T1yvalues2) == False])
                params.T1imgvalues[n, m] = round(-(1 / params.T1linregres.slope), 2)

        self.img_max = np.max(np.amax(params.T1img_mag[params.T1img_mag.shape[0] - 1, :, :]))
        params.T1imgvalues[params.T1img_mag[params.T1img_mag.shape[0] - 1, :, :] < self.img_max * params.signalmask] = np.nan

        print('T1 map calculated!')

    def T2measurement_SE(self):
        print('Measuring T2 (SE)...')

        self.TE_temp = 0
        self.TE_temp = params.TE

        self.T2steps = np.linspace(params.TEstart, params.TEstop, params.TEsteps)
        params.T2values = np.matrix(np.zeros((2, params.TEsteps)))
        self.T2peakvalues = np.zeros(params.TEsteps)
        
        self.estimated_time = 0
        for n in range(params.TEsteps):
            self.estimated_time = self.estimated_time + ((100 + params.flippulselength/2 + self.T2steps[n]*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        self.T2steps[0] = round(self.T2steps[0], 1)
        params.TE = self.T2steps[0]
        seq.SE_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TEsteps):
            print(n + 1, '/', params.TEsteps)
            self.T2steps[n] = round(self.T2steps[n], 1)
            params.TE = self.T2steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T2peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + params.flippulselength/2 + self.T2steps[m]*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TEsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)
            

        params.T2values[0, :] = self.T2steps
        params.T2values[1, :] = self.T2peakvalues

        params.TE = self.TE_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TEsteps, 2)))
        self.datatxt1 = np.transpose(params.T2values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T2 (SE) Data aquired!')

    def T2measurement_SIR_FID(self):
        print('Measuring T2 (SIR-FID)...')

        self.SIR_TE_temp = 0
        self.SIR_TE_temp = params.SIR_TE

        self.T2steps = np.linspace(params.TEstart, params.TEstop, params.TEsteps)
        params.T2values = np.matrix(np.zeros((2, params.TEsteps)))
        self.T2peakvalues = np.zeros(params.TEsteps)
        
        self.estimated_time = 0
        for n in range(params.TEsteps):
            self.estimated_time = self.estimated_time + ((100 + params.flippulselength/2 + self.T2steps[n]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        self.T2steps[0] = round(self.T2steps[0], 1)
        params.SIR_TE = self.T2steps[0]
        seq.SIR_FID_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TEsteps):
            print(n + 1, '/', params.TEsteps)
            self.T2steps[n] = round(self.T2steps[n], 1)
            params.SIR_TE = self.T2steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.SIR_FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T2peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + params.flippulselength/2 + self.T2steps[m]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TEsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.T2values[0, :] = self.T2steps
        params.T2values[1, :] = self.T2peakvalues

        params.SIR_TE = self.SIR_TE_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TEsteps, 2)))
        self.datatxt1 = np.transpose(params.T2values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T2 (SIR-FID) Data aquired!')

    def T2measurement_SE_Gs(self):
        print('Measuring T2 (Slice, SE)...')

        self.TE_temp = 0
        self.TE_temp = params.TE

        self.T2steps = np.linspace(params.TEstart, params.TEstop, params.TEsteps)
        params.T2values = np.matrix(np.zeros((2, params.TEsteps)))
        self.T2peakvalues = np.zeros(params.TEsteps)
        
        self.estimated_time = 0
        for n in range(params.TEsteps):
            self.estimated_time = self.estimated_time + ((100 + 2*params.flippulselength + self.T2steps[n]*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        self.T2steps[0] = round(self.T2steps[0], 1)
        params.TE = self.T2steps[0]
        seq.SE_Gs_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE_Gs()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TEsteps):
            print(n + 1, '/', params.TEsteps)
            self.T2steps[n] = round(self.T2steps[n], 1)
            params.TE = self.T2steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T2peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + 2*params.flippulselength + self.T2steps[m]*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TEsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.T2values[0, :] = self.T2steps
        params.T2values[1, :] = self.T2peakvalues

        params.TE = self.TE_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TEsteps, 2)))
        self.datatxt1 = np.transpose(params.T2values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T2 (Slice, SE) Data aquired!')

    def T2measurement_SIR_FID_Gs(self):
        print('Measuring T2 (Slice, SIR-FID)...')

        self.SIR_TE_temp = 0
        self.SIR_TE_temp = params.SIR_TE

        self.T2steps = np.linspace(params.TEstart, params.TEstop, params.TEsteps)
        params.T2values = np.matrix(np.zeros((2, params.TEsteps)))
        self.T2peakvalues = np.zeros(params.TEsteps)
        
        self.estimated_time = 0
        for n in range(params.TEsteps):
            self.estimated_time = self.estimated_time + ((100 + 2*params.flippulselength + self.T2steps[n]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
        
        self.T2steps[0] = round(self.T2steps[0], 1)
        params.SIR_TE = self.T2steps[0]
        seq.SIR_FID_Gs_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE_Gs()
        proc.spectrum_process()
        proc.spectrum_analytics()
        if params.measurement_time_dialog == 1:
            msg_box = QMessageBox()
            msg_box.setText('Pre-measuring...')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        else: time.sleep((params.TR-100)/1000)
        time.sleep(0.1)

        for n in range(params.TEsteps):
            print(n + 1, '/', params.TEsteps)
            self.T2steps[n] = round(self.T2steps[n], 1)
            params.SIR_TE = self.T2steps[n]
            # if params.SNR >= 100:
                # params.frequency = params.centerfrequency
                # print('Recenter to: ', params.frequency)
                # params.saveFileParameter()
            seq.SIR_FID_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T2peakvalues[n] = params.peakvalue
            
            self.remaining_time_1 = 0
            for m in range(n):
                self.remaining_time_1 = self.remaining_time_1 + ((100 + 2*params.flippulselength + self.T2steps[m]*1000 + params.TE*1000 + (params.TS*1000)/2 + 400 + params.spoilertime) / 1000 + params.TR)
            self.remaining_time_2 = (self.estimated_time - self.remaining_time_1)/1000
            self.remaining_time_h = math.floor(self.remaining_time_2 / (3600))
            self.remaining_time_min = math.floor(self.remaining_time_2 / 60)
            self.remaining_time_s = int(self.remaining_time_2 % 60)
            
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Measuring... ' + str(n+1) + '/' + str(params.TEsteps) + '\nRemaining time: ' + str(self.remaining_time_h) + 'h' + str(self.remaining_time_min) + 'min' + str(self.remaining_time_s) + 's')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

        params.T2values[0, :] = self.T2steps
        params.T2values[1, :] = self.T2peakvalues

        params.SIR_TE = self.SIR_TE_temp
        params.saveFileParameter()

        self.datatxt1 = np.matrix(np.zeros((params.TEsteps, 2)))
        self.datatxt1 = np.transpose(params.T2values)
        np.savetxt(params.datapath + '.txt', self.datatxt1)

        print('T2 (Slice, SIR-FID) Data aquired!')

    def T2process(self):
        print('Calculating T2...')
        self.procdata = np.genfromtxt(params.datapath + '.txt')
        params.T2values = np.transpose(self.procdata)

        params.T2xvalues = np.zeros(params.T2values.shape[1])
        params.T2yvalues = np.zeros(params.T2values.shape[1])
        params.T2xvalues[:] = params.T2values[0, :]
        params.T2yvalues[:] = np.log(params.T2values[1, :])

        params.T2linregres = linregress(params.T2xvalues, params.T2yvalues)
        params.T2regyvalues = params.T2linregres.slope * params.T2xvalues + params.T2linregres.intercept
        params.T2 = round(-(1 / params.T2linregres.slope), 2)

        print('T2 calculated!')

    def T2measurement_Image_SE(self):
        print('Measuring T2 (2D SE)...')

        self.TE_temp = 0
        self.TE_temp = params.TE

        self.T2steps = np.linspace(params.TEstart, params.TEstop, params.TEsteps)
        params.T2stepsimg = np.zeros((params.TEsteps))
        params.T2img_mag = np.array(np.zeros((params.TEsteps, params.nPE, params.nPE)))

        for n in range(params.TEsteps):
            params.TE = self.TE_temp
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

            print(n + 1, '/', params.TEsteps)
            params.T2stepsimg[n] = round(self.T2steps[n], 1)
            params.TE = params.T2stepsimg[n]
            seq.Image_SE_setup()
            seq.Sequence_upload()
            seq.acquire_image_SE()
            proc.image_process()
            params.T2img_mag[n, :, :] = params.img_mag[:, :]
            time.sleep(params.TR / 1000)

        params.TE = self.TE_temp
        params.saveFileData()

        self.datatxt1 = np.zeros((params.T2stepsimg.shape[0]))
        self.datatxt1 = np.transpose(params.T2stepsimg)
        np.savetxt(params.datapath + '_Image_TE_steps.txt', self.datatxt1)

        self.datatxt2 = np.matrix(np.zeros((params.T2img_mag.shape[1], params.T2img_mag.shape[0] * params.T2img_mag.shape[2])))
        for m in range(params.T2img_mag.shape[0]):
            self.datatxt2[:, m * params.T2img_mag.shape[2]:m * params.T2img_mag.shape[2] + params.T2img_mag.shape[2]] = params.T2img_mag[m, :, :]
        np.savetxt(params.datapath + '_Image_Magnitude.txt', self.datatxt2)

        print('T2 (2D SE) Data aquired!')

    def T2measurement_Image_SIR_GRE(self):
        print('\033[1m' + 'WIP, 2D SIR-GRE sequence not jet implemented' + '\033[0m')

    def T2measurement_Image_SE_Gs(self):
        print('Measuring T2 (Slice, 2D SE)...')

        self.SIR_TE_temp = 0
        self.SIR_TE_temp = params.SIR_TE

        self.T2steps = np.linspace(params.TEstart, params.TEstop, params.TEsteps)
        params.T2stepsimg = np.zeros((params.TEsteps))
        params.T2img_mag = np.array(np.zeros((params.TEsteps, params.nPE, params.nPE)))

        for n in range(params.TEsteps):
            params.SIR_TE = self.TE_temp
            seq.RXconfig_upload()
            seq.Gradients_upload()
            seq.Frequency_upload()
            seq.RFattenuation_upload()
            seq.SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE_Gs()
            proc.spectrum_process()
            proc.spectrum_analytics()
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            print('Autorecenter to:', params.frequency)
            if params.measurement_time_dialog == 1:
                msg_box = QMessageBox()
                msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                msg_box.button(QMessageBox.Ok).hide()
                msg_box.exec()
            else: time.sleep((params.TR-100)/1000)
            time.sleep(0.1)

            print(n + 1, '/', params.TEsteps)
            params.T2stepsimg[n] = round(self.T2steps[n], 1)
            params.SIR_TE = params.T2stepsimg[n]
            seq.Image_SE_Gs_setup()
            seq.Sequence_upload()
            seq.acquire_image_SE_Gs()
            proc.image_process()
            params.T2img_mag[n, :, :] = params.img_mag[:, :]
            time.sleep(params.TR / 1000)

        params.SIR_TE = self.SIR_TE_temp
        params.saveFileData()

        self.datatxt1 = np.zeros((params.T2stepsimg.shape[0]))
        self.datatxt1 = np.transpose(params.T2stepsimg)
        np.savetxt(params.datapath + '_Image_TE_steps.txt', self.datatxt1)

        self.datatxt2 = np.matrix(np.zeros((params.T2img_mag.shape[1], params.T2img_mag.shape[0] * params.T2img_mag.shape[2])))
        for m in range(params.T2img_mag.shape[0]):
            self.datatxt2[:, m * params.T2img_mag.shape[2]:m * params.T2img_mag.shape[2] + params.T2img_mag.shape[2]] = params.T2img_mag[m, :, :]
        np.savetxt(params.datapath + '_Image_Magnitude.txt', self.datatxt2)

        print('T2 (Slice, 2D SE) Data aquired!')

    def T2measurement_Image_SIR_GRE_Gs(self):
        print('\033[1m' + 'WIP, 2D SIR-GRE (slice) sequence not implemented' + '\033[0m')

    def T2imageprocess(self):
        print('Calculating T2 map...')

        self.procdata = np.genfromtxt(params.datapath + '_Image_TE_steps.txt')
        params.T2stepsimg = np.transpose(self.procdata)

        self.procdata = np.genfromtxt(params.datapath + '_Image_Magnitude.txt')
        params.T2img_mag = np.array(np.zeros((int(self.procdata.shape[1] / self.procdata.shape[0]), self.procdata.shape[0], self.procdata.shape[0])))

        for n in range(int(self.procdata.shape[1] / self.procdata.shape[0])):
            params.T2img_mag[n, :, :] = self.procdata[:, n * self.procdata.shape[0]:n * self.procdata.shape[0] + self.procdata.shape[0]]
        params.T2imgvalues = np.matrix(np.zeros((params.T2img_mag.shape[1], params.T2img_mag.shape[2])))

        for n in range(params.T2img_mag.shape[1]):
            for m in range(params.T2img_mag.shape[2]):
                params.T2xvalues = np.zeros(params.T2stepsimg.shape[0])
                params.T2yvalues = np.zeros(params.T2stepsimg.shape[0])
                params.T2xvalues[:] = params.T2stepsimg[:]
                params.T2yvalues[:] = np.log(params.T2img_mag[:, n, m])

                params.T2linregres = linregress(params.T2xvalues, params.T2yvalues)
                params.T2imgvalues[n, m] = round(-(1 / params.T2linregres.slope), 2)

        self.img_max = np.max(np.amax(params.T2img_mag[0, :, :]))
        params.T2imgvalues[params.T2img_mag[0, :, :] < self.img_max * params.signalmask] = np.nan

        print('T2 map calculated!')

    def animation_image_cartesian_process(self):

        self.kspaceanimate = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[1]), dtype=np.complex64))
        self.kspaceanimate_temp = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0])))
        self.animationimage_temp = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0])))
        params.animationimage = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0], params.kspace.shape[0] * 2)))

        self.kspace_centerx = int(params.kspace.shape[1] / 2)
        self.kspace_centery = int(params.kspace.shape[0] / 2)

        for n in range(params.kspace.shape[0]):
            self.kspaceanimate[n, :] = params.kspace[n, :]
            self.kspaceanimate_temp = np.abs(self.kspaceanimate[:,int(self.kspace_centerx - params.kspace.shape[0] / 2 * int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))):int(self.kspace_centerx + params.kspace.shape[0] / 2 * int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))):int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))]) / np.amax(params.k_amp)

            # Image calculations
            I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspaceanimate)))
            self.animationimage_temp[:, :] = np.abs(I[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]) / np.amax(params.img_mag)
            
            # Store animation array
            params.animationimage[n, :, :] = np.concatenate((self.animationimage_temp[:, :], self.kspaceanimate_temp[:, :]), axis=1)

    def animation_image_cartesian_IO_process(self):

        self.kspaceanimate = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[1]), dtype=np.complex64))
        self.kspaceanimate_temp = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0])))
        self.animationimage_temp = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0])))
        params.animationimage = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0], params.kspace.shape[0] * 2)))

        self.kspace_centerx = int(params.kspace.shape[1] / 2)
        self.kspace_centery = int(params.kspace.shape[0] / 2)

        for n in range(int(params.kspace.shape[0]/2)):
            self.kspaceanimate[self.kspace_centery-n, :] = params.kspace[self.kspace_centery-n, :]
            self.kspaceanimate_temp = np.abs(self.kspaceanimate[:,int(self.kspace_centerx - params.kspace.shape[0] / 2 * int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))):int(self.kspace_centerx + params.kspace.shape[0] / 2 * int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))):int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))]) / np.amax(params.k_amp)
            
            # Image calculations
            I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspaceanimate)))
            self.animationimage_temp[:, :] = np.abs(I[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]) / np.amax(params.img_mag)
            
            # Store animation array
            params.animationimage[n*2, :, :] = np.concatenate((self.animationimage_temp[:, :], self.kspaceanimate_temp[:, :]), axis=1)
            
            self.kspaceanimate[self.kspace_centery+n, :] = params.kspace[self.kspace_centery+n, :]
            self.kspaceanimate_temp = np.abs(self.kspaceanimate[:,int(self.kspace_centerx - params.kspace.shape[0] / 2 * int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))):int(self.kspace_centerx + params.kspace.shape[0] / 2 * int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))):int(math.floor(params.kspace.shape[1] / params.kspace.shape[0]))]) / np.amax(params.k_amp)

            # Image calculations
            I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspaceanimate)))
            self.animationimage_temp[:, :] = np.abs(I[:, self.kspace_centerx - int(params.kspace.shape[0] / 2 * params.ROBWscaler):self.kspace_centerx + int(params.kspace.shape[0] / 2 * params.ROBWscaler)]) / np.amax(params.img_mag)
            
            # Store animation array
            params.animationimage[n*2+1, :, :] = np.concatenate((self.animationimage_temp[:, :], self.kspaceanimate_temp[:, :]), axis=1)

    def animation_image_radial_full_process(self):   
        self.kspace_center = int(params.kspace.shape[0] / 2)
        
        self.radialangles = np.arange(0, 180, params.radialanglestep)
        self.radialanglecount = self.radialangles.shape[0]
        
        self.kspaceanimate1 = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0]), dtype=np.complex64))
        self.kspaceanimate2 = np.array(np.zeros((int(params.kspace.shape[0]/params.radialosfactor), int(params.kspace.shape[0]/params.radialosfactor)), dtype=np.complex64))
        self.kspaceanimate_temp = np.array(np.zeros((int(params.kspace.shape[0]/params.radialosfactor), int(params.kspace.shape[0]/params.radialosfactor))))
        self.animationimage_temp = np.array(np.zeros((int(params.kspace.shape[0]/params.radialosfactor), int(params.kspace.shape[0]/params.radialosfactor))))
        params.animationimage = np.array(np.zeros((self.radialanglecount, int(params.kspace.shape[0]/params.radialosfactor), int(params.kspace.shape[0]/params.radialosfactor) * 2)))
        
        for o in range(self.radialanglecount):
            for n in range(o+1):
                self.radialangleradmod100 = int((math.radians(self.radialangles[n]) % (2*np.pi))*100)
                for m in range(params.kspace.shape[0]):
                    self.kspaceanimate1[int(self.kspace_center + math.sin(self.radialangleradmod100/100)*(m-self.kspace_center)), int(self.kspace_center + math.cos(self.radialangleradmod100/100)*(m-self.kspace_center))] = params.kspace[int(self.kspace_center + math.sin(self.radialangleradmod100/100)*(m-self.kspace_center)), int(self.kspace_center + math.cos(self.radialangleradmod100/100)*(m-self.kspace_center))]
                for m in range(int(params.kspace.shape[0]/params.radialosfactor)):
                    self.kspaceanimate2[int(self.kspace_center/params.radialosfactor + math.sin(self.radialangleradmod100/100)*(m-self.kspace_center/params.radialosfactor)), int(self.kspace_center/params.radialosfactor + math.cos(self.radialangleradmod100/100)*(m-self.kspace_center/params.radialosfactor))] = params.kspace[int(self.kspace_center + math.sin(self.radialangleradmod100/100)*(m*params.radialosfactor-self.kspace_center)), int(self.kspace_center + math.cos(self.radialangleradmod100/100)*(m*params.radialosfactor-self.kspace_center))]
            self.kspaceanimate_temp = np.abs(self.kspaceanimate2) / np.amax(params.k_amp)
            # Image calculations
            I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspaceanimate1)))
            self.animationimage_temp = np.abs(I[int(self.kspace_center-self.kspace_center/params.radialosfactor):int(self.kspace_center+self.kspace_center/params.radialosfactor), int(self.kspace_center-self.kspace_center/params.radialosfactor):int(self.kspace_center+self.kspace_center/params.radialosfactor)]) / np.amax(params.img_mag)
            # Store animation array
            params.animationimage[o, :, :] = np.concatenate((self.animationimage_temp[:, :], self.kspaceanimate_temp[:, :]), axis=1)
        
    def animation_image_radial_half_process(self):
        self.kspace_center = int(params.kspace.shape[0] / 2)
        
        self.radialangles = np.arange(0, 360, params.radialanglestep)
        self.radialanglecount = self.radialangles.shape[0]
        
        self.kspaceanimate1 = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0]), dtype=np.complex64))
        self.kspaceanimate2 = np.array(np.zeros((int(params.kspace.shape[0]/(2*params.radialosfactor)), int(params.kspace.shape[0]/(2*params.radialosfactor))), dtype=np.complex64))
        self.kspaceanimate_temp = np.array(np.zeros((int(params.kspace.shape[0]/(2*params.radialosfactor)), int(params.kspace.shape[0]/(2*params.radialosfactor)))))
        self.animationimage_temp = np.array(np.zeros((int(params.kspace.shape[0]/(2*params.radialosfactor)), int(params.kspace.shape[0]/(2*params.radialosfactor)))))
        params.animationimage = np.array(np.zeros((self.radialanglecount, int(params.kspace.shape[0]/(2*params.radialosfactor)), int(params.kspace.shape[0]/(2*params.radialosfactor)) * 2)))
        
        for o in range(self.radialanglecount):
            for n in range(o+1):
                self.radialangleradmod100 = int((math.radians(self.radialangles[n]) % (2*np.pi))*100)
                for m in range(self.kspace_center):
                    self.kspaceanimate1[int(self.kspace_center + math.sin(self.radialangleradmod100/100)*(m)), int(self.kspace_center + math.cos(self.radialangleradmod100/100)*(m))] = params.kspace[int(self.kspace_center + math.sin(self.radialangleradmod100/100)*(m)), int(self.kspace_center + math.cos(self.radialangleradmod100/100)*(m))]
                for m in range(int(self.kspace_center/(2*params.radialosfactor))):
                    self.kspaceanimate2[int(self.kspace_center/(2*params.radialosfactor) + math.sin(self.radialangleradmod100/100)*(m)), int(self.kspace_center/(2*params.radialosfactor) + math.cos(self.radialangleradmod100/100)*(m))] = params.kspace[int(self.kspace_center + math.sin(self.radialangleradmod100/100)*(m*2*params.radialosfactor)), int(self.kspace_center + math.cos(self.radialangleradmod100/100)*(m*2*params.radialosfactor))]
            
            self.kspaceanimate_temp = np.abs(self.kspaceanimate2) / np.amax(params.k_amp)
            # Image calculations
            I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspaceanimate1)))
            self.animationimage_temp = np.abs(I[int(self.kspace_center-self.kspace_center/(2*params.radialosfactor)):int(self.kspace_center+self.kspace_center/(2*params.radialosfactor)), int(self.kspace_center-self.kspace_center/(2*params.radialosfactor)):int(self.kspace_center+self.kspace_center/(2*params.radialosfactor))]) / np.amax(params.img_mag)
            # Store animation array
            params.animationimage[o, :, :] = np.concatenate((self.animationimage_temp[:, :], self.kspaceanimate_temp[:, :]), axis=1)

    def animate_cartesian(self):
        proc.animation_image_cartesian_process()

        import matplotlib.animation as animation

        fig = plt.figure()

        im = plt.imshow(params.animationimage[params.kspace.shape[0]-1, :, :], cmap=params.imagecolormap, animated=True)
        
        plt.axis('off')

        def updatefig(i):
            im.set_array(params.animationimage[i, :, :])
            return im,

        ani = animation.FuncAnimation(fig, updatefig, frames=params.kspace.shape[0], interval=params.animationstep, blit=True)

        plt.show()
        
    def animate_cartesian_IO(self):
        proc.animation_image_cartesian_IO_process()

        import matplotlib.animation as animation

        fig = plt.figure()

        im = plt.imshow(params.animationimage[params.kspace.shape[0]-1, :, :], cmap=params.imagecolormap, animated=True)
        
        plt.axis('off')

        def updatefig(i):
            im.set_array(params.animationimage[i, :, :])
            return im,

        ani = animation.FuncAnimation(fig, updatefig, frames=params.kspace.shape[0], interval=params.animationstep, blit=True)

        plt.show()
        
    def animate_radial_full(self):
        self.radialangles = np.arange(0, 180, params.radialanglestep)
        self.radialanglecount = self.radialangles.shape[0]
        
        proc.animation_image_radial_full_process()

        import matplotlib.animation as animation

        fig = plt.figure()

        im = plt.imshow(params.animationimage[self.radialanglecount-1, :, :], cmap=params.imagecolormap, animated=True)
        
        plt.axis('off')

        def updatefig(i):
            im.set_array(params.animationimage[i, :, :])
            return im,

        ani = animation.FuncAnimation(fig, updatefig, frames=self.radialanglecount, interval=params.animationstep, blit=True)

        plt.show()
                
    def animate_radial_half(self):
        self.radialangles = np.arange(0, 360, params.radialanglestep)
        self.radialanglecount = self.radialangles.shape[0]
        
        proc.animation_image_radial_half_process()

        import matplotlib.animation as animation

        fig = plt.figure()

        im = plt.imshow(params.animationimage[self.radialanglecount-1, :, :], cmap=params.imagecolormap, animated=True)
        
        plt.axis('off')

        def updatefig(i):
            im.set_array(params.animationimage[i, :, :])
            return im,

        ani = animation.FuncAnimation(fig, updatefig, frames=self.radialanglecount, interval=params.animationstep, blit=True)

        plt.show()
        
proc = process()
