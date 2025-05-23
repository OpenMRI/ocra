################################################################################
#
# Author: Marcus Prier
# Date: 2025
#
################################################################################

import pickle
import json
from PyQt5.QtCore import QFile, QTextStream
from cycler import cycler

import breeze_resources


class Parameters:
    def __init__(self):
        self.GUIthemestr = ['light', 'dark']
        file = QFile(':/' + self.GUIthemestr[0] + '.qss')
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        self.stylesheet = stream.readAll()
        self.cycler = cycler(color=['#000000', '#0000BB', '#BB0000'])

        self.ip = []

    def var_init(self):
        print('Setting default parameters.')
        self.hosts = ['192.168.1.84']
        self.GUItheme = 1
        self.connectionmode = 0
        self.GUImode = 0
        self.sequence = 0
        self.sequencefile = ''
        self.datapath = ''
        self.frequency = 11.3
        self.autorecenter = 1
        self.autodataprocess = 1
        self.frequencyoffset = 0
        self.frequencyoffsetsign = 0
        self.phaseoffset = 0
        self.phaseoffsetradmod100 = 0
        self.RFpulselength = 100
        self.RFpulseamplitude = 16384
        self.flipangletime = 90
        self.flipangleamplitude = 90
        self.flippulselength = 50
        self.flippulseamplitude = 16384
        self.RFattenuation = -15.00
        self.rx1 = 1
        self.rx2 = 0
        self.rxmode = 1
        self.RXscaling = 1280 # 20480 Exp binaries 0.0000762939
        self.TS = 6
        self.ROBWscaler = 1
        self.TE = 12
        self.TI = 1700
        self.SIR_TE = 10
        self.TR = 500
        self.grad = [0, 0, 0, 0]
        self.Gradientorientation = [0, 1, 2, 3]
        self.imageorientation = 2
        self.imageresolution = 2
        self.nPE = 32
        self.frequencyrange = 250000
        self.samples = 50000
        self.sampledelay = 0.344
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
        self.img_st = []
        self.img_st_mag = []
        self.img_st_pha = []
        self.ACstart = 11.2
        self.ACstop = 11.4
        self.ACstepwidth = 5000
        self.ACvalues = []
        self.Reffrequency = 11.31
        self.FAstart = -31.00
        self.FAstop = -1.00
        self.FAsteps = 30
        self.FAvalues = []
        self.RefRFattenuation = -15.00
        self.TIstart = 400
        self.TIstop = 10000
        self.TIsteps = 20
        self.T1values = []
        self.T1xvalues = []
        self.T1yvalues1 = []
        self.T1yvalues2 = []
        self.T1linregres = []
        self.T1regyvalues1 = []
        self.T1regyvalues2 = []
        self.T1 = 100
        self.T1stepsimg = []
        self.T1img_mag = []
        self.T1imgvalues = []
        self.TEstart = 10
        self.TEstop = 1000
        self.TEsteps = 20
        self.T2values = []
        self.T2xvalues = []
        self.T2yvalues = []
        self.T2linregres = []
        self.T2regyvalues = []
        self.T2 = 10
        self.T2stepsimg = []
        self.T2img_mag = []
        self.T2imgvalues = []
        self.projaxis = []
        self.average = 0
        self.average_complex = 1
        self.averagecount = 10
        self.imagplots = 0
        self.cutcirc = 0
        self.cutrec = 0
        self.cutcenter = 0
        self.cutoutside = 0
        self.cutcentervalue = 20
        self.cutoutsidevalue = 70
        self.usmethode = 1
        self.ustime = 0
        self.usphase = 0
        self.ustimeidx = 2
        self.usphaseidx = 2
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
        self.radialosfactor = 2
        self.radialanglestepradmod100 = 0
        self.lnkspacemag = 0
        self.autograd = 1
        self.FOV = 16.0
        self.slicethickness = 5.0
        self.gradsens = [35.0, 32.0, 36.0]
        self.gradnominal = [10.0, 10.0, 10.0]
        self.gradmeasured = [10.0, 10.0, 10.0]
        self.gradsenstool = [33.5, 31.9, 32.5]
        self.autofreqoffset = 1
        self.sliceoffset = 0
        self.animationstep = 100
        self.animationimage = []
        self.ToolShimStart = -400
        self.ToolShimStop = 400
        self.ToolShimSteps = 20
        self.ToolShimChannel = [0, 0, 0, 0]
        self.ToolAutoShimMode = 0
        self.STvalues = []
        self.AutoSTvalues = []
        self.STgrad = []
        self.B0DeltaB0map = []
        self.B0DeltaB0mapmasked = []
        self.B1alphamap = []
        self.B1alphamapmasked = []
        self.imagefilter = 1
        self.signalmask = 0.5
        self.SAR_enable = 0
        self.SAR_limit = 1
        self.SAR_6mlimit = 1
        self.SAR_peak_limit = 1
        self.SAR_status = 0
        self.SAR_LOG_counter = 0
        self.SAR_cal_raw =[]
        self.SAR_cal_mean = []
        self.SAR_cal_start=[]
        self.SAR_cal_end=[]
        self.SAR_cal_lookup=[]
        self.SAR_power_unit = 'mW'
        self.SAR_max_power = 15
        self.headerfileformat = 1
        self.motor_enable = 1
        self.motor_available = 0
        self.motor_port = []
        self.motor_axis_limit_negative = 0
        self.motor_axis_limit_positive = 195
        self.motor_movement_direction = 0
        self.motor_actual_position = 0
        self.motor_goto_position = 0
        self.motor_start_position = 0
        self.motor_end_position = 100
        self.motor_total_image_length = 100
        self.motor_movement_step = 10
        self.motor_image_count = 11
        self.motor_current_image_count = 0
        self.motor_settling_time = 1.0
        self.motor_AC_position = 50
        self.motor_AC_position_center = 1
        self.motor_AC_inbetween = 1
        self.motor_AC_inbetween_step = 1
        self.single_plot = 1
        self.ernstanglecalc_T1 = 1700
        self.ernstanglecalc_TR = 500
        self.ernstanglecalc_EA = 90
        self.imagecolormap = 'viridis'
        self.imageminimum = 0.0
        self.imagemaximum = 1.0
        self.measurement_time_dialog = 0
        self.toolautosequence = 0
        self.image_grid = 0
        self.projection3D = 0

    def saveFileParameter(self):  
        with open('parameters.pkl', 'wb') as file:
            pickle.dump([self.hosts, \
                         self.GUItheme, \
                         self.connectionmode, \
                         self.GUImode, \
                         self.sequence, \
                         self.sequencefile, \
                         self.datapath, \
                         self.frequency, \
                         self.autorecenter, \
                         self.autodataprocess, \
                         self.frequencyoffset, \
                         self.frequencyoffsetsign, \
                         self.phaseoffset, \
                         self.phaseoffsetradmod100, \
                         self.RFpulselength, \
                         self.RFpulseamplitude, \
                         self.flipangletime, \
                         self.flipangleamplitude, \
                         self.flippulselength, \
                         self.flippulseamplitude, \
                         self.RFattenuation, \
                         self.rx1, \
                         self.rx2, \
                         self.rxmode, \
                         self.RXscaling, \
                         self.TS, \
                         self.ROBWscaler, \
                         self.TE, \
                         self.TI, \
                         self.SIR_TE, \
                         self.TR, \
                         self.grad, \
                         self.Gradientorientation, \
                         self.imageorientation, \
                         self.imageresolution, \
                         self.nPE, \
                         self.frequencyrange, \
                         self.samples, \
                         self.sampledelay, \
                         self.dataTimestamp, \
                         self.timeaxis, \
                         self.frequencyplotrange, \
                         self.FWHM, \
                         self.peakvalue, \
                         self.noise, \
                         self.SNR, \
                         self.inhomogeneity, \
                         self.centerfrequency, \
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
                         self.T1, \
                         self.T1stepsimg, \
                         self.TEstart, \
                         self.TEstop, \
                         self.TEsteps, \
                         self.T2, \
                         self.T2stepsimg, \
                         self.projaxis, \
                         self.average, \
                         self.average_complex, \
                         self.averagecount, \
                         self.imagplots, \
                         self.cutcirc, \
                         self.cutrec, \
                         self.cutcenter, \
                         self.cutoutside, \
                         self.cutcentervalue, \
                         self.cutoutsidevalue, \
                         self.usmethode, \
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
                         self.radialosfactor, \
                         self.radialanglestepradmod100, \
                         self.lnkspacemag, \
                         self.autograd, \
                         self.FOV, \
                         self.slicethickness, \
                         self.gradsens, \
                         self.gradnominal, \
                         self.gradmeasured, \
                         self.gradsenstool, \
                         self.autofreqoffset, \
                         self.sliceoffset, \
                         self.animationstep, \
                         self.animationimage, \
                         self.ToolShimStart, \
                         self.ToolShimStop, \
                         self.ToolShimSteps, \
                         self.ToolShimChannel, \
                         self.ToolAutoShimMode, \
                         self.STvalues, \
                         self.AutoSTvalues, \
                         self.STgrad, \
                         self.imagefilter, \
                         self.signalmask, \
                         self.SAR_enable, \
                         self.SAR_limit, \
                         self.SAR_6mlimit, \
                         self.SAR_peak_limit, \
                         self.SAR_LOG_counter, \
                         self.SAR_cal_raw,\
                         self.SAR_cal_mean,\
                         self.SAR_cal_start,\
                         self.SAR_cal_end,\
                         self.SAR_cal_lookup,\
                         self.SAR_power_unit,\
                         self.SAR_status,\
                         self.SAR_max_power,\
                         self.headerfileformat, \
                         self.motor_enable, \
                         self.motor_available, \
                         self.motor_port, \
                         self.motor_axis_limit_negative, \
                         self.motor_axis_limit_positive, \
                         self.motor_movement_direction, \
                         self.motor_actual_position, \
                         self.motor_goto_position, \
                         self.motor_start_position, \
                         self.motor_end_position, \
                         self.motor_total_image_length, \
                         self.motor_movement_step, \
                         self.motor_image_count, \
                         self.motor_current_image_count, \
                         self.motor_settling_time, \
                         self.motor_AC_position, \
                         self.motor_AC_position_center, \
                         self.motor_AC_inbetween, \
                         self.motor_AC_inbetween_step, \
                         self.single_plot, \
                         self.ernstanglecalc_T1, \
                         self.ernstanglecalc_TR, \
                         self.ernstanglecalc_EA, \
                         self.imagecolormap, \
                         self.imageminimum, \
                         self.imagemaximum, \
                         self.measurement_time_dialog, \
                         self.toolautosequence, \
                         self.image_grid, \
                         self.projection3D], file)
       
        print('Parameters saved!')
        
    def saveFileData(self):  
        with open('data.pkl', 'wb') as file:
            pickle.dump([self.spectrumdata, \
                         self.mag, \
                         self.real, \
                         self.imag, \
                         self.freqencyaxis, \
                         self.spectrumfft, \
                         self.kspace, \
                         self.k_amp, \
                         self.k_pha, \
                         self.img, \
                         self.img_mag, \
                         self.img_pha, \
                         self.img_st, \
                         self.img_st_mag, \
                         self.img_st_pha, \
                         self.T1values, \
                         self.T1xvalues, \
                         self.T1yvalues1, \
                         self.T1yvalues2, \
                         self.T1linregres, \
                         self.T1regyvalues1, \
                         self.T1regyvalues2, \
                         self.T1img_mag, \
                         self.T1imgvalues, \
                         self.T2values, \
                         self.T2xvalues, \
                         self.T2yvalues, \
                         self.T2linregres, \
                         self.T2regyvalues, \
                         self.T2img_mag, \
                         self.T2imgvalues, \
                         self.img_mag_diff, \
                         self.B0DeltaB0map, \
                         self.B0DeltaB0mapmasked, \
                         self.B1alphamap, \
                         self.B1alphamapmasked], file)
       
        print('Data saved!')

    def saveSarCal(self):  
        with open('sarcal.pkl', 'wb') as file:
            pickle.dump([self.SAR_cal_raw], file)
       
        print('SAR data saved!')
        
    def loadSarCal(self):
        try:
            with open('sarcal.pkl', 'rb') as file:
                self.SAR_cal_raw = pickle.load(file)
                print('SAR data successfully restored from file.')
                
        except:
            print('SAR data could not have been restored.')

    def loadParam(self):
        try:
            with open('parameters.pkl', 'rb') as file:
                self.hosts, \
                self.GUItheme, \
                self.connectionmode, \
                self.GUImode, \
                self.sequence, \
                self.sequencefile, \
                self.datapath, \
                self.frequency, \
                self.autorecenter, \
                self.autodataprocess, \
                self.frequencyoffset, \
                self.frequencyoffsetsign, \
                self.phaseoffset, \
                self.phaseoffsetradmod100, \
                self.RFpulselength, \
                self.RFpulseamplitude, \
                self.flipangletime, \
                self.flipangleamplitude, \
                self.flippulselength, \
                self.flippulseamplitude, \
                self.RFattenuation, \
                self.rx1, \
                self.rx2, \
                self.rxmode, \
                self.RXscaling, \
                self.TS, \
                self.ROBWscaler, \
                self.TE, \
                self.TI, \
                self.SIR_TE, \
                self.TR, \
                self.grad, \
                self.Gradientorientation, \
                self.imageorientation, \
                self.imageresolution, \
                self.nPE, \
                self.frequencyrange, \
                self.samples, \
                self.sampledelay, \
                self.dataTimestamp, \
                self.timeaxis, \
                self.frequencyplotrange, \
                self.FWHM, \
                self.peakvalue, \
                self.noise, \
                self.SNR, \
                self.inhomogeneity, \
                self.centerfrequency, \
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
                self.T1, \
                self.T1stepsimg, \
                self.TEstart, \
                self.TEstop, \
                self.TEsteps, \
                self.T2, \
                self.T2stepsimg, \
                self.projaxis, \
                self.average, \
                self.average_complex, \
                self.averagecount, \
                self.imagplots, \
                self.cutcirc, \
                self.cutrec, \
                self.cutcenter, \
                self.cutoutside, \
                self.cutcentervalue, \
                self.cutoutsidevalue, \
                self.usmethode, \
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
                self.radialosfactor, \
                self.radialanglestepradmod100, \
                self.lnkspacemag, \
                self.autograd, \
                self.FOV, \
                self.slicethickness, \
                self.gradsens, \
                self.gradnominal, \
                self.gradmeasured, \
                self.gradsenstool, \
                self.autofreqoffset, \
                self.sliceoffset, \
                self.animationstep, \
                self.animationimage, \
                self.ToolShimStart, \
                self.ToolShimStop, \
                self.ToolShimSteps, \
                self.ToolShimChannel, \
                self.ToolAutoShimMode, \
                self.STvalues, \
                self.AutoSTvalues, \
                self.STgrad, \
                self.imagefilter, \
                self.signalmask, \
                self.SAR_enable, \
                self.SAR_limit, \
                self.SAR_6mlimit, \
                self.SAR_peak_limit, \
                self.SAR_LOG_counter, \
                self.SAR_cal_raw,\
                self.SAR_cal_mean,\
                self.SAR_cal_start,\
                self.SAR_cal_end,\
                self.SAR_cal_lookup,\
                self.SAR_power_unit,\
                self.SAR_status,\
                self.SAR_max_power,\
                self.headerfileformat, \
                self.motor_enable, \
                self.motor_available, \
                self.motor_port , \
                self.motor_axis_limit_negative, \
                self.motor_axis_limit_positive, \
                self.motor_movement_direction, \
                self.motor_actual_position, \
                self.motor_goto_position, \
                self.motor_start_position, \
                self.motor_end_position, \
                self.motor_total_image_length, \
                self.motor_movement_step, \
                self.motor_image_count, \
                self.motor_current_image_count, \
                self.motor_settling_time, \
                self.motor_AC_position, \
                self.motor_AC_position_center, \
                self.motor_AC_inbetween, \
                self.motor_AC_inbetween_step, \
                self.single_plot, \
                self.ernstanglecalc_T1, \
                self.ernstanglecalc_TR, \
                self.ernstanglecalc_EA, \
                self.imagecolormap, \
                self.imageminimum, \
                self.imagemaximum, \
                self.measurement_time_dialog, \
                self.toolautosequence, \
                self.image_grid, \
                self.projection3D = pickle.load(file)
             
                print('Internal GUI parameter successfully restored from file.')
                
        except:
            print('Parameter could not have been restored, setting default.')
            self.var_init()
            
    def loadData(self):
        try:
            with open('data.pkl', 'rb') as file:
                self.spectrumdata, \
                self.mag, \
                self.real, \
                self.imag, \
                self.freqencyaxis, \
                self.spectrumfft, \
                self.kspace, \
                self.k_amp, \
                self.k_pha, \
                self.img, \
                self.img_mag, \
                self.img_pha, \
                self.img_st, \
                self.img_st_mag, \
                self.img_st_pha, \
                self.T1values, \
                self.T1xvalues, \
                self.T1yvalues1, \
                self.T1yvalues2, \
                self.T1linregres, \
                self.T1regyvalues1, \
                self.T1regyvalues2, \
                self.T1img_mag, \
                self.T1imgvalues, \
                self.T2values, \
                self.T2xvalues, \
                self.T2yvalues, \
                self.T2linregres, \
                self.T2regyvalues, \
                self.T2img_mag, \
                self.T2imgvalues, \
                self.img_mag_diff, \
                self.B0DeltaB0map, \
                self.B0DeltaB0mapmasked, \
                self.B1alphamap, \
                self.B1alphamapmasked = pickle.load(file)
             
                print('Internal GUI Data successfully restored from file.')
                
        except:
            print('Data could not have been restored, setting default.')
            self.var_init()
        
    def save_header_file_txt(self):
        file = open(params.datapath + '_Header.txt','w')

        file.write('Hosts: ' + str(self.hosts) + '\n')
        # file.write(': ' + str(self.GUItheme) + '\n')
        file.write('Connection mode: ' + str(self.connectionmode) + '\n')
        file.write('GUI mode: ' + str(self.GUImode) + '\n')
        file.write('Sequence: ' + str(self.sequence) + '\n')
        file.write('Sequence file: ' + str(self.sequencefile) + '\n')
        file.write('Data path: ' + str(self.datapath) + '\n')
        file.write('Frequency [MHz]: ' + str(self.frequency) + '\n')
        file.write('Auto recenter: ' + str(self.autorecenter) + '\n')
        # file.write('Auto data process: ' + str(self.autodataprocess) + '\n')
        if self.frequencyoffsetsign == 1:
            file.write('RF frequency offset [Hz]: -' + str(self.frequencyoffset) + '\n')
        else:
            file.write('RF frequency offset [Hz]: ' + str(self.frequencyoffset) + '\n')
        file.write('RF phase offset [°]: ' + str(self.phaseoffset) + '\n')
        file.write('RF phase offset [rad]: ' + str(self.phaseoffsetradmod100) + '\n')
        file.write('RF pulse length [µs]: ' + str(self.RFpulselength) + '\n')
        file.write('RF pulse amplitude: ' + str(self.RFpulseamplitude) + '\n')
        file.write('Flip angle (time) [°]: ' + str(self.flipangletime) + '\n')
        file.write('Flip angle (amplitude) [°]: ' + str(self.flipangleamplitude) + '\n')
        file.write('Flip pulse length [µs]: ' + str(self.flippulselength) + '\n')
        file.write('Flip pulse amplitude: ' + str(self.flippulseamplitude) + '\n')
        file.write('RF attenuation [dB]: ' + str(self.RFattenuation) + '\n')
        file.write('RX port 1: ' + str(self.rx1) + '\n')
        file.write('RX port 2: ' + str(self.rx2) + '\n')
        file.write('RX mode: ' + str(self.rxmode) + '\n')
        file.write('RX scaling: ' + str(self.RXscaling) + '\n')
        file.write('TS [ms]: ' + str(self.TS) + '\n')
        file.write('Readout bandwidth scaling: ' + str(self.ROBWscaler) + '\n')
        file.write('TE [ms]: ' + str(self.TE) + '\n')
        file.write('TI [ms]: ' + str(self.TI) + '\n')
        file.write('SIR TE [ms]: ' + str(self.SIR_TE) + '\n')
        file.write('TR [ms]: ' + str(self.TR) + '\n')
        file.write('Shim values [mA]: ' + str(self.grad) + '\n')
        file.write('Gradient orientation: ' + str(self.Gradientorientation) + '\n')
        if self.imageorientation == 0:
            file.write('Image orientation: XY\n')
        elif self.imageorientation == 1:
            file.write('Image orientation: YZ\n')
        elif self.imageorientation == 2:
            file.write('Image orientation: ZX\n')
        elif self.imageorientation == 3:
            file.write('Image orientation: YX\n')
        elif self.imageorientation == 4:
            file.write('Image orientation: ZY\n')
        else:
            file.write('Image orientation: XZ\n')
        file.write('Image resolution index: ' + str(self.imageresolution) + '\n')
        file.write('Image resolution [pixel]: ' + str(self.nPE) + '\n')
        file.write('Frequency range [Hz]: ' + str(self.frequencyrange) + '\n')
        file.write('Samples: ' + str(self.samples) + '\n')
        file.write('Sampledelay: ' + str(self.sampledelay) + '\n')
        file.write('Timestamp: ' + str(self.dataTimestamp) + '\n')
        # file.write(': ' + str(self.timeaxis) + '\n')
        # file.write(': ' + str(self.frequencyplotrange) + '\n')
        # file.write(': ' + str(self.FWHM) + '\n')
        # file.write(': ' + str(self.peakvalue) + '\n')
        # file.write(': ' + str(self.noise) + '\n')
        # file.write(': ' + str(self.SNR) + '\n')
        # file.write(': ' + str(self.inhomogeneity) + '\n')
        # file.write(': ' + str(self.centerfrequency) + '\n')
        # file.write(': ' + str(self.ACstart) + '\n')
        # file.write(': ' + str(self.ACstop) + '\n')
        # file.write(': ' + str(self.ACstepwidth) + '\n')
        # file.write(': ' + str(self.ACvalues) + '\n')
        # file.write(': ' + str(self.Reffrequency) + '\n')
        # file.write(': ' + str(self.FAstart) + '\n')
        # file.write(': ' + str(self.FAstop) + '\n')
        # file.write(': ' + str(self.FAsteps) + '\n')
        # file.write(': ' + str(self.FAvalues) + '\n')
        # file.write(': ' + str(self.RefRFattenuation) + '\n')
        file.write('TI start [ms]: ' + str(self.TIstart) + '\n')
        file.write('TI stop [ms]: ' + str(self.TIstop) + '\n')
        file.write('TI steps: ' + str(self.TIsteps) + '\n')
        # file.write(': ' + str(self.T1) + '\n')
        # file.write(': ' + str(self.T1stepsimg) + '\n')
        file.write('TE start [ms]: ' + str(self.TEstart) + '\n')
        file.write('TE stop [ms]: ' + str(self.TEstop) + '\n')
        file.write('TE steps: ' + str(self.TEsteps) + '\n')
        # file.write(': ' + str(self.T2) + '\n')
        # file.write(': ' + str(self.T2stepsimg) + '\n')
        file.write('Projection axes: ' + str(self.projaxis) + '\n')
        file.write('Average: ' + str(self.average) + '\n')
        file.write('Average complex: ' + str(self.average_complex) + '\n')
        file.write('Number of averages: ' + str(self.averagecount) + '\n')
        # file.write(': ' + str(self.imagplots) + '\n')
        # file.write(': ' + str(self.cutcirc) + '\n')
        # file.write(': ' + str(self.cutrec) + '\n')
        # file.write(': ' + str(self.cutcenter) + '\n')
        # file.write(': ' + str(self.cutoutside) + '\n')
        # file.write(': ' + str(self.cutcentervalue) + '\n')
        # file.write(': ' + str(self.cutoutsidevalue) + '\n')
        # file.write(': ' + str(self.usmethode) + '\n')
        # file.write(': ' + str(self.ustime) + '\n')
        # file.write(': ' + str(self.usphase) + '\n')
        # file.write(': ' + str(self.ustimeidx) + '\n')
        # file.write(': ' + str(self.usphaseidx) + '\n')
        file.write('Projection gradient amplitude [mA]: ' + str(self.Gproj) + '\n')
        # file.write(': ' + str(self.projx) + '\n')
        # file.write(': ' + str(self.projy) + '\n')
        # file.write(': ' + str(self.projz) + '\n')
        file.write('Projection angle [°]: ' + str(self.projectionangle) + '\n')
        file.write('Projection angle [rad]: ' + str(self.projectionangleradmod100) + '\n')
        file.write('Readout gradient amplitude [mA]: ' + str(self.GROamplitude) + '\n')
        file.write('Phase gradient step amplitude [mA]: ' + str(self.GPEstep) + '\n')
        file.write('Slice gradient amplitude [mA]: ' + str(self.GSamplitude) + '\n')
        file.write('3D phase gradient step amplitude [mA]:: ' + str(self.GSPEstep) + '\n')
        file.write('3D phase steps: ' + str(self.SPEsteps) + '\n')
        file.write('Diffusion gradient amplitude [mA]: ' + str(self.Gdiffamplitude) + '\n')
        file.write('Crusher gradient amplitude [mA]: ' + str(self.crusheramplitude) + '\n')
        file.write('Spoiler gradient amplitude [mA]: ' + str(self.spoileramplitude) + '\n')
        file.write('Readout gradient prephaser duration [µs]: ' + str(self.GROpretime) + '\n')
        file.write('Readout gradient prephaser duration scaling: ' + str(self.GROpretimescaler) + '\n')
        file.write('Slice gradient rephaser time [µs]: ' + str(self.GSposttime) + '\n')
        file.write('Crusher gradient duration [µs]: ' + str(self.crushertime) + '\n')
        file.write('Spoiler gradient duration [µs]: ' + str(self.spoilertime) + '\n')
        file.write('Diffusion gradient duration [µs]: ' + str(self.diffusiontime) + '\n')
        file.write('Fluid compensation readout gradient prephaser 1 duration [µs]: ' + str(self.GROfcpretime1) + '\n')
        file.write('Fluid compensation readout gradient prephaser 2 duration [µs]: ' + str(self.GROfcpretime2) + '\n')
        file.write('Radial angle [°]: ' + str(self.radialanglestep) + '\n')
        file.write('Radial oversampling factor: ' + str(self.radialosfactor) + '\n')
        file.write('Radial angle [rad]: ' + str(self.radialanglestepradmod100) + '\n')
        # file.write(': ' + str(self.lnkspacemag) + '\n')
        file.write('Auto gradients: ' + str(self.autograd) + '\n')
        file.write('FOV [mm]: ' + str(self.FOV) + '\n')
        file.write('Slice/Slab thickness [mm]: ' + str(self.slicethickness) + '\n')
        file.write('Gradient sensitivity [mT/m/A]: ' + str(self.gradsens) + '\n')
        # file.write(': ' + str(self.gradnominal) + '\n')
        # file.write(': ' + str(self.gradmeasured) + '\n')
        # file.write(': ' + str(self.gradsenstool) + '\n')
        file.write('Auto frequency offset: ' + str(self.autofreqoffset) + '\n')
        file.write('Slice offset [mm]: ' + str(self.sliceoffset) + '\n')
        # file.write(': ' + str(self.animationstep) + '\n')
        # file.write(': ' + str(self.animationimage) + '\n')
        # file.write(': ' + str(self.ToolShimStart) + '\n')
        # file.write(': ' + str(self.ToolShimStop) + '\n')
        # file.write(': ' + str(self.ToolShimSteps) + '\n')
        # file.write(': ' + str(self.ToolShimChannel) + '\n')
        # file.write(': ' + str(self.ToolAutoShimMode) + '\n')
        # file.write(': ' + str(self.STvalues) + '\n')
        # file.write(': ' + str(self.AutoSTvalues) + '\n')
        # file.write(': ' + str(self.STgrad) + '\n')
        # file.write(': ' + str(self.imagefilter) + '\n')
        # file.write(': ' + str(self.signalmask))
        file.write('SAR enable: ' + str(self.SAR_enable) + '\n')
        file.write('SAR limit [W]: ' + str(self.SAR_limit) + '\n')
        file.write('SAR status: ' + str(self.SAR_status) + '\n')
        if self.headerfileformat == 0:
            file.write('Header File Format: .txt\n')
        elif self.headerfileformat == 1:
            file.write('Header File Format: .json\n')
        file.write('Motor enable: ' + str(self.motor_enable) + '\n')
        file.write('Motor available: ' + str(self.motor_available) + '\n')
        file.write('Motor COM Port: ' + str(self.motor_port) + '\n')
        file.write('Motor axis limit negative [mm]: ' + str(self.motor_axis_limit_negative) + '\n')
        file.write('Motor axis limit positive [mm]: ' + str(self.motor_axis_limit_positive) + '\n')
        file.write('Motor movement direction: ' + str(self.motor_movement_direction) + '\n')
        file.write('Motor actual position [mm]: ' + str(self.motor_actual_position) + '\n')
        file.write('Motor goto position [mm]: ' + str(self.motor_goto_position) + '\n')
        file.write('Motor start position [mm]: ' + str(self.motor_start_position) + '\n')
        file.write('Motor end position [mm]: ' + str(self.motor_end_position) + '\n')
        file.write('Motor total image length [mm]: ' + str(self.motor_total_image_length) + '\n')
        file.write('Motor movement step [mm]: ' + str(self.motor_movement_step) + '\n')
        file.write('Motor image count: ' + str(self.motor_image_count) + '\n')
        file.write('Motor current image count: ' + str(self.motor_current_image_count) + '\n')
        file.write('Motor settling time: ' + str(self.motor_settling_time) + '\n')
        file.write('Motor Autocenter position [mm]: ' + str(self.motor_AC_position) + '\n')
        file.write('Motor Autocenter position keep in center: ' + str(self.motor_AC_position_center) + '\n')
        file.write('Motor Autocenter In-between: ' + str(self.motor_AC_inbetween) + '\n')
        file.write('Motor Autocenter In-between Image Step: ' + str(self.motor_AC_inbetween_step) + '\n')
        # file.write('Single plot: ' + str(self.single_plot) + '\n')
        # file.write('Ernst Angle Calculator T1 [ms]: ' + str(self.ernstanglecalc_T1) + '\n')
        # file.write('Ernst Angle Calculator TR [ms]: ' + str(self.ernstanglecalc_TR) + '\n')
        # file.write('Ernst Angle Calculator Ernst Angle [°]: ' + str(self.ernstanglecalc_EA) + '\n')
        # file.write('Image Colormap: ' + str(self.imagecolormap) + '\n')
        # file.write('Image Minimum: ' + str(self.imageminimum) + '\n')
        # file.write('Image Maximum: ' + str(self.imagemaximum) + '\n')
        # file.write(': ' + str(self.measurement_time_dialog) + '\n')
        # file.write(': ' + str(self.toolautosequence) + '\n')
        # file.write(': ' + str(self.image_grid) + '\n')
        # file.write(': ' + str(self.projection3D) + '\n')
        
        file.close()

    def save_header_file_json(self):
        filename = params.datapath + '_Header.json'

        header_dict = {
            'Hosts': self.hosts,
            'Connection mode': self.connectionmode,
            'GUI mode': self.GUImode,
            'Sequence': self.sequence,
            'Sequence file': self.sequencefile,
            'Data path': self.datapath,
            'Frequency [MHz]': self.frequency,
            'Auto recenter': self.autorecenter,
            'Auto data process': self.autodataprocess,
            'RF frequency offset [Hz]':
                -self.frequencyoffset if self.frequencyoffsetsign == 1
                else self.frequencyoffset,
            'RF phase offset [°]': self.phaseoffset,
            'RF phase offset [rad]': self.phaseoffsetradmod100,
            'RF pulse length [µs]': self.RFpulselength,
            'RF pulse amplitude': self.RFpulseamplitude,
            'Flip angle (time) [°]': self.flipangletime,
            'Flip angle (amplitude) [°]': self.flipangleamplitude,
            'Flip pulse length [µs]': self.flippulselength,
            'Flip pulse amplitude': self.flippulseamplitude,
            'RF attenuation [dB]': self.RFattenuation,
            'RX port 1': self.rx1,
            'RX port 2': self.rx2,
            'RX mode': self.rxmode,
            'RX scaling': self.RXscaling,
            'TS [ms]': self.TS,
            'Readout bandwidth scaling': self.ROBWscaler,
            'TE [ms]': self.TE,
            'TI [ms]': self.TI,
            'SIR TE [ms]': self.SIR_TE,
            'TR [ms]': self.TR,
            'Shim values [mA]': list(self.grad),
            'Gradient orientation': list(self.Gradientorientation),
            'Image orientation': 'XY' if self.imageorientation == 0
            else ('YZ' if self.imageorientation == 1
                  else ('ZX' if self.imageorientation == 2
                      else ('YX' if self.imageorientation == 3
                          else ('ZY' if self.imageorientation == 4
                              else ('XZ'))))),
            'Image resolution index': self.imageresolution,
            'Image resolution [pixel]': self.nPE,
            'Frequency range [Hz]': self.frequencyrange,
            'Samples': self.samples,
            'Sampledelay': self.sampledelay,
            'Timestamp': self.dataTimestamp,
            'TI start [ms]': self.TIstart,
            'TI stop [ms]': self.TIstop,
            'TI steps': self.TIsteps,
            'TE start [ms]': self.TEstart,
            'TE stop [ms]': self.TEstop,
            'TE steps': self.TEsteps,
            'Projection axes': list(self.projaxis),
            'Average': self.average,
            'Average complex': self.average_complex,
            'Number of averages': self.averagecount,
            'Projection gradient amplitude [mA]': list(self.Gproj),
            'Projection angle [°]': self.projectionangle,
            'Projection angle [rad]': self.projectionangleradmod100,
            'Readout gradient amplitude [mA]': self.GROamplitude,
            'Phase gradient step amplitude [mA]': self.GPEstep,
            'Slice gradient amplitude [mA]': self.GSamplitude,
            '3D phase gradient step amplitude [mA]:': self.GSPEstep,
            '3D phase steps': self.SPEsteps,
            'Diffusion gradient amplitude [mA]': self.Gdiffamplitude,
            'Crusher gradient amplitude [mA]': self.crusheramplitude,
            'Spoiler gradient amplitude [mA]': self.spoileramplitude,
            'Readout gradient prephaser duration [µs]': self.GROpretime,
            'Readout gradient prephaser duration scaling': self.GROpretimescaler,
            'Slice gradient rephaser time [µs]': self.GSposttime,
            'Crusher gradient duration [µs]': self.crushertime,
            'Spoiler gradient duration [µs]': self.spoilertime,
            'Diffusion gradient duration [µs]': self.diffusiontime,
            'Fluid compensation readout gradient prephaser 1 duration [µs]':
                self.GROfcpretime1,
            'Fluid compensation readout gradient prephaser 2 duration [µs]':
                self.GROfcpretime2,
            'Radial angle [°]': self.radialanglestep,
            'Radial oversampling factor': self.radialosfactor,
            'Radial angle [rad]': self.radialanglestepradmod100,
            'Auto gradients': self.autograd,
            'FOV [mm]': self.FOV,
            'Slice/Slab thickness [mm]': self.slicethickness,
            'Gradient sensitivity [mT/m/A]': list(self.gradsens),
            'Auto frequency offset': self.autofreqoffset,
            'Slice offset [mm]': self.sliceoffset,
            'SAR enable': self.SAR_enable,
            'SAR limit [W]': self.SAR_limit,
            'SAR status': self.SAR_status,
            'Header File Format': '.txt' if self.headerfileformat == 0
            else ('.json'),
            'Motor enable': self.motor_enable,
            'Motor available': self.motor_available,
            'Motor COM Port': self.motor_port,
            'Motor axis limit negative [mm]': self.motor_axis_limit_negative,
            'Motor axis limit positive [mm]': self.motor_axis_limit_positive,
            'Motor movement direction': self.motor_movement_direction,
            'Motor actual position [mm]': self.motor_actual_position,
            'Motor goto position [mm]': self.motor_goto_position,
            'Motor start position [mm]': self.motor_start_position,
            'Motor end position [mm]': self.motor_end_position,
            'Motor total image length [mm]':self.motor_total_image_length,
            'Motor movement step [mm]': self.motor_movement_step,
            'Motor image count': self.motor_image_count,
            'Motor current image count': self.motor_current_image_count,
            'Motor settling time': self.motor_settling_time,
            'Motor Autocenter position [mm]': self.motor_AC_position,
            'Motor Autocenter position keep in center': self.motor_AC_position_center,
            'Motor Autocenter In-between': self.motor_AC_inbetween,
            'Motor Autocenter In-between Image Step': self.motor_AC_inbetween_step
        }

        out_file = open(filename, 'w')

        json.dump(header_dict, out_file, ensure_ascii=False, indent=4)

    def load_GUItheme(self):
        file = QFile(':/' + self.GUIthemestr[self.GUItheme] + '.qss')
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        self.stylesheet = stream.readAll()
        self.cycler = cycler(color=['#000000', '#0000BB', '#BB0000'])
        
params = Parameters()
