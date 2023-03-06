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
import pickle
from PyQt5.QtCore import QFile, QTextStream
from cycler import cycler

import breeze_resources


class Parameters:
    def __init__(self):
        file = QFile(":/light.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)

        self.stylesheet = stream.readAll()
        self.cycler = cycler(color=['#000000', '#0000BB', '#BB0000'])

        self.ip = []

    def var_init(self):
        print("Setting default parameters.")
        self.hosts = ['192.168.1.84']
        self.GUImode = 0
        self.sequence = 0
        self.sequencefile = ''
        self.datapath = ''
        self.frequency = 11.3
        self.frequencyoffset = 0
        self.frequencyoffsetsign = 0
        self.phaseoffset = 0
        self.phaseoffsetradmod100 = 0
        self.RFpulselength = 100
        self.RFpulseamplitude = 16384
        self.flipangetime = 90
        self.flipangeamplitude = 90
        self.flippulselength = 50
        self.flippulseamplitude = 16384
        self.RFattenuation = -15.00
        self.TS = 6
        self.ROBWscaler = 1
        self.TE = 15
        self.TI = 2
        self.TR = 500
        self.grad = [0, 0, 0, 0]
        self.Gradientorientation = [0, 1, 2, 3]
        self.imageorientation = 0
        self.nPE = 32
        self.frequencyrange = 250000
        self.samples = 50000
        self.sampledelay = 0.35
        self.spectrumdata = []
        self.dataTimestamp = ''
        self.timeaxis = []
        self.mag = []
        self.real = []
        self.imag = []
        self.freqencyaxis = []
        self.frequencyplotrange = 250000
        self.spectrumfft = []
        self.FWHM = 0
        self.peakvalue = 0
        self.noise = 0
        self.SNR = 0
        self.inhomogeneity = 0
        self.centerfrequency = 1
        self.kspace = []
        self.k_amp = []
        self.k_pha = []
        self.img = []
        self.img_mag = []
        self.img_pha = []
        self.ACstart = 11.25
        self.ACstop = 11.35
        self.ACstepwidth = 10000
        self.ACvalues = []
        self.Reffrequency = 11.31
        self.FAstart = -31.00
        self.FAstop = -1.00
        self.FAsteps = 10
        self.FAvalues = []
        self.RefRFattenuation = -15.00
        self.TIstart = 1
        self.TIstop = 2000
        self.TIsteps = 10
        self.T1values = []
        self.T1xvalues = []
        self.T1yvalues1 = []
        self.T1yvalues2 = []
        self.T1linregres = []
        self.T1regyvalues1 = []
        self.T1regyvalues2 = []
        self.T1 = 100
        self.TEstart = 4
        self.TEstop = 20
        self.TEsteps = 10
        self.T2values = []
        self.T2xvalues = []
        self.T2yvalues = []
        self.T2linregres = []
        self.T2regyvalues = []
        self.T2 = 10
        self.projaxis = []
        self.average = 0
        self.averagecount = 10
        self.imagplots = 0
        self.cutcenter = 0
        self.cutoutside = 0
        self.cutcentervalue = 0
        self.cutoutsidevalue = 0
        self.ustime = 0
        self.usphase = 0
        self.ustimeidx = 0
        self.usphaseidx = 0
        self.Gproj = [0, 0, 0]
        self.projx = []
        self.projy = []
        self.projz = []
        self.projectionangle = 0
        self.projectionangleradmod100 = 0
        self.GROamplitude = 2000
        self.GPEstep = 60
        self.GSamplitude = 1500
        self.GSPEstep = 60
        self.SPEsteps = 4
        self.Gdiffamplitude = 2000
        self.img_mag_diff = []
        self.crusheramplitude = 1000
        self.spoileramplitude = 2000
        self.GROpretime = 600
        self.GROpretimescaler = 1.00
        self.GSposttime = 200
        self.crushertime = 400
        self.spoilertime = 1000
        self.diffusiontime = 1000
        self.GROfcpretime1 = 0
        self.GROfcpretime2 = 0
        self.radialanglestep = 45
        self.radialanglestepradmod100 = 0
        self.lnkspacemag = 0
        self.autograd = 1
        self.FOV = 20.0
        self.slicethickness = 5.0
        self.gradsens = [33.5, 31.9, 32.5]
        self.autofreqoffset = 1
        self.sliceoffset = 0
        self.animationstep = 100
        self.animationimage = []
        self.ToolShimStart = -100
        self.ToolShimStop = 100
        self.ToolShimSteps = 20
        self.ToolShimChannel = [0, 0, 0, 0]
        self.STvalues = []
        

    def saveFile(self):  
        with open('parameters.pkl', 'wb') as file:
            pickle.dump([self.hosts, \
                         self.GUImode, \
                         self.sequence, \
                         self.sequencefile, \
                         self.datapath, \
                         self.frequency, \
                         self.frequencyoffset, \
                         self.frequencyoffsetsign, \
                         self.phaseoffset, \
                         self.phaseoffsetradmod100, \
                         self.RFpulselength, \
                         self.RFpulseamplitude, \
                         self.flipangetime, \
                         self.flipangeamplitude, \
                         self.flippulselength, \
                         self.flippulseamplitude, \
                         self.RFattenuation, \
                         self.TS, \
                         self.ROBWscaler, \
                         self.TE, \
                         self.TI, \
                         self.TR, \
                         self.grad, \
                         self.Gradientorientation, \
                         self.imageorientation, \
                         self.nPE, \
                         self.frequencyrange, \
                         self.samples, \
                         self.sampledelay, \
                         self.spectrumdata, \
                         self.dataTimestamp, \
                         self.timeaxis, \
                         self.mag, \
                         self.real, \
                         self.imag, \
                         self.freqencyaxis, \
                         self.frequencyplotrange, \
                         self.spectrumfft, \
                         self.FWHM, \
                         self.peakvalue, \
                         self.noise, \
                         self.SNR, \
                         self.inhomogeneity, \
                         self.centerfrequency, \
                         self.kspace, \
                         self.k_amp, \
                         self.k_pha, \
                         self.img, \
                         self.img_mag, \
                         self.img_pha, \
                         self.ACstart, \
                         self.ACstop, \
                         self.ACstepwidth, \
                         self.ACvalues, \
                         self.Reffrequency, \
                         self.FAstart, \
                         self.FAstop, \
                         self.FAsteps, \
                         self.FAvalues, \
                         self.RefRFattenuation, \
                         self.TIstart, \
                         self.TIstop, \
                         self.TIsteps, \
                         self.T1values, \
                         self.T1xvalues, \
                         self.T1yvalues1, \
                         self.T1yvalues2, \
                         self.T1linregres, \
                         self.T1regyvalues1, \
                         self.T1regyvalues2, \
                         self.T1, \
                         self.TEstart, \
                         self.TEstop, \
                         self.TEsteps, \
                         self.T2values, \
                         self.T2xvalues, \
                         self.T2yvalues, \
                         self.T2linregres, \
                         self.T2regyvalues, \
                         self.T2, \
                         self.projaxis, \
                         self.average, \
                         self.averagecount, \
                         self.imagplots, \
                         self.cutcenter, \
                         self.cutoutside, \
                         self.cutcentervalue, \
                         self.cutoutsidevalue, \
                         self.ustime, \
                         self.usphase, \
                         self.ustimeidx, \
                         self.usphaseidx, \
                         self.Gproj, \
                         self.projx, \
                         self.projy, \
                         self.projz, \
                         self.projectionangle, \
                         self.projectionangleradmod100, \
                         self.GROamplitude, \
                         self.GPEstep, \
                         self.GSamplitude, \
                         self.GSPEstep, \
                         self.SPEsteps, \
                         self.Gdiffamplitude, \
                         self.img_mag_diff, \
                         self.crusheramplitude, \
                         self.spoileramplitude, \
                         self.GROpretime, \
                         self.GROpretimescaler, \
                         self.GSposttime, \
                         self.crushertime, \
                         self.spoilertime, \
                         self.diffusiontime, \
                         self.GROfcpretime1, \
                         self.GROfcpretime2, \
                         self.radialanglestep, \
                         self.radialanglestepradmod100, \
                         self.lnkspacemag, \
                         self.autograd, \
                         self.FOV, \
                         self.slicethickness, \
                         self.gradsens, \
                         self.autofreqoffset, \
                         self.sliceoffset, \
                         self.animationstep, \
                         self.animationimage, \
                         self.ToolShimStart, \
                         self.ToolShimStop, \
                         self.ToolShimSteps, \
                         self.ToolShimChannel, \
                         self.STvalues], file)
       
        print("Parameters saved!")

    def loadParam(self):
        try:
            with open('parameters.pkl', 'rb') as file:
                self.hosts, \
                self.GUImode, \
                self.sequence, \
                self.sequencefile, \
                self.datapath, \
                self.frequency, \
                self.frequencyoffset, \
                self.frequencyoffsetsign, \
                self.phaseoffset, \
                self.phaseoffsetradmod100, \
                self.RFpulselength, \
                self.RFpulseamplitude, \
                self.flipangetime, \
                self.flipangeamplitude, \
                self.flippulselength, \
                self.flippulseamplitude, \
                self.RFattenuation, \
                self.TS, \
                self.ROBWscaler, \
                self.TE, \
                self.TI, \
                self.TR, \
                self.grad, \
                self.Gradientorientation, \
                self.imageorientation, \
                self.nPE, \
                self.frequencyrange, \
                self.samples, \
                self.sampledelay, \
                self.spectrumdata, \
                self.dataTimestamp, \
                self.timeaxis, \
                self.mag, \
                self.real, \
                self.imag, \
                self.freqencyaxis, \
                self.frequencyplotrange, \
                self.spectrumfft, \
                self.FWHM, \
                self.peakvalue, \
                self.noise, \
                self.SNR, \
                self.inhomogeneity, \
                self.centerfrequency, \
                self.kspace, \
                self.k_amp, \
                self.k_pha, \
                self.img, \
                self.img_mag, \
                self.img_pha, \
                self.ACstart, \
                self.ACstop, \
                self.ACstepwidth, \
                self.ACvalues, \
                self.Reffrequency, \
                self.FAstart, \
                self.FAstop, \
                self.FAsteps, \
                self.FAvalues, \
                self.RefRFattenuation, \
                self.TIstart, \
                self.TIstop, \
                self.TIsteps, \
                self.T1values, \
                self.T1xvalues, \
                self.T1yvalues1, \
                self.T1yvalues2, \
                self.T1linregres, \
                self.T1regyvalues1, \
                self.T1regyvalues2, \
                self.T1, \
                self.TEstart, \
                self.TEstop, \
                self.TEsteps, \
                self.T2values, \
                self.T2xvalues, \
                self.T2yvalues, \
                self.T2linregres, \
                self.T2regyvalues, \
                self.T2, \
                self.projaxis, \
                self.average, \
                self.averagecount, \
                self.imagplots, \
                self.cutcenter, \
                self.cutoutside, \
                self.cutcentervalue, \
                self.cutoutsidevalue, \
                self.ustime, \
                self.usphase, \
                self.ustimeidx, \
                self.usphaseidx, \
                self.Gproj, \
                self.projx, \
                self.projy, \
                self.projz, \
                self.projectionangle, \
                self.projectionangleradmod100, \
                self.GROamplitude, \
                self.GPEstep, \
                self.GSamplitude, \
                self.GSPEstep, \
                self.SPEsteps, \
                self.Gdiffamplitude, \
                self.img_mag_diff, \
                self.crusheramplitude, \
                self.spoileramplitude, \
                self.GROpretime, \
                self.GROpretimescaler, \
                self.GSposttime, \
                self.crushertime, \
                self.spoilertime, \
                self.diffusiontime, \
                self.GROfcpretime1, \
                self.GROfcpretime2, \
                self.radialanglestep, \
                self.radialanglestepradmod100, \
                self.lnkspacemag, \
                self.autograd, \
                self.FOV, \
                self.slicethickness, \
                self.gradsens, \
                self.autofreqoffset, \
                self.sliceoffset, \
                self.animationstep, \
                self.animationimage, \
                self.ToolShimStart, \
                self.ToolShimStop, \
                self.ToolShimSteps, \
                self.ToolShimChannel, \
                self.STvalues = pickle.load(file)
             
                print("Internal GUI parameter successfully restored from file.")
                
        except:
            print("Parameter could not have been restored, setting default.")
            self.var_init()

    def dispVars(self):
        print("Parameters to save:")
        print("GUImode:\t\t\t", self.GUImode)
        print("Sequence:\t\t\t", self.sequence)
        print("Frequency:\t\t\t", self.frequency, "MHz")
        print("RF Pulselength:\t\t\t", self.RFpulselength, "µs")
        print("RF Attenuation:\t\t\t", self.RFattenuation, "dB")
        print("Sampling Time TS:\t\t", self.TS, "ms")
        print("Readout BW scaler:\t\t", self.ROBWscaler)
        print("Echo Time TE:\t\t\t",self.TE, "ms")
        print("Inversion Time TI:\t\t",self.TI, "ms")
        print("Repetition Time TR:\t\t", self.TR, "ms")
        print("Gradients (x, y, z, z2):\t", self.grad, "mA")
        print("Gradient Orientation:\t\t", self.Gradientorientation)
        print("Image Resolution:\t\t", self.nPE)
        
params = Parameters()
