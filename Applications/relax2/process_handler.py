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


from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal

import numpy as np
import math
import pandas as pd
from scipy.stats import linregress

from TCPsocket import socket, connected, unconnected
from sequence_handler import seq
from parameter_handler import params


class process:
    def __init__(self):

        params.loadParam()
        params.loadData()

    def spectrum_process(self):
        self.procdata = np.genfromtxt(params.datapath + '.txt', dtype = np.complex64)
        self.procdata = np.transpose(self.procdata)
        params.timeaxis = np.real(self.procdata[0,:])
        params.spectrumdata = self.procdata[1:self.procdata.shape[0],:]
        

        self.data_idx = params.spectrumdata.shape[1]

        params.mag = np.mean(np.abs(params.spectrumdata), axis = 0)
        params.real = np.mean(np.real(params.spectrumdata), axis = 0)
        params.imag = np.mean(np.imag(params.spectrumdata), axis = 0)
        
        self.mag_con = np.convolve(params.mag, np.ones((50,))/50, mode='same')
        self.real_con = np.convolve(params.real, np.ones((50,))/50, mode='same')
        
        params.freqencyaxis = np.linspace(-params.frequencyrange/2, params.frequencyrange/2, self.data_idx) 
        
        #print(params.spectrumdata.shape)
        
        self.fft = np.matrix(np.zeros((params.spectrumdata.shape[0],params.spectrumdata.shape[1]), dtype = np.complex64))
        
        for m in range(params.spectrumdata.shape[0]):
            self.fft[m,:] = np.fft.fftshift(np.fft.fft(np.fft.fftshift(params.spectrumdata[m,:]), n=self.data_idx, norm='ortho'))

        params.spectrumfft = np.transpose(np.mean(abs(self.fft), axis = 0))

        print("Spectrum data processed!")
        
    def image_process(self):
        # Load kspace from file
        self.procdata = np.genfromtxt(params.datapath + '.txt', dtype = np.complex64)
        params.kspace = np.transpose(self.procdata)

        self.kspace_centerx = int(params.kspace.shape[1]/2)
        self.kspace_centery = int(params.kspace.shape[0]/2)
        
        print('k-Space shape: ',params.kspace.shape)
        
        #Undersampling (Option)
        if params.ustime == 1:
            self.ustimecrop = params.kspace.shape[1]/params.ustimeidx
            for n in range(int(self.ustimecrop)):
                for m in range(int(params.ustimeidx/2)):
                    params.kspace[:,int(n*params.ustimeidx+m)] = 0
                    
        if params.usphase == 1:
            self.usphasecrop = params.kspace.shape[0]/params.usphaseidx
            for n in range(int(self.usphasecrop)):
                for m in range(int(params.usphaseidx/2)):
                    params.kspace[int(n*params.usphaseidx+m),:] = 0

        if params.cutcirc == 1:
            #Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) <= self.cutc:
                            params.kspace[jj,ii] = 0
                            
            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) >= self.cuto:
                            params.kspace[jj,ii] = 0
            
        if params.cutrec == 1:
            #Set kSpace to 0 (Option)
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
            
        #Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)
        
        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full
        
        params.img = I[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
        params.img_mag = self.img_mag_full[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
        params.img_pha = self.img_pha_full[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
         
        print("Image data processed!")
            
    def image_3D_process(self):
        # Load kspace from file
        self.procdata = np.genfromtxt(params.datapath + '_3D_' + str(params.SPEsteps) + '.txt', dtype = np.complex64)
        self.kspacetemp = np.transpose(self.procdata)
        params.kspace = np.array(np.zeros((int(params.SPEsteps), int(self.kspacetemp.shape[0]/params.SPEsteps), int(self.kspacetemp.shape[1])), dtype = np.complex64))

        for n in range(params.SPEsteps):
            self.kspacetemp2 = self.kspacetemp[int(n*self.kspacetemp.shape[0]/params.SPEsteps):int(n*self.kspacetemp.shape[0]/params.SPEsteps+self.kspacetemp.shape[0]/params.SPEsteps),:]

            params.kspace[n,0:int(self.kspacetemp.shape[0]/params.SPEsteps),:] = self.kspacetemp[int(n*self.kspacetemp.shape[0]/params.SPEsteps):int(n*self.kspacetemp.shape[0]/params.SPEsteps+self.kspacetemp.shape[0]/params.SPEsteps),:]

        self.kspace_centerx = int(params.kspace.shape[2]/2)
        self.kspace_centery = int(params.kspace.shape[1]/2)
        self.kspace_centerz = int(params.kspace.shape[0]/2)
        
        #Undersampling (Option)
        if params.ustime == 1:
            self.ustimecrop = params.kspace.shape[2]/params.ustimeidx
            for n in range(int(self.ustimecrop)):
                for m in range(int(params.ustimeidx/2)):
                    params.kspace[:,:,int(n*params.ustimeidx+m)] = 0
                    
        if params.usphase == 1:
            self.usphasecrop = params.kspace.shape[1]/params.usphaseidx
            for n in range(int(self.usphasecrop)):
                for m in range(int(params.usphaseidx/2)):
                    params.kspace[:,int(n*params.usphaseidx+m),:] = 0

        if params.cutcirc == 1:
            #Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[2] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[2] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for kk in range(params.kspace.shape[0]):
                    for ii in range(params.kspace.shape[2]):
                        for jj in range(params.kspace.shape[1]):
                            if np.sqrt((ii - (params.kspace.shape[2]/2))**2 + (jj * params.kspace.shape[2]/params.kspace.shape[1] - (params.kspace.shape[2]/2))**2) <= self.cutc:
                                params.kspace[kk,jj,ii] = 0
                            
            if params.cutoutside == 1:
                for kk in range(params.kspace.shape[0]):
                    for ii in range(params.kspace.shape[2]):
                        for jj in range(params.kspace.shape[1]):
                            if np.sqrt((ii - (params.kspace.shape[2]/2))**2 + (jj * params.kspace.shape[2]/params.kspace.shape[1] - (params.kspace.shape[2]/2))**2) >= self.cuto:
                                params.kspace[kk,jj,ii] = 0
            
        if params.cutrec == 1:
            #Set kSpace to 0 (Option)
            self.cutcx = int(params.kspace.shape[2] / 2 * params.cutcentervalue / 100)
            self.cutcy = int(params.kspace.shape[1] / 2 * params.cutcentervalue / 100)
            self.cutox = int(params.kspace.shape[2] / 2 * params.cutoutsidevalue / 100)
            self.cutoy = int(params.kspace.shape[1] / 2 * params.cutoutsidevalue / 100)
        
            if params.cutcenter == 1:
                params.kspace[:,self.kspace_centery - self.cutcy:self.kspace_centery + self.cutcy, self.kspace_centerx - self.cutcx:self.kspace_centerx + self.cutcx] = 0
            
            if params.cutoutside == 1:
                params.kspace[:,0:self.cutoy, :] = 0
                params.kspace[:,params.kspace.shape[1] - self.cutoy:params.kspace.shape[1], :] = 0
                params.kspace[:,:, 0:self.cutox] = 0
                params.kspace[:,:, params.kspace.shape[2] - self.cutox:params.kspace.shape[2]] = 0
            
        #Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fftn(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)

        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full

        params.img = I[:,:,self.kspace_centerx-int(params.kspace.shape[1]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[1]/2*params.ROBWscaler)]
        params.img_mag = self.img_mag_full[:,:,self.kspace_centerx-int(params.kspace.shape[1]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[1]/2*params.ROBWscaler)]
        params.img_pha = self.img_pha_full[:,:,self.kspace_centerx-int(params.kspace.shape[1]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[1]/2*params.ROBWscaler)]#print(params.img_mag.shape)
        print("3D Image data processed!")
        
    def image_diff_process(self):
        # Load kspace from file
        self.procdatatemp = np.genfromtxt(params.datapath + '.txt', dtype = np.complex64)
        self.procdata = self.procdatatemp[:,0:int(self.procdatatemp.shape[1]/2)]
        params.kspace = np.transpose(self.procdata)

        self.kspace_centerx = int(params.kspace.shape[1]/2)
        self.kspace_centery = int(params.kspace.shape[0]/2)
        
        #Undersampling (Option)
        if params.ustime == 1:
            self.ustimecrop = params.kspace.shape[1]/params.ustimeidx
            for n in range(int(self.ustimecrop)):
                for m in range(int(params.ustimeidx/2)):
                    params.kspace[:,int(n*params.ustimeidx+m)] = 0
                    
        if params.usphase == 1:
            self.usphasecrop = params.kspace.shape[0]/params.usphaseidx
            for n in range(int(self.usphasecrop)):
                for m in range(int(params.usphaseidx/2)):
                    params.kspace[int(n*params.usphaseidx+m),:] = 0
       
        if params.cutcirc == 1:
            #Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) <= self.cutc:
                            params.kspace[jj,ii] = 0
                            
            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) >= self.cuto:
                            params.kspace[jj,ii] = 0
            
        if params.cutrec == 1:
            #Set kSpace to 0 (Option)
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
            
        #Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)
        
        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full
        
        params.img = I[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
        params.img_mag = self.img_mag_full[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
        params.img_pha = self.img_pha_full[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
        
        # Load diff kspace from file
        self.procdatatemp = np.genfromtxt(params.datapath + '.txt', dtype = np.complex64)
        self.procdata = self.procdatatemp[:,int(self.procdatatemp.shape[1]/2):int(self.procdatatemp.shape[1])]
        self.kspacediff = np.transpose(self.procdata)
        print(self.kspacediff.shape)
        
        #Undersampling (Option)
        if params.ustime == 1:
            self.ustimecrop = params.kspace.shape[1]/params.ustimeidx
            for n in range(int(self.ustimecrop)):
                for m in range(int(params.ustimeidx/2)):
                    self.kspacediff[:,int(n*params.ustimeidx+m)] = 0
                    
        if params.usphase == 1:
            self.usphasecrop = params.kspace.shape[0]/params.usphaseidx
            for n in range(int(self.usphasecrop)):
                for m in range(int(params.usphaseidx/2)):
                    self.kspacediff[int(n*params.usphaseidx+m),:] = 0

        if params.cutcirc == 1:
            #Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) <= self.cutc:
                            params.kspace[jj,ii] = 0
                            
            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) >= self.cuto:
                            params.kspace[jj,ii] = 0
            
        if params.cutrec == 1:
            #Set kSpace to 0 (Option)
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
            
        #Image calculations
        self.k_amp_full = np.abs(self.kspacediff)
        self.k_pha_full = np.angle(self.kspacediff)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspacediff)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)
        
        self.k_ampdiff = self.k_amp_full
        self.k_phadiff = self.k_pha_full
        
        self.img_magdiff = self.img_mag_full[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
        self.img_phadiff = self.img_pha_full[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)]
        
        params.img_mag_diff = params.img_mag - self.img_magdiff
        
        print("Diffusion Image data processed!")
        
    def radial_process(self):
        # Load kspace from file
        self.procdata = np.genfromtxt(params.datapath + '.txt', dtype = np.complex64)
        params.kspace = np.transpose(self.procdata)

        self.kspace_centerx = int(params.kspace.shape[1]/2)
        self.kspace_centery = int(params.kspace.shape[0]/2)
        
        print('kspace shape',params.kspace.shape)
        
        #Undersampling (Option)
        if params.ustime == 1:
            self.ustimecrop = params.kspace.shape[1]/params.ustimeidx
            for n in range(int(self.ustimecrop)):
                for m in range(int(params.ustimeidx/2)):
                    params.kspace[:,int(n*params.ustimeidx+m)] = 0
                    
        if params.usphase == 1:
            self.usphasecrop = params.kspace.shape[0]/params.usphaseidx
            for n in range(int(self.usphasecrop)):
                for m in range(int(params.usphaseidx/2)):
                    params.kspace[int(n*params.usphaseidx+m),:] = 0


                    
        if params.cutcirc == 1:
            #Set kSpace to 0 (Option)
            self.cutc = params.kspace.shape[1] / 2 * params.cutcentervalue / 100
            self.cuto = params.kspace.shape[1] / 2 * (1 - params.cutoutsidevalue / 100)

            if params.cutcenter == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) <= self.cutc:
                            params.kspace[jj,ii] = 0
                            
            if params.cutoutside == 1:
                for ii in range(params.kspace.shape[1]):
                    for jj in range(params.kspace.shape[0]):
                        if np.sqrt((ii - (params.kspace.shape[1]/2))**2 + (jj * params.kspace.shape[1]/params.kspace.shape[0] - (params.kspace.shape[1]/2))**2) >= self.cuto:
                            params.kspace[jj,ii] = 0
            
        if params.cutrec == 1:
            #Set kSpace to 0 (Option)
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
            
        #Image calculations
        self.k_amp_full = np.abs(params.kspace)
        self.k_pha_full = np.angle(params.kspace)
        I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(params.kspace)))
        self.img_mag_full = np.abs(I)
        self.img_pha_full = np.angle(I)
        
        params.k_amp = self.k_amp_full
        params.k_pha = self.k_pha_full
        
        params.img = I[self.kspace_centery-int(params.nPE/2*params.ROBWscaler):self.kspace_centery+int(params.nPE/2*params.ROBWscaler),self.kspace_centerx-int(params.nPE/2*params.ROBWscaler):self.kspace_centerx+int(params.nPE/2*params.ROBWscaler)]
        params.img_mag = self.img_mag_full[self.kspace_centery-int(params.nPE/2*params.ROBWscaler):self.kspace_centery+int(params.nPE/2*params.ROBWscaler),self.kspace_centerx-int(params.nPE/2*params.ROBWscaler):self.kspace_centerx+int(params.nPE/2*params.ROBWscaler)]#[:, int(self.kspace_centerx - ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.kspace_centerx + ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.bandwidth / (params.kspace.shape[0]-1))]
        params.img_pha = self.img_pha_full[self.kspace_centery-int(params.nPE/2*params.ROBWscaler):self.kspace_centery+int(params.nPE/2*params.ROBWscaler),self.kspace_centerx-int(params.nPE/2*params.ROBWscaler):self.kspace_centerx+int(params.nPE/2*params.ROBWscaler)]#[:, int(self.kspace_centerx - ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.kspace_centerx + ((params.kspace.shape[0] / 2) * int(self.bandwidth / (params.kspace.shape[0]-1)))):int(self.bandwidth / (params.kspace.shape[0]-1))]
        
        # Save Image Data
        #np.savetxt(params.datapath + '_Magnitude_Image.txt', params.img_mag)
        #np.savetxt(params.datapath + '_Phase_Image.txt', params.pha_mag)
        
        print("Image data processed!")
            
        
    def spectrum_analytics(self): 

        params.peakvalue = round(np.max(params.spectrumfft), 3)
        print("Signal: ", params.peakvalue)
        self.maxindex = np.argmax(params.spectrumfft)
        #print("Maxindex: ", self.maxindex)
        self.lowerspectum = params.spectrumfft[1:self.maxindex]
        self.upperspectum = params.spectrumfft[self.maxindex+1:params.spectrumfft.shape[0]]
        #print("lowerspectum: ", self.lowerspectum)
        #print("upperspectum: ", self.upperspectum)
        self.absinvhalflowerspectum = abs(self.lowerspectum - params.peakvalue/2)
        self.absinvhalfupperspectum = abs(self.upperspectum - params.peakvalue/2)
        #print("absinvhalflowerspectum: ", self.absinvhalflowerspectum)
        #print("absinvhalfupperspectum: ", self.absinvhalfupperspectum)
        
        self.lowerindex = np.argmin(self.absinvhalflowerspectum)
        self.upperindex = np.argmin(self.absinvhalfupperspectum)+self.maxindex
        #print("lowerindex: ", self.lowerindex)
        #print("upperindex: ", self.upperindex)
        
        params.FWHM = int(round((self.upperindex - self.lowerindex) * (params.frequencyrange / params.spectrumfft.shape[0])))
        #print("FWHM: ", params.FWHM)
        
        self.lowerlowerindex = self.maxindex - ((self.maxindex - self.lowerindex)*5)
        self.upperupperindex = self.maxindex + ((self.upperindex - self.maxindex)*5)
        

        self.noisevector = np.concatenate((params.spectrumfft[0:self.lowerlowerindex],params.spectrumfft[self.upperupperindex:params.spectrumfft.shape[0]]))
        params.noise = round(np.mean(self.noisevector), 3)
        print("Noise: ", params.noise)
        
        params.SNR = round(params.peakvalue / params.noise, 1)
        if np.isnan(params.SNR) == True:
            params.SNR = 0.001
        print("SNR: ", params.SNR)

        params.centerfrequency = round(params.frequency + ((self.maxindex - params.spectrumfft.shape[0]/2) * params.frequencyrange / params.spectrumfft.shape[0] ) / 1.0e6, 6)
        
        params.inhomogeneity = int(round(params.FWHM/params.centerfrequency))
        
        print("B0 inhomogeneity: ", params.inhomogeneity, "ppm")
        #print("Center Frequency: ", params.centerfrequency)
        print("Data analysed!")
        
    def image_analytics(self):
        self.img_max = np.max(np.amax(params.img_mag))
        
        self.img_phantomcut = np.matrix(np.zeros((params.img_mag.shape[0],params.img_mag.shape[1])))
        self.img_phantomcut[:,:] = params.img_mag[:,:]
        self.img_phantomcut[self.img_phantomcut < self.img_max/2] = np.nan
        params.peakvalue = round(np.mean(self.img_phantomcut[np.isnan(self.img_phantomcut) == False]), 3)
        print("Signal: ", params.peakvalue)
        
        self.img_noisecut = np.matrix(np.zeros((params.img_mag.shape[0],params.img_mag.shape[1])))
        self.img_noisecut[:,:] = params.img_mag[:,:]
        self.img_noisecut[self.img_noisecut >= self.img_max/2] = np.nan
        params.noise = round(np.mean(self.img_noisecut[np.isnan(self.img_noisecut) == False]), 3)
        print("Noise: ", params.noise)
        
        params.SNR = round(params.peakvalue / params.noise, 1)
        if np.isnan(params.SNR) == True:
            params.SNR = 0.001
        print("SNR: ", params.SNR)
        
        
    def Autocentertool(self):
        print('Finding Signals...')
        
        self.freqtemp = 0
        self.freqtemp = params.frequency
        
        #params.GUImode = 0
        #params.sequence = 1
        #params.TR = 2000
        
        self.ACidx = round(abs((params.ACstop*1.0e6-params.ACstart*1.0e6))/(params.ACstepwidth))+1
        self.ACsteps = np.linspace(params.ACstart,params.ACstop,self.ACidx)
        params.ACvalues = np.matrix(np.zeros((2,self.ACidx)))
        self.ACpeakvalues = np.zeros(self.ACidx)
        
        for n in range(self.ACidx):
            print(n+1, '/', self.ACidx)
            self.ACsteps[n] = round(self.ACsteps[n], 6)
            params.frequency = self.ACsteps[n]
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.ACsteps[n] = params.centerfrequency
            self.ACpeakvalues[n] = params.peakvalue
            time.sleep(params.TR/1000)
            
        params.ACvalues[0,:] = self.ACsteps
        params.ACvalues[1,:] = self.ACpeakvalues
        params.Reffrequency = self.ACsteps[np.argmax(self.ACpeakvalues)]
        
        np.savetxt('imagedata/Autocenter_Tool_Data.txt', np.transpose(params.ACvalues))

        params.frequency = self.freqtemp
        
    def Flipangletool(self):
        print('Finding Flipangles...')
        
        self.RFattenuationtemp = 0
        self.RFattenuationtemp = params.RFattenuation
        
        self.FAsteps = np.linspace(params.FAstart,params.FAstop,params.FAsteps)
        params.FAvalues = np.matrix(np.zeros((2,params.FAsteps)))
        self.FApeakvalues = np.zeros(params.FAsteps)
        
        params.RFattenuation = -31.75
        seq.sequence_upload()
        proc.spectrum_process()
        proc.spectrum_analytics()
        time.sleep(params.TR/1000)
        
        for n in range(params.FAsteps):
            print(n+1, '/', params.FAsteps)
            self.FAsteps[n] = int(self.FAsteps[n]/0.25)*0.25
            print(self.FAsteps[n])
            params.RFattenuation = self.FAsteps[n]
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.FApeakvalues[n] = params.peakvalue
            time.sleep(params.TR/1000)
            
        params.FAvalues[0,:] = self.FAsteps
        params.FAvalues[1,:] = self.FApeakvalues
        
        params.RefRFattenuation = self.FAsteps[np.argmax(self.FApeakvalues)]
        
        np.savetxt('imagedata/Flipangle_Tool_Data.txt', np.transpose(params.FAvalues))

        params.RFattenuation = self.RFattenuationtemp
        
    def Shimtool(self):
        print('Processing shimtool...')
        
        self.frequencytemp = 0
        self.frequencytemp = params.frequency
        self.shimtemp = [0, 0, 0, 0]
        self.shimtemp[:] = params.grad[:]
        #print(self.shimtemp)
        
        self.STsteps = np.linspace(params.ToolShimStart,params.ToolShimStop,params.ToolShimSteps)
        self.STsteps = self.STsteps.astype(int)
        #print(self.STsteps)
        
        params.STvalues = np.matrix(np.zeros((5,params.ToolShimSteps)))
        params.STvalues[0,:] = self.STsteps
        
        seq.sequence_upload()
        proc.spectrum_process()
        proc.spectrum_analytics()
        time.sleep(params.TR/1000)
        params.frequency = params.centerfrequency
        
        if params.ToolShimChannel[0] == 1:
            self.STpeakvaluesX = np.zeros(params.ToolShimSteps)
            params.grad[0] = self.STsteps[0]
            
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            time.sleep(params.TR/1000)
            
            for n in range(params.ToolShimSteps):
                print(n+1, '/', params.ToolShimSteps)
                params.grad[0] = self.STsteps[n]
                params.frequency = params.centerfrequency
                
                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesX[n] = params.peakvalue
                time.sleep(params.TR/1000)
                
            params.STvalues[1,:] = self.STpeakvaluesX
            
            params.frequency = self.frequencytemp
            params.grad[0] = self.shimtemp[0]
            
        if params.ToolShimChannel[1] == 1:
            self.STpeakvaluesY = np.zeros(params.ToolShimSteps)
            params.grad[1] = self.STsteps[0]
            
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            time.sleep(params.TR/1000)
            
            for n in range(params.ToolShimSteps):
                print(n+1, '/', params.ToolShimSteps)
                params.grad[1] = self.STsteps[n]
                params.frequency = params.centerfrequency
                
                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesY[n] = params.peakvalue
                time.sleep(params.TR/1000)
                
            params.STvalues[2,:] = self.STpeakvaluesY
        
            params.frequency = self.frequencytemp
            params.grad[1] = self.shimtemp[1]
            
        if params.ToolShimChannel[2] == 1:
            self.STpeakvaluesZ = np.zeros(params.ToolShimSteps)
            params.grad[2] = self.STsteps[0]
            
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            time.sleep(params.TR/1000)
            
            for n in range(params.ToolShimSteps):
                print(n+1, '/', params.ToolShimSteps)
                params.frequency = params.centerfrequency
                params.grad[2] = self.STsteps[n]
                
                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesZ[n] = params.peakvalue
                time.sleep(params.TR/1000)
                
            params.STvalues[3,:] = self.STpeakvaluesZ
            
            params.frequency = self.frequencytemp
            params.grad[2] = self.shimtemp[2]
            
        if params.ToolShimChannel[3] == 1:
            self.STpeakvaluesZ2 = np.zeros(params.ToolShimSteps)
            params.grad[3] = self.STsteps[0]
            
            seq.sequence_upload()
            proc.spectrum_process()
            proc.spectrum_analytics()
            time.sleep(params.TR/1000)
            
            for n in range(params.ToolShimSteps):
                print(n+1, '/', params.ToolShimSteps)
                params.frequency = params.centerfrequency
                params.grad[3] = self.STsteps[n]
                
                seq.sequence_upload()
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.STpeakvaluesZ2[n] = params.peakvalue
                time.sleep(params.TR/1000)
                
            params.STvalues[4,:] = self.STpeakvaluesZ2
            
            params.frequency = self.frequencytemp
            params.grad[3] = self.shimtemp[3]
            
        np.savetxt('imagedata/Shim_Tool_Data.txt', np.transpose(params.STvalues))

    def FieldMapB0(self):
        print('Measuring B0 field...')
        
        self.GUImodetemp = 0
        self.sequencetemp = 0
        self.datapathtemp = ''
        self.GUImodetemp = params.GUImode
        self.sequencetemp = params.sequence
        self.datapathtemp = params.datapath
        
        params.GUImode = 1
        params.sequence = 4
        params.datapath = 'rawdata/Tool_rawdata'
        
        self.TEtemp = 0
        self.TEtemp = params.TE
        params.TE = params.TE + 1
        
        seq.sequence_upload()
        proc.image_process()
        
        self.FieldMapB0_S2_raw = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S2 = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S2_raw[:,:] = params.img_pha[:,:]
        self.FieldMapB0_S2[:,:] = params.img_pha[:,:]
        
        for kk in range (10):
        
            for jj in range(int(self.FieldMapB0_S2.shape[1]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[1]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] - 2 * math.pi
            
            for jj in range(int(self.FieldMapB0_S2.shape[0]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[0]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] - 2 * math.pi
        
        time.sleep(params.TR/1000)
        
        params.TE = self.TEtemp
        
        seq.sequence_upload()
        proc.image_process()
        
        self.FieldMapB0_S1_raw = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S1 = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S1_raw = params.img_pha
        self.FieldMapB0_S1 = params.img_pha
        
        for kk in range (10):
        
            for jj in range(int(self.FieldMapB0_S1.shape[1]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[1]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] - 2 * math.pi
            
            for jj in range(int(self.FieldMapB0_S1.shape[0]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[0]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] - 2 * math.pi

        params.B0DeltaB0map = (self.FieldMapB0_S2 - self.FieldMapB0_S1) / (2 * math.pi * 42.577 * (((params.TE + 1) - params.TE))/1000)
        params.B0DeltaB0mapmasked = np.matrix(np.zeros((params.B0DeltaB0map.shape[1],params.B0DeltaB0map.shape[0])))
        params.B0DeltaB0mapmasked[:,:] = params.B0DeltaB0map[:,:]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B0DeltaB0mapmasked[params.img_mag < self.img_max * 0.3] = np.nan
        
        self.FieldMapB0_pha_raw = np.concatenate((self.FieldMapB0_S1_raw,self.FieldMapB0_S2_raw),axis=0)
        np.savetxt('imagedata/FieldMap_B0_Phase_Raw_Data.txt', self.FieldMapB0_pha_raw)
        self.FieldMapB0_pha = np.concatenate((self.FieldMapB0_S1,self.FieldMapB0_S2),axis=0)
        np.savetxt('imagedata/FieldMap_B0_Phase_Data.txt', self.FieldMapB0_pha)
        self.B0DeltaB0maps = np.concatenate((params.img_mag,params.B0DeltaB0map,params.B0DeltaB0mapmasked),axis=0)
        np.savetxt('imagedata/FieldMap_B0_deltat1ms_Mag_Map_MapMasked_Data.txt', self.B0DeltaB0maps)
        
        params.GUImode = self.GUImodetemp
        params.sequence = self.sequencetemp
        params.datapath = self.datapathtemp
        
    def FieldMapB0Slice(self):
        print('Measuring B0 (Slice) field...')
        
        self.GUImodetemp = 0
        self.sequencetemp = 0
        self.datapathtemp = ''
        self.GUImodetemp = params.GUImode
        self.sequencetemp = params.sequence
        self.datapathtemp = params.datapath
        
        params.GUImode = 1
        params.sequence = 20
        params.datapath = 'rawdata/Tool_rawdata'
        
        self.TEtemp = 0
        self.TEtemp = params.TE
        params.TE = params.TE + 1
        
        seq.sequence_upload()
        proc.image_process()
        
        self.FieldMapB0_S2_raw = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S2 = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S2_raw[:,:] = params.img_pha[:,:]
        self.FieldMapB0_S2[:,:] = params.img_pha[:,:]
        
        for kk in range (10):
        
            for jj in range(int(self.FieldMapB0_S2.shape[1]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S2.shape[1]/2)+jj+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[1]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S2.shape[1]/2)-jj-1] - 2 * math.pi
            
            for jj in range(int(self.FieldMapB0_S2.shape[0]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)+jj+1,int(self.FieldMapB0_S2.shape[1]/2)-jj+ii+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S2.shape[0]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii-1] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii] - 2 * math.pi
                    if self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] + self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] > math.pi:
                        self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] = self.FieldMapB0_S2[int(self.FieldMapB0_S2.shape[0]/2)-jj-1,int(self.FieldMapB0_S2.shape[1]/2)+jj-ii+1] - 2 * math.pi
        
        time.sleep(params.TR/1000)
        
        params.TE = self.TEtemp
        
        seq.sequence_upload()
        proc.image_process()
        
        self.FieldMapB0_S1_raw = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S1 = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0])))
        self.FieldMapB0_S1_raw = params.img_pha
        self.FieldMapB0_S1 = params.img_pha
        
        for kk in range (10):
        
            for jj in range(int(self.FieldMapB0_S1.shape[1]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii-1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj+ii+1,int(self.FieldMapB0_S1.shape[1]/2)+jj+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[1]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii-1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj-ii+1,int(self.FieldMapB0_S1.shape[1]/2)-jj-1] - 2 * math.pi
            
            for jj in range(int(self.FieldMapB0_S1.shape[0]/2)-2):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)+jj+1,int(self.FieldMapB0_S1.shape[1]/2)-jj+ii+1] - 2 * math.pi
            for jj in range(int(self.FieldMapB0_S1.shape[0]/2)-1):
                for ii in range(1+jj*2):
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii-1] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii] - 2 * math.pi
                    if self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] + self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] > math.pi:
                        self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] = self.FieldMapB0_S1[int(self.FieldMapB0_S1.shape[0]/2)-jj-1,int(self.FieldMapB0_S1.shape[1]/2)+jj-ii+1] - 2 * math.pi

        params.B0DeltaB0map = (self.FieldMapB0_S2 - self.FieldMapB0_S1) / (2 * math.pi * 42.577 * (((params.TE + 1) - params.TE))/1000)
        params.B0DeltaB0mapmasked = np.matrix(np.zeros((params.B0DeltaB0map.shape[1],params.B0DeltaB0map.shape[0])))
        params.B0DeltaB0mapmasked[:,:] = params.B0DeltaB0map[:,:]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B0DeltaB0mapmasked[params.img_mag < self.img_max * 0.3] = np.nan
        
        self.FieldMapB0_pha_raw = np.concatenate((self.FieldMapB0_S1_raw,self.FieldMapB0_S2_raw),axis=1)
        np.savetxt('imagedata/FieldMap_B0_Phase_Raw_Data.txt', self.FieldMapB0_pha_raw)
        self.FieldMapB0_pha = np.concatenate((self.FieldMapB0_S1,self.FieldMapB0_S2),axis=1)
        np.savetxt('imagedata/FieldMap_B0_Phase_Data.txt', self.FieldMapB0_pha)
        self.B0DeltaB0maps = np.concatenate((params.img_mag,params.B0DeltaB0map,params.B0DeltaB0mapmasked),axis=1)
        np.savetxt('imagedata/FieldMap_B0_deltat1ms_Mag_Map_MapMasked_Data.txt', self.B0DeltaB0maps)
        
        params.GUImode = self.GUImodetemp
        params.sequence = self.sequencetemp
        params.datapath = self.datapathtemp

    def FieldMapB1(self):
        print('Measuring B1 field...')
        
        self.GUImodetemp = 0
        self.sequencetemp = 0
        self.datapathtemp = ''
        self.GUImodetemp = params.GUImode
        self.sequencetemp = params.sequence
        self.datapathtemp = params.datapath
        
        params.GUImode = 1
        params.sequence = 4
        params.datapath = 'rawdata/Tool_rawdata'
        
        self.flipangleamplitudetemp = 0
        self.flipangleamplitudetemp = params.flipangleamplitude
        
        seq.sequence_upload()
        proc.image_process()
        
        self.FieldMapB1_S1 = np.matrix(np.zeros((params.img_mag.shape[1],params.img_mag.shape[0])))
        self.FieldMapB1_S1[:,:] = params.img_mag[:,:]
        
        time.sleep(params.TR/1000)
        
        params.flipangleamplitude = params.flipangleamplitude * 2
        
        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB1_S2 = np.matrix(np.zeros((params.img_mag.shape[1],params.img_mag.shape[0])))
        self.FieldMapB1_S2[:,:] = params.img_mag[:,:]
        
        params.flipangleamplitude = self.flipangleamplitudetemp
        
        params.B1alphamap = np.arccos(self.FieldMapB1_S2 / (2 * self.FieldMapB1_S1)) * params.flipangleamplitude
        params.B1alphamapmasked = np.matrix(np.zeros((params.B1alphamap.shape[1],params.B1alphamap.shape[0])))
        params.B1alphamapmasked[:,:] = params.B1alphamap[:,:]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B1alphamapmasked[params.img_mag < self.img_max * 0.3] = np.nan
        
        self.FieldMapB1_mag = np.concatenate((self.FieldMapB1_S1,self.FieldMapB1_S2),axis=1)
        np.savetxt('imagedata/FieldMap_B1_Phase_Data.txt', self.FieldMapB1_mag)
        self.B1alphamaps = np.concatenate((params.img_mag,params.B1alphamap,params.B1alphamapmasked),axis=1)
        np.savetxt('imagedata/FieldMap_B1_alpha'+ str(params.flipangleamplitude) +'deg_Mag_Map_MapMasked_Data.txt', self.B1alphamaps)
        
        params.GUImode = self.GUImodetemp
        params.sequence = self.sequencetemp
        params.datapath = self.datapathtemp
        
    def FieldMapB1Slice(self):
        print('Measuring B1 (Slice) field...')
        
        self.GUImodetemp = 0
        self.sequencetemp = 0
        self.datapathtemp = ''
        self.GUImodetemp = params.GUImode
        self.sequencetemp = params.sequence
        self.datapathtemp = params.datapath
        
        params.GUImode = 1
        params.sequence = 20
        params.datapath = 'rawdata/Tool_rawdata'
        
        self.flipangleamplitudetemp = 0
        self.flipangleamplitudetemp = params.flipangleamplitude
        
        seq.sequence_upload()
        proc.image_process()
        
        self.FieldMapB1_S1 = np.matrix(np.zeros((params.img_mag.shape[1],params.img_mag.shape[0])))
        self.FieldMapB1_S1[:,:] = params.img_mag[:,:]
        
        time.sleep(params.TR/1000)
        
        params.flipangleamplitude = params.flipangleamplitude * 2
        
        seq.sequence_upload()
        proc.image_process()

        self.FieldMapB1_S2 = np.matrix(np.zeros((params.img_mag.shape[1],params.img_mag.shape[0])))
        self.FieldMapB1_S2[:,:] = params.img_mag[:,:]
        
        params.flipangleamplitude = self.flipangleamplitudetemp
        
        params.B1alphamap = np.arccos(self.FieldMapB1_S2 / (2 * self.FieldMapB1_S1)) * params.flipangleamplitude
        params.B1alphamapmasked = np.matrix(np.zeros((params.B1alphamap.shape[1],params.B1alphamap.shape[0])))
        params.B1alphamapmasked[:,:] = params.B1alphamap[:,:]
        self.img_max = np.max(np.amax(params.img_mag))
        params.B1alphamapmasked[params.img_mag < self.img_max * 0.3] = np.nan
        
        self.FieldMapB1_mag = np.concatenate((self.FieldMapB1_S1,self.FieldMapB1_S2),axis=1)
        np.savetxt('imagedata/FieldMap_B1_Phase_Data.txt', self.FieldMapB1_mag)
        self.B1alphamaps = np.concatenate((params.img_mag,params.B1alphamap,params.B1alphamapmasked),axis=1)
        np.savetxt('imagedata/FieldMap_B1_alpha'+ str(params.flipangleamplitude) +'deg_Mag_Map_MapMasked_Data.txt', self.B1alphamaps)
        
        params.GUImode = self.GUImodetemp
        params.sequence = self.sequencetemp
        params.datapath = self.datapathtemp
        
    def FieldMapGradient(self):
        print('Gradient tool started...')
        
        self.GUImodetemp = 0
        self.sequencetemp = 0
        self.datapathtemp = ''
        self.GUImodetemp = params.GUImode
        self.sequencetemp = params.sequence
        self.datapathtemp = params.datapath
        
        params.GUImode = 1
        params.sequence = 5
        params.datapath = 'rawdata/Tool_rawdata'
        
        seq.sequence_upload()
        proc.image_process()
        
        params.GUImode = self.GUImodetemp
        params.sequence = self.sequencetemp
        params.datapath = self.datapathtemp
        
    def FieldMapGradientSlice(self):
        print('Gradient (Slice) tool started...')
        
        self.GUImodetemp = 0
        self.sequencetemp = 0
        self.datapathtemp = ''
        self.GUImodetemp = params.GUImode
        self.sequencetemp = params.sequence
        self.datapathtemp = params.datapath
        
        params.GUImode = 1
        params.sequence = 21
        params.datapath = 'rawdata/Tool_rawdata'
        
        seq.sequence_upload()
        proc.image_process()
        
        params.GUImode = self.GUImodetemp
        params.sequence = self.sequencetemp
        params.datapath = self.datapathtemp
        

    def T1measurement_IR_FID(self):
        print('Measuring T1...')
        
        self.TItemp = 0
        self.TItemp = params.TI
        
        self.T1steps = np.linspace(params.TIstart,params.TIstop,params.TIsteps)
        params.T1values = np.matrix(np.zeros((2,params.TIsteps)))
        self.T1peakvalues = np.zeros(params.TIsteps)
        
        self.T1steps[0] = round(self.T1steps[0],1)
        params.TI = self.T1steps[0]
        seq.IR_FID_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_FID()
        proc.spectrum_process()
        proc.spectrum_analytics()
        time.sleep(params.TR/1000)
        
        for n in range(params.TIsteps):
            print(n+1, '/', params.TIsteps)
            self.T1steps[n] = round(self.T1steps[n],1)
            params.TI = self.T1steps[n]
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            seq.IR_FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_FID()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T1peakvalues[n] = params.peakvalue
            time.sleep(params.TR/1000)
            
        params.T1values[0,:] = self.T1steps
        params.T1values[1,:] = self.T1peakvalues
        
        params.TI = self.TItemp
        
        self.datatxt2 = np.matrix(np.zeros((params.TIsteps,2)))
        self.datatxt2 = np.transpose(params.T1values)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        print('T1 Data aquired!')
        
    def T1measurement_IR_SE(self):
        print('Measuring T1...')
        
        self.TItemp = 0
        self.TItemp = params.TI
        
        self.T1steps = np.linspace(params.TIstart,params.TIstop,params.TIsteps)
        params.T1values = np.matrix(np.zeros((2,params.TIsteps)))
        self.T1peakvalues = np.zeros(params.TIsteps)
        
        self.T1steps[0] = round(self.T1steps[0],1)
        params.TI = self.T1steps[0]
        seq.IR_SE_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE()
        proc.spectrum_process()
        proc.spectrum_analytics()
        time.sleep(params.TR/1000)
        
        for n in range(params.TIsteps):
            print(n+1, '/', params.TIsteps)
            self.T1steps[n] = round(self.T1steps[n],1)
            params.TI = self.T1steps[n]
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            seq.IR_SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T1peakvalues[n] = params.peakvalue
            time.sleep(params.TR/1000)
            
        params.T1values[0,:] = self.T1steps
        params.T1values[1,:] = self.T1peakvalues
        
        params.TI = self.TItemp
        
        self.datatxt2 = np.matrix(np.zeros((params.TIsteps,2)))
        self.datatxt2 = np.transpose(params.T1values)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        print('T1 Data aquired!')
        
    def T1process(self):
        print('Calculating T1...')
        self.procdata = np.genfromtxt(params.datapath + '.txt')
        params.T1values = np.transpose(self.procdata)
        
        params.T1xvalues = np.zeros(params.T1values.shape[1])
        params.T1yvalues1 = np.zeros(params.T1values.shape[1])
        params.T1yvalues2 = np.zeros(params.T1values.shape[1])
        params.T1xvalues[:] = params.T1values[0,:]
        params.T1yvalues1[:] = params.T1values[1,:]
        params.T1yvalues2[:] = params.T1values[1,:]
        
        self.minindex = np.argmin(params.T1yvalues1)
        
        if self.minindex >=1:
            params.T1yvalues2[0:self.minindex-1] = -params.T1yvalues1[0:self.minindex-1]
            
        self.T1ymax = np.max(params.T1yvalues2)

        # params.T1yvalues2[:] = np.log(self.T1ymax - params.T1yvalues2)
        params.T1yvalues2[:] = np.log(self.T1ymax - params.T1yvalues2)
        
        params.T1yvalues2[np.isinf(params.T1yvalues2)] = np.nan
        
        print(params.T1xvalues)
        print(params.T1yvalues2)

        params.T1linregres = linregress(params.T1xvalues[np.isnan(params.T1yvalues2) == False], params.T1yvalues2[np.isnan(params.T1yvalues2) == False])
        
        params.T1regyvalues2 = params.T1linregres.slope * params.T1xvalues + params.T1linregres.intercept
        
        params.T1 = round(-(1/params.T1linregres.slope),2)
        
        params.T1regyvalues1 = abs(self.T1ymax * (1-2*np.exp(-(params.T1xvalues/params.T1))))
        
        print(params.T1linregres)
        print('T1 calculated!')
        
    def T2measurement_SE(self):
        print('Measuring T2...')
        
        self.TEtemp = 0
        self.TEtemp = params.TE
        
        self.T2steps = np.linspace(params.TEstart,params.TEstop,params.TEsteps)
        params.T2values = np.matrix(np.zeros((2,params.TEsteps)))
        self.T2peakvalues = np.zeros(params.TEsteps)
        
        self.T2steps[0] = round(self.T2steps[0],1)
        params.TE = self.T2steps[0]
        seq.SE_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE()
        proc.spectrum_process()
        proc.spectrum_analytics()
        time.sleep(params.TR/1000)
        
        for n in range(params.TEsteps):
            print(n+1, '/', params.TEsteps)
            self.T2steps[n] = round(self.T2steps[n],1)
            params.TE = self.T2steps[n]
            params.frequency = params.centerfrequency
            params.saveFileParameter()
            seq.SE_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T2peakvalues[n] = params.peakvalue
            time.sleep(params.TR/1000)
            
        params.T2values[0,:] = self.T2steps
        params.T2values[1,:] = self.T2peakvalues
        
        params.TE = self.TEtemp
        
        self.datatxt2 = np.matrix(np.zeros((params.TEsteps,2)))
        self.datatxt2 = np.transpose(params.T2values)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        print('T2 Data aquired!')
            
    def T2measurement_SIR_FID(self):
        print('Measuring T2...')
        
        self.TEtemp = 0
        self.TEtemp = params.TE
        
        self.T2steps = np.linspace(params.TEstart,params.TEstop,params.TEsteps)
        params.T2values = np.matrix(np.zeros((2,params.TEsteps)))
        self.T2peakvalues = np.zeros(params.TEsteps)
        
        self.T2steps[0] = round(self.T2steps[0],1)
        params.TE = self.T2steps[0]
        params.frequency = params.centerfrequency
        params.saveFileParameter()
        seq.SIR_FID_setup()
        seq.Sequence_upload()
        seq.acquire_spectrum_SE()
        proc.spectrum_process()
        proc.spectrum_analytics()
        time.sleep(params.TR/1000)
        
        for n in range(params.TEsteps):
            print(n+1, '/', params.TEsteps)
            self.T2steps[n] = round(self.T2steps[n],1)
            params.TE = self.T2steps[n]
            seq.SIR_FID_setup()
            seq.Sequence_upload()
            seq.acquire_spectrum_SE()
            proc.spectrum_process()
            proc.spectrum_analytics()
            self.T2peakvalues[n] = params.peakvalue
            time.sleep(params.TR/1000)
            
        params.T2values[0,:] = self.T2steps
        params.T2values[1,:] = self.T2peakvalues
        
        params.TE = self.TEtemp
        
        self.datatxt2 = np.matrix(np.zeros((params.TEsteps,2)))
        self.datatxt2 = np.transpose(params.T2values)
        np.savetxt(params.datapath + '.txt', self.datatxt2)
        
        print('T2 Data aquired!')
        
    def T2process(self):
        print('Calculating T2...')
        self.procdata = np.genfromtxt(params.datapath + '.txt')
        params.T2values = np.transpose(self.procdata)
        
        params.T2xvalues = np.zeros(params.T2values.shape[1])
        params.T2yvalues = np.zeros(params.T2values.shape[1])
        params.T2xvalues[:] = params.T2values[0,:]
        params.T2yvalues[:] = np.log(params.T2values[1,:])
        
        params.T2linregres = linregress(params.T2xvalues, params.T2yvalues)

        params.T2regyvalues = params.T2linregres.slope * params.T2xvalues + params.T2linregres.intercept
        
        params.T2 = round(-(1/params.T2linregres.slope),2)
        
        print('T2 calculated!')
        
    def animation_image_process(self):
        
        self.kspaceanimate = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[1]), dtype = np.complex64))
        self.kspaceanimatetemp = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0])))
        self.animationimagetemp = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0])))
        params.animationimage = np.array(np.zeros((params.kspace.shape[0], params.kspace.shape[0], params.kspace.shape[0]*2)))
        
        self.kspace_centerx = int(params.kspace.shape[1]/2)
        self.kspace_centery = int(params.kspace.shape[0]/2)
        
        for n in range(params.kspace.shape[0]):
            self.kspaceanimate[n,:] = params.kspace[n,:]
            self.kspaceanimatetemp = np.abs(self.kspaceanimate[:,int(self.kspace_centerx-params.kspace.shape[0]/2*int(math.floor(params.kspace.shape[1]/params.kspace.shape[0]))):int(self.kspace_centerx+params.kspace.shape[0]/2*int(math.floor(params.kspace.shape[1]/params.kspace.shape[0]))):int(math.floor(params.kspace.shape[1]/params.kspace.shape[0]))])/np.amax(params.k_amp)
        
            #Image calculations
            I = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspaceanimate)))
            self.animationimagetemp[:,:] = np.abs(I[:,self.kspace_centerx-int(params.kspace.shape[0]/2*params.ROBWscaler):self.kspace_centerx+int(params.kspace.shape[0]/2*params.ROBWscaler)])
            self.animationimagetemp = self.animationimagetemp / np.amax(params.img_mag)
            #Store animation array
            params.animationimage[n,:,:] = np.concatenate((self.animationimagetemp[:,:],self.kspaceanimatetemp[:,:]),axis=1)  

proc = process()
