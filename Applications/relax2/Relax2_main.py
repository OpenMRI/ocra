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
import csv
import numpy as np
import os
import math
import time
import shutil

from datetime import datetime

# import PyQt5 packages
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QApplication, QFileDialog, QDesktopWidget, QFrame, QTableWidget, QTableWidgetItem
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QRegExp, pyqtSignal, QStandardPaths
from PyQt5.QtGui import QRegExpValidator, QPixmap

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from parameter_handler import params
from sequence_handler import seq
from process_handler import proc
from data_logger import logger

plt.rc('axes', prop_cycle=params.cycler)
plt.rcParams['lines.linewidth'] = 2
plt.rcParams['axes.grid'] = True
plt.rcParams['figure.autolayout'] = True
plt.rcParams['figure.dpi'] = 75
plt.rcParams['legend.loc'] = "upper right"
plt.rcParams['toolbar'] = 'toolbar2'

Main_Window_Form, Main_Window_Base = loadUiType('ui/mainwindow.ui')
Conn_Dialog_Form, Conn_Dialog_Base = loadUiType('ui/connDialog.ui')
Para_Window_Form, Para_Window_Base = loadUiType('ui/parameters.ui')
Plot_Window_Form, Plot_Window_Base = loadUiType('ui/plotview.ui')
Tools_Window_Form, Tools_Window_Base = loadUiType('ui/tools.ui')
Protocol_Window_Form, Protocol_Window_Base = loadUiType('ui/protocol.ui')


class MainWindow(Main_Window_Base, Main_Window_Form):
    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.dialog_params = None

        self.ui = loadUi('ui/mainwindow.ui')
        self.setWindowTitle('Relax 2.0')
        self.setStyleSheet(params.stylesheet)
        self.setGeometry(10, 40, 400, 410)
        
        params.connectionmode = 0
        params.projaxis = np.zeros(3)
        params.ustime = 0
        params.usphase = 0
        params.flipangletime = 90
        params.flipangleamplitude = 90
        params.flippulselength = int(params.RFpulselength / 90 * params.flipangletime)
        params.flippulseamplitude = int(params.RFpulseamplitude / 90 * params.flipangleamplitude)
        params.average = 0
        params.frequencyplotrange = 250000
        params.sliceoffset = 0
        params.frequencyoffset = 0
        params.frequencyoffsetsign = 0
        params.phaseoffset = 0
        params.phaseoffsetradmod100 = 0
        params.lnkspacemag = 0
        params.ToolShimChannel = [0, 0, 0, 0]
        
        if params.GSamplitude == 0:
            params.GSposttime = 0
        else:
            params.GSposttime = int((200*params.GSamplitude + 4*params.flippulselength*params.GSamplitude)/2-200*params.GSamplitude/2)/(params.GSamplitude/2)
        #params.dispVars()

        self.establish_conn()

        self.Mode_Spectroscopy_pushButton.clicked.connect(lambda: self.switch_GUImode(0))
        self.Mode_Imaging_pushButton.clicked.connect(lambda: self.switch_GUImode(1))
        self.Mode_T1_Measurement_pushButton.clicked.connect(lambda: self.switch_GUImode(2))
        self.Mode_T2_Measurement_pushButton.clicked.connect(lambda: self.switch_GUImode(3))
        self.Mode_Projections_pushButton.clicked.connect(lambda: self.switch_GUImode(4))
        
        self.Sequence_comboBox.currentIndexChanged.connect(self.set_sequence)
        self.Parameters_pushButton.clicked.connect(lambda: self.parameter_window())
        self.Acquire_pushButton.clicked.connect(lambda: self.acquire())
        self.Data_Process_pushButton.clicked.connect(lambda: self.dataprocess())
        self.Tools_pushButton.clicked.connect(lambda: self.tools())
        self.Protocol_pushButton.clicked.connect(lambda: self.protocol())
        
        self.Datapath_lineEdit.editingFinished.connect(lambda: self.set_Datapath())

    def establish_conn(self):
        self.dialog_con = ConnectionDialog(self)
        self.dialog_con.show()
        self.dialog_con.connected.connect(self.start_com)

    def start_com(self):
        logger.init()

    def switch_GUImode(self, mode):
        params.GUImode = mode
        
        print("GUImode:\t", params.GUImode)
        
        if params.GUImode == 0:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Free Induction Decay', 'Spin Echo', 'Inversion Recovery (FID)' \
                                             , 'Inversion Recovery (SE)','Saturation Inversion Recovery (FID)','Saturation Inversion Recovery (SE)' \
                                             , 'Echo Planar Spectrum (FID, 4 Echos)', 'Echo Planar Spectrum (SE, 4 Echos)', 'Turbo Spin Echo (4 Echos)' \
                                             , 'Free Induction Decay (Slice)', 'Spin Echo (Slice)', 'Inversion Recovery (FID, Slice)' \
                                             , 'Inversion Recovery (SE, Slice)','Saturation Inversion Recovery (FID, Slice)','Saturation Inversion Recovery (SE, Slice)' \
                                             , 'Echo Planar Spectrum (FID, 4 Echos, Slice)', 'Echo Planar Spectrum (SE, 4 Echos, Slice)', 'Turbo Spin Echo (4 Echos, Slice)' \
                                             , 'RF Testsequence', 'Gradient Testsequence'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/Spectrum_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 1:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['2D Radial (GRE, Full)', '2D Radial (SE, Full)', '2D Radial (GRE, Half)' \
                                             , '2D Radial (SE, Half)', '2D Gradient Echo', '2D Spin Echo' \
                                             , '2D Spin Echo (InOut)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                             , '2D Saturation Inversion Recovery (GRE)', 'WIP 2D Saturation Inversion Recovery (SE)' \
                                             , '2D Turbo Spin Echo (4 Echos)', '2D Echo Planar Imaging (GRE, 4 Echos)', '2D Echo Planar Imaging (SE, 4 Echos)' \
                                             , '2D Diffusion (SE)', '2D Flow Compensation (GRE)', '2D Flow Compensation (SE)' \
                                             , 'WIP 2D Radial (Slice, GRE, Full)', 'WIP 2D Radial (Slice, SE, Full)', 'WIP 2D Radial (Slice, GRE, Half)' \
                                             , 'WIP 2D Radial (Slice, SE, Half)', '2D Gradient Echo (Slice)', '2D Spin Echo (Slice)' \
                                             , '2D Spin Echo (Slice, InOut)', '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)' \
                                             , 'WIP 2D Saturation Inversion Recovery (Slice, GRE)', 'WIP 2D Saturation Inversion Recovery (Slice, SE)', '2D Turbo Spin Echo (Slice, 4 Echos)' \
                                             , 'WIP 2D Echo Planar Imaging (Slice, GRE, 4 Echos)', 'WIP 2D Echo Planar Imaging (Slice, SE, 4 Echos)', 'WIP 2D Diffusion (Slice, SE)' \
                                             , 'WIP 2D Flow Compensation (Slice, GRE)', 'WIP 2D Flow Compensation (Slice, SE)', 'WIP 3D FFT Spin Echo' \
                                             , '3D FFT Spin Echo (Slab)', '3D FFT Turbo Spin Echo (Slab)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/Image_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 2:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Inversion Recovery (FID)', 'Inversion Recovery (SE)','Inversion Recovery (Slice, FID)' \
                                             , 'Inversion Recovery (Slice, SE)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                             , '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/T1_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 3:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Spin Echo', 'Saturation Inversion Recovery (FID)','Spin Echo (Slice)' \
                                             , 'Saturation Inversion Recovery (Slice, FID)','2D Spin Echo', '2D Saturation Inversion Recovery (GRE)' \
                                             ,'2D Spin Echo (Slice)', '2D Saturation Inversion Recovery (Slice, GRE)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/T2_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 4:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Gradient Echo (On Axis)', 'Spin Echo (On Axis)', 'Gradient Echo (On Angle)', 'Spin Echo (On Angle)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/Projection_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        
    def set_sequence(self, idx):
        params.sequence = idx
        if params.sequence != -1: print("Sequence:\t", params.sequence)
        
    def acquire(self):
        if params.connectionmode == 1:
            if params.GUImode == 2 and params.sequence == 0:
                proc.T1measurement_IR_FID()
            elif params.GUImode == 2 and params.sequence == 1:
                proc.T1measurement_IR_SE()
            elif params.GUImode == 2 and params.sequence == 2:
                proc.T1measurement_IR_FID_Gs()
            elif params.GUImode == 2 and params.sequence == 3:
                proc.T1measurement_IR_SE_Gs()
            elif params.GUImode == 2 and params.sequence == 4:
                proc.T1measurement_Image_IR_GRE()
            elif params.GUImode == 2 and params.sequence == 5:
                proc.T1measurement_Image_IR_SE()
            elif params.GUImode == 2 and params.sequence == 6:
                proc.T1measurement_Image_IR_GRE_Gs()
            elif params.GUImode == 2 and params.sequence == 7:
                proc.T1measurement_Image_IR_SE_Gs()
            elif params.GUImode == 3 and params.sequence == 0:
                proc.T2measurement_SE()
            elif params.GUImode == 3 and params.sequence == 1:
                proc.T2measurement_SIR_FID()
            elif params.GUImode == 3 and params.sequence == 2:
                proc.T2measurement_SE_Gs()
            elif params.GUImode == 3 and params.sequence == 3:
                proc.T2measurement_SIR_FID_Gs()
            elif params.GUImode == 3 and params.sequence == 4:
                proc.T2measurement_Image_SE()
            elif params.GUImode == 3 and params.sequence == 5:
                proc.T2measurement_Image_SIR_GRE()
            elif params.GUImode == 3 and params.sequence == 6:
                proc.T2measurement_Image_SE_Gs()
            elif params.GUImode == 3 and params.sequence == 7:
                proc.T2measurement_Image_SIR_GRE_Gs()
            elif params.GUImode == 1:
                if params.autorecenter == 1:
                    if params.sequence == 0 or params.sequence == 2 or params.sequence == 4 \
                       or params.sequence == 7 or params.sequence == 9 or params.sequence == 12 \
                       or params.sequence == 15:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        seq.sequence_upload()
                    elif params.sequence == 17 or params.sequence == 19 or params.sequence == 21 \
                         or params.sequence == 24 or params.sequence == 26 or params.sequence == 29 \
                         or params.sequence == 32:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        seq.sequence_upload()
                    elif params.sequence == 1 or params.sequence == 3 or params.sequence == 5 \
                         or params.sequence == 6 or params.sequence == 8 or params.sequence == 10 \
                         or params.sequence == 11 or params.sequence == 13 or params.sequence == 14 \
                         or params.sequence == 16:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        seq.sequence_upload()
                    elif params.sequence == 18 or params.sequence == 20 or params.sequence == 22 \
                         or params.sequence == 23 or params.sequence == 25 or params.sequence == 27 \
                         or params.sequence == 28 or params.sequence == 30 or params.sequence == 31 \
                         or params.sequence == 33 or params.sequence == 34 or params.sequence == 35 \
                         or params.sequence == 36:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        seq.sequence_upload()
                else: seq.sequence_upload()
            else: seq.sequence_upload()
        else: print('\033[1m' + 'Not allowed in offline mode!' + '\033[0m')
        if self.dialog_params != None:
            self.dialog_params.load_params()
            self.dialog_params.repaint()  
            
    def load_params(self):
        self.Sequence_comboBox.clear()
        self.switch_GUImode(params.GUImode)
        
    def parameter_window(self):
            self.dialog_params = None
            self.dialog_params = ParametersWindow(self)
            self.dialog_params.show()
        
    def set_Datapath(self):
        params.datapath = self.Datapath_lineEdit.text()
        print('Datapath:', params.datapath)
        
    def dataprocess(self): 
        if params.GUImode == 0:
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.spectrum_process()
                proc.spectrum_analytics()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No File!!')
        elif params.GUImode == 1 and (params.sequence == 34 or params.sequence == 35 or params.sequence == 36):
            if os.path.isfile(params.datapath + '_3D_' + str(params.SPEsteps) + '.txt') == True:
                proc.image_3D_process()
                # proc.image_3D_analytics()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No 3D File!! \'Path/Filename_3D_slices\', \'_3D_slices\' will add automatically, Parameter: 3D Slab Steps needs to match \'slices\'')
        elif params.GUImode == 1 and (params.sequence == 14 or params.sequence == 31):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.image_diff_process()
                # proc.image_analytics()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No File!!')
        elif params.GUImode == 1 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 \
                                      or params.sequence == 3 or params.sequence == 17 or params.sequence == 18 \
                                      or params.sequence == 19 or params.sequence == 20):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.radial_process()
                proc.image_analytics()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No File!!')
        elif params.GUImode == 1 and (params.sequence != 34 or params.sequence != 35 or params.sequence != 36 \
                                      or params.sequence != 14 or params.sequence != 31 or params.sequence != 0 \
                                      or params.sequence != 1 or params.sequence != 2 or params.sequence != 3 \
                                      or params.sequence != 17 or params.sequence != 18 or params.sequence != 19 \
                                      or params.sequence != 20):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.image_process()
                proc.image_analytics()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No File!!')
                
        elif params.GUImode == 2 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.T1process()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No File!!')
        elif params.GUImode == 2 and (params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7):
            if os.path.isfile(params.datapath + '_Image_TI_steps.txt') == True:
                if os.path.isfile(params.datapath + '_Image_Magnitude.txt') == True:
                    proc.T1imageprocess()
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
                else: print('No File!!')
            else: print('No File!!')
            
        elif params.GUImode == 3 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.T2process()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No File!!')
        elif params.GUImode == 3 and (params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7):
            if os.path.isfile(params.datapath + '_Image_TE_steps.txt') == True:
                if os.path.isfile(params.datapath + '_Image_Magnitude.txt') == True:
                    proc.T2imageprocess()
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else: print('No File!!')
            
        elif params.GUImode == 4:
            if params.sequence == 0 or params.sequence == 1:
                self.datapathtemp = params.datapath
                params.projx =  np.matrix(np.zeros((1,4)))
                params.projy =  np.matrix(np.zeros((1,4)))
                params.projz =  np.matrix(np.zeros((1,4)))
                for m in range(params.projaxis.shape[0]):
                    params.datapath = self.datapathtemp + '_' + str(m)
                    if os.path.isfile(params.datapath + '.txt') == True:
                        proc.spectrum_process()
                        if m == 0:
                            params.projx = np.matrix(np.zeros((params.timeaxis.shape[0],4)))
                            params.projx[:,0] = np.reshape(params.mag,(params.timeaxis.shape[0],1))
                            params.projx[:,1] = np.reshape(params.real,(params.timeaxis.shape[0],1))
                            params.projx[:,2] = np.reshape(params.imag,(params.timeaxis.shape[0],1))
                            params.projx[:,3] = params.spectrumfft
                        elif m == 1:
                            params.projy = np.matrix(np.zeros((params.timeaxis.shape[0],4)))
                            params.projy[:,0] = np.reshape(params.mag,(params.timeaxis.shape[0],1))
                            params.projy[:,1] = np.reshape(params.real,(params.timeaxis.shape[0],1))
                            params.projy[:,2] = np.reshape(params.imag,(params.timeaxis.shape[0],1))
                            params.projy[:,3] = params.spectrumfft
                        elif m == 2:
                            params.projz = np.matrix(np.zeros((params.timeaxis.shape[0],4)))
                            params.projz[:,0] = np.reshape(params.mag,(params.timeaxis.shape[0],1))
                            params.projz[:,1] = np.reshape(params.real,(params.timeaxis.shape[0],1))
                            params.projz[:,2] = np.reshape(params.imag,(params.timeaxis.shape[0],1))
                            params.projz[:,3] = params.spectrumfft
                    else: print('No File!!')
                params.datapath = self.datapathtemp
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            elif params.sequence == 2 or params.sequence == 3:
                proc.spectrum_process()
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
                
        params.saveFileData()
   
    def tools(self):
        self.dialog_tools = ToolsWindow(self)
        self.dialog_tools.show()
        
    def protocol(self):
        self.dialog_prot = ProtocolWindow(self)
        self.dialog_prot.show()

    def update_gui(self):
        QApplication.processEvents()

    def closeEvent(self, event):
        choice = QMessageBox.question(self, 'Close Relax 2.0', 'Are you sure that you want to quit Relax 2.0?',\
            QMessageBox.Cancel | QMessageBox.Close, QMessageBox.Cancel)

        if choice == QMessageBox.Close:

            params.GUImode = 0
            params.sequence = 0
            params.saveFileParameter()
            params.saveFileData()
            event.accept()
            raise SystemExit
        else: event.ignore()

class ParametersWindow(Para_Window_Form, Para_Window_Base):

    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ParametersWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.load_params()
        
        self.ui = loadUi('ui/parameters.ui')
        self.setWindowTitle('Parameters')
        self.setGeometry(420, 40, 1300, 750)
        
        #self.label_3.setToolTip('<img src="tooltip/test.png">')
        self.Frequency_doubleSpinBox.setKeyboardTracking(False)
        self.Frequency_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label.setToolTip('Frequency of the RF carrier signal. Needs to be set to the Larmor frequency of the MRI system.')
        self.Center_pushButton.clicked.connect(lambda: self.frequency_center())
        self.Center_pushButton.setToolTip('Sets the RF frequency to the peak frequency of the last measured and processed spectrum.')
        self.auto_recenter_radioButton.toggled.connect(self.update_params)
        self.auto_recenter_radioButton.setToolTip('A spin echo spectrum is performed and the RF carrier frequency will recentered before imaging.')
        self.RF_Pulselength_spinBox.setKeyboardTracking(False)
        self.RF_Pulselength_spinBox.valueChanged.connect(self.update_params)
        self.label_2.setToolTip('The reference duration of a 90° RF hard pulse.\nThe 180° hard pulse is 2x this duration.\nThe 90° sinc pulse main peak is 2x this duration and has a total duration of 4x.\nThe 180° sinc pulse main peak is 4x this duration and has a total duration of 8x')
        self.RF_Attenuation_doubleSpinBox.setKeyboardTracking(False)
        self.RF_Attenuation_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_3.setToolTip('The attenuation of the OCRA1 RF attenuator.\nThis determinants the reference amplitude of the 90° and 180° pulse.')
        self.Samplingtime_spinBox.setKeyboardTracking(False)
        self.Samplingtime_spinBox.valueChanged.connect(self.update_params)
        self.label_6.setToolTip('The duration of the sampling window where the MRI signal is measured.')
        self.Readout_Bandwidth_spinBox.setKeyboardTracking(False)
        self.Readout_Bandwidth_spinBox.valueChanged.connect(self.update_params)
        self.label_11.setToolTip('Scales the image in readout direction.\nThis happens after the reconstruction.\nLike a digital zoom. Standard is 1.')
        self.TE_doubleSpinBox.setKeyboardTracking(False)
        self.TE_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_4.setToolTip('The time between the center of the RF flip pulse and the center of the sampling window (also in FID and GRE sequences).')
        self.TI_doubleSpinBox.setKeyboardTracking(False)
        self.TI_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_13.setToolTip('The time between the center of the RF 180° inversion pulse and the center of the RF flip pulse.')
        self.TR_spinBox.setKeyboardTracking(False)
        self.TR_spinBox.valueChanged.connect(self.update_params)
        self.label_5.setToolTip('The time between repetitions for aquirering k-space lines in images or averages in spectra.')
        self.Shim_X_spinBox.setKeyboardTracking(False)
        self.Shim_X_spinBox.valueChanged.connect(self.update_params)
        self.Shim_Y_spinBox.setKeyboardTracking(False)
        self.Shim_Y_spinBox.valueChanged.connect(self.update_params)
        self.Shim_Z_spinBox.setKeyboardTracking(False)
        self.Shim_Z_spinBox.valueChanged.connect(self.update_params)
        self.Shim_Z2_spinBox.setKeyboardTracking(False)
        self.Shim_Z2_spinBox.valueChanged.connect(self.update_params)
        self.Image_Resolution_spinBox.setKeyboardTracking(False)
        self.Image_Resolution_spinBox.valueChanged.connect(self.update_params)
        self.label_12.setToolTip('The images resolution determents the numper of k-space lines to acquire.\nNote that a few sequences only work for the standard resolutions 8, 16, 32, 64 or 128.')
        self.TI_Start_doubleSpinBox.setKeyboardTracking(False)
        self.TI_Start_doubleSpinBox.valueChanged.connect(self.update_params)
        self.TI_Stop_doubleSpinBox.setKeyboardTracking(False)
        self.TI_Stop_doubleSpinBox.valueChanged.connect(self.update_params)
        self.TI_Steps_spinBox.setKeyboardTracking(False)
        self.TI_Steps_spinBox.valueChanged.connect(self.update_params)
        self.TE_Start_doubleSpinBox.setKeyboardTracking(False)
        self.TE_Start_doubleSpinBox.valueChanged.connect(self.update_params)
        self.TE_Stop_doubleSpinBox.setKeyboardTracking(False)
        self.TE_Stop_doubleSpinBox.valueChanged.connect(self.update_params)
        self.TE_Steps_spinBox.setKeyboardTracking(False)
        self.TE_Steps_spinBox.valueChanged.connect(self.update_params)
        
        self.Projection_X_radioButton.toggled.connect(self.update_params)
        self.Projection_Y_radioButton.toggled.connect(self.update_params)
        self.Projection_Z_radioButton.toggled.connect(self.update_params)
        
        self.Projection_Angle_spinBox.setKeyboardTracking(False)
        self.Projection_Angle_spinBox.valueChanged.connect(self.update_params) 
        
        self.Average_spinBox.setKeyboardTracking(False)
        self.Average_spinBox.valueChanged.connect(self.update_params)
        self.Average_radioButton.toggled.connect(self.update_params)
        self.Average_radioButton.setToolTip('Averaging of MRI spectra.')
        
        self.Image_Filter_radioButton.toggled.connect(self.update_params)
        self.Images_Plot_radioButton.toggled.connect(self.update_params)
        
        self.kspace_cut_circ_radioButton.toggled.connect(self.update_params)
        self.kspace_cut_rec_radioButton.toggled.connect(self.update_params)
        
        self.kSpace_Cut_Center_radioButton.toggled.connect(self.update_params)
        self.kSpace_Cut_Outside_radioButton.toggled.connect(self.update_params)
        self.kSpace_Cut_Center_spinBox.setKeyboardTracking(False)
        self.kSpace_Cut_Center_spinBox.valueChanged.connect(self.update_params)
        self.kSpace_Cut_Outside_spinBox.setKeyboardTracking(False)
        self.kSpace_Cut_Outside_spinBox.valueChanged.connect(self.update_params)
        
        self.Undersampling_Time_comboBox.currentIndexChanged.connect(self.update_params)
        self.Undersampling_Phase_comboBox.currentIndexChanged.connect(self.update_params)
        
        self.Undersampling_Time_comboBox.clear()
        self.Undersampling_Time_comboBox.addItems(['2', '5', '10', '50'])
        self.Undersampling_Time_comboBox.setCurrentIndex(0)
        
        self.Undersampling_Phase_comboBox.clear()
        self.Undersampling_Phase_comboBox.addItems(['2', '4', '8'])
        self.Undersampling_Phase_comboBox.setCurrentIndex(0)
        
        self.Undersampling_Time_radioButton.toggled.connect(self.update_params)
        self.Undersampling_Phase_radioButton.toggled.connect(self.update_params)
        
        self.Undersampling_Time_comboBox.currentIndexChanged.connect(self.update_params)
        self.Undersampling_Phase_comboBox.currentIndexChanged.connect(self.update_params)
        
        self.Auto_Gradients_radioButton.toggled.connect(self.auto_gradients)
        
        self.GROamplitude_spinBox.setKeyboardTracking(False)
        self.GROamplitude_spinBox.valueChanged.connect(self.update_gradients)
        self.label_32.setToolTip('Amplitude of the readout gradient.\nThe readout prephaser is 2x this amplitude.')
        self.GPEstep_spinBox.setKeyboardTracking(False)
        self.GPEstep_spinBox.valueChanged.connect(self.update_gradients)
        self.label_33.setToolTip('Amplitude of a phase gradient step.\nThe total amplitude add up to (image resolution / 2) * phase gradient step.')
        
        self.GSamplitude_spinBox.setKeyboardTracking(False)
        self.GSamplitude_spinBox.valueChanged.connect(self.update_gradients)
        self.label_34.setToolTip('Amplitude of a slice gradient.\nThe slice rephaser is 0.5x this amplitude.\n For 3D FFT imaging this determinants the slab thickness')
        
        self.Flipangle_Time_spinBox.setKeyboardTracking(False)
        self.Flipangle_Time_spinBox.valueChanged.connect(self.update_flippulselength)
        self.label_35.setToolTip('Scales the 90° reference duration of the flip pulse to the according flip angle.')
        self.Flipangle_Amplitude_spinBox.setKeyboardTracking(False)
        self.Flipangle_Amplitude_spinBox.valueChanged.connect(self.update_flippulseamplitude)
        self.label_45.setToolTip('Scales the 90° reference amplitude (not attenuation) of the flip pulse to the according flip angle.')
        
        self.GSPEstep_spinBox.setKeyboardTracking(False)
        self.GSPEstep_spinBox.valueChanged.connect(self.update_gradients)
        self.label_39.setToolTip('Amplitude of a 3D "slice" phase gradient step.\nThe total amplitude add up to (3D slab steps / 2) * 3D "slice" phase gradient step.')
        self.SPEsteps_spinBox.setKeyboardTracking(False)
        self.SPEsteps_spinBox.valueChanged.connect(self.update_params)
        self.label_40.setToolTip('Number of 3D FFT "slices".')
        
        self.GDiffamplitude_spinBox.setKeyboardTracking(False)
        self.GDiffamplitude_spinBox.valueChanged.connect(self.update_params)
        self.label_41.setToolTip('Amplitude of the diffusion gradient pulses.\nThe duration is 1ms and can be adjusted in the parameters_handler.py')
        
        self.Crusher_Amplitude_spinBox.setKeyboardTracking(False)
        self.Crusher_Amplitude_spinBox.valueChanged.connect(self.update_gradients)
        self.label_42.setToolTip('Amplitude of the crusher gradient pulses.\nThe duration is 0.4ms and can be adjusted in the parameters_handler.py')
        self.Spoiler_Amplitude_spinBox.setKeyboardTracking(False)
        self.Spoiler_Amplitude_spinBox.valueChanged.connect(self.update_gradients)
        self.label_43.setToolTip('Amplitude of the spoiler gradient pulse.\nThe duration is 1ms and can be adjusted in the parameters_handler.py')
        
        self.Image_Orientation_comboBox.clear()
        self.Image_Orientation_comboBox.addItems(['XY', 'YZ', 'ZX'])
        self.Image_Orientation_comboBox.setCurrentIndex(params.imageorientation)
        self.Image_Orientation_comboBox.currentIndexChanged.connect(self.update_params)
        
        self.Auto_Frequency_Offset_radioButton.toggled.connect(self.auto_freqoffset)
        
        self.Slice_Offset_doubleSpinBox.setKeyboardTracking(False)
        self.Slice_Offset_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.Frequency_Offset_spinBox.setKeyboardTracking(False)
        self.Frequency_Offset_spinBox.valueChanged.connect(self.update_freqoffset)
        self.label_46.setToolTip('Frequency offset of the RF carrier signal for slice selection.\nThe frequency is based on the flip pulse bandwidth.')
        self.Phase_Offset_spinBox.setKeyboardTracking(False)
        self.Phase_Offset_spinBox.valueChanged.connect(self.update_params)
        self.label_48.setToolTip('Phase offset of the RF carrier signal for RF spoiling. In images the phase angle shifts with k² (WIP).')
        
        self.GRO_Length_Scaler_doubleSpinBox.setKeyboardTracking(False)
        self.GRO_Length_Scaler_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.Radial_Angle_Step_spinBox.setKeyboardTracking(False)
        self.Radial_Angle_Step_spinBox.valueChanged.connect(self.update_params)
        
        self.ln_kSpace_Magnitude_radioButton.toggled.connect(self.update_params)
        
        self.AC_Apply_pushButton.clicked.connect(lambda: self.Set_AC_centerfrequency())
        self.FA_Apply_pushButton.clicked.connect(lambda: self.Set_FA_RFattenution())
        
        self.FOV_doubleSpinBox.setKeyboardTracking(False)
        self.FOV_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Slice_Thickness_doubleSpinBox.setKeyboardTracking(False)
        self.Slice_Thickness_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.RX1_radioButton.toggled.connect(self.update_params)
        self.RX2_radioButton.toggled.connect(self.update_params)
        
        self.SignalMask_doubleSpinBox.setKeyboardTracking(False)
        self.SignalMask_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_28.setToolTip('Image mask for overlays like T1, T2 or field maps. Draw all pixels with a signal strength above the value times the maximum pixel signal strength. Default value is 0.5.')
        
    def frequency_center(self):
        params.frequency = params.centerfrequency
        self.Frequency_doubleSpinBox.setValue(params.frequency)
        print('Center Frequency applied!')
        
    def load_params(self):
        self.Frequency_doubleSpinBox.setValue(params.frequency)
        
        if params.autorecenter == 1: self.auto_recenter_radioButton.setChecked(True)
        
        self.RF_Pulselength_spinBox.setValue(params.RFpulselength)
        self.RF_Attenuation_doubleSpinBox.setValue(params.RFattenuation)
        self.Readout_Bandwidth_spinBox.setValue(params.ROBWscaler)
        self.TE_doubleSpinBox.setValue(params.TE)
        self.TI_doubleSpinBox.setValue(params.TI)
        self.TR_spinBox.setValue(params.TR)
        self.Shim_X_spinBox.setValue(params.grad[0])
        self.Shim_Y_spinBox.setValue(params.grad[1])
        self.Shim_Z_spinBox.setValue(params.grad[2])
        self.Shim_Z2_spinBox.setValue(params.grad[3])
        self.Image_Resolution_spinBox.setValue(params.nPE)
        self.Samplingtime_spinBox.setValue(params.TS)
        self.TI_Start_doubleSpinBox.setValue(params.TIstart)
        self.TI_Stop_doubleSpinBox.setValue(params.TIstop)
        self.TI_Steps_spinBox.setValue(params.TIsteps)
        self.TE_Start_doubleSpinBox.setValue(params.TEstart)
        self.TE_Stop_doubleSpinBox.setValue(params.TEstop)
        self.TE_Steps_spinBox.setValue(params.TEsteps)
        
        if params.projaxis[0] == 1: self.Projection_X_radioButton.setChecked(True)
        if params.projaxis[1] == 1: self.Projection_Y_radioButton.setChecked(True)
        if params.projaxis[2] == 1: self.Projection_Z_radioButton.setChecked(True)
        
        self.Projection_Angle_spinBox.setValue(params.projectionangle)
        
        if params.average == 1: self.Average_radioButton.setChecked(True)
        self.Average_spinBox.setValue(params.averagecount)
        
        if params.imagplots == 1: self.Images_Plot_radioButton.setChecked(True)
        if params.imagefilter == 1: self.Image_Filter_radioButton.setChecked(True)
        
        if params.cutcirc == 1: self.kspace_cut_circ_radioButton.setChecked(True)
        if params.cutrec == 1: self.kspace_cut_rec_radioButton.setChecked(True)
        
        if params.cutcenter == 1: self.kSpace_Cut_Center_radioButton.setChecked(True)
        if params.cutoutside == 1: self.kSpace_Cut_Outside_radioButton.setChecked(True)
        self.kSpace_Cut_Center_spinBox.setValue(params.cutcentervalue)
        self.kSpace_Cut_Outside_spinBox.setValue(params.cutoutsidevalue)
        
        if params.ustime == 1: self.Undersampling_Time_radioButton.setChecked(True)
        if params.usphase == 1: self.Undersampling_Phase_radioButton.setChecked(True)
        
        self.GROamplitude_spinBox.setValue(params.GROamplitude)
        self.GPEstep_spinBox.setValue(params.GPEstep)
        self.GSamplitude_spinBox.setValue(params.GSamplitude)

        self.Flipangle_Time_spinBox.setValue(params.flipangletime)
        self.Flipangle_Amplitude_spinBox.setValue(params.flipangleamplitude)
        
        self.GSPEstep_spinBox.setValue(params.GSPEstep)
        self.SPEsteps_spinBox.setValue(params.SPEsteps)
        
        self.GDiffamplitude_spinBox.setValue(params.Gdiffamplitude)
        
        self.Crusher_Amplitude_spinBox.setValue(params.crusheramplitude)
        self.Spoiler_Amplitude_spinBox.setValue(params.spoileramplitude)
        
        self.Image_Orientation_comboBox.setCurrentIndex(params.imageorientation)
        
        if params.frequencyoffsetsign == 0:
            self.Frequency_Offset_spinBox.setValue(params.frequencyoffset)
        elif params.frequencyoffsetsign == 1:
            self.Frequency_Offset_spinBox.setValue(-1*params.frequencyoffset)
            
        self.Phase_Offset_spinBox.setValue(params.phaseoffset)
        
        self.GRO_Length_Scaler_doubleSpinBox.setValue(params.GROpretimescaler)
        
        self.Radial_Angle_Step_spinBox.setValue(params.radialanglestep)
        
        if params.lnkspacemag == 1: self.ln_kSpace_Magnitude_radioButton.setChecked(True)
        
        self.FOV_doubleSpinBox.setValue(params.FOV)
        self.Slice_Thickness_doubleSpinBox.setValue(params.slicethickness)
        
        if params.autograd == 1: self.Auto_Gradients_radioButton.setChecked(True)
        
        self.Slice_Offset_doubleSpinBox.setValue(params.sliceoffset)
        
        if params.autofreqoffset == 1: self.Auto_Frequency_Offset_radioButton.setChecked(True)
        
        if params.rx1 == 1: self.RX1_radioButton.setChecked(True)
        if params.rx2 == 1: self.RX2_radioButton.setChecked(True)
        
        self.SignalMask_doubleSpinBox.setValue(params.signalmask)
        
    def update_flippulselength(self):
        params.flipangletime = self.Flipangle_Time_spinBox.value()
 
        if params.flipangletime != 90:
            params.flipangleamplitude = 90
            self.Flipangle_Amplitude_spinBox.setValue(params.flipangleamplitude)
            
        params.flippulselength = int(params.RFpulselength / 90 * params.flipangletime)
        if params.GSamplitude == 0:
            params.GSposttime =0
        else:
            params.GSposttime = int((200*params.GSamplitude + 4*params.flippulselength*params.GSamplitude)/2-200*params.GSamplitude/2)/(params.GSamplitude/2)

        if params.autograd == 1:
            self.Deltaf = 1 / (params.flippulselength) *1000000
            
            self.Gz = (2 * np.pi * self.Deltaf)/(2 * np.pi * 42.57 * (params.slicethickness)) 
            params.GSamplitude = int(self.Gz / self.Gzsens * 1000)
            
            self.Gz3D = (2 * np.pi / params.slicethickness)/(2 * np.pi * 42.57 * (self.GPEtime/1000000))
            params.GSPEstep =  int(self.Gz3D / self.Gzsens * 1000)
            print('Auto 3D SlPE max:', params.GSPEstep * params.SPEsteps / 2)
        
            self.update_gradients()
            
        if params.autofreqoffset == 1:
            
            self.Deltafs = (2 * np.pi * 42.57 * self.Gz * params.sliceoffset)/(2 * np.pi)
                
            if self.Deltafs >= 0:
                params.frequencyoffset = int(self.Deltafs)
                params.frequencyoffsetsign = 0
            else:
                params.frequencyoffset = int(abs(self.Deltafs))
                params.frequencyoffsetsign = 1
                
            self.update_freqoffset()
        
        params.saveFileParameter()
        
    def update_flippulseamplitude(self):
        params.flipangleamplitude = self.Flipangle_Amplitude_spinBox.value()
        
        if params.flipangleamplitude != 90:
            params.flipangletime = 90
            self.Flipangle_Time_spinBox.setValue(params.flipangletime)
        
        params.flippulseamplitude = int(params.RFpulseamplitude / 90 * params.flipangleamplitude)
        
        params.saveFileParameter()
        
    def auto_freqoffset(self):
        
        if self.Auto_Frequency_Offset_radioButton.isChecked():
            params.autofreqoffset = 1
            self.update_params()
        else: params.autofreqoffset = 0
        
        print('Autofreqoffset set to: ',params.autofreqoffset)
        
        params.saveFileParameter()
        
    def auto_gradients(self):
        
        if self.Auto_Gradients_radioButton.isChecked():
            params.autograd = 1
            self.update_params()
        else: params.autograd = 0
        
        print('Autograd set to: ',params.autograd)
        
        params.saveFileParameter()
        
    def update_params(self):
        params.frequency = self.Frequency_doubleSpinBox.value()
        if self.auto_recenter_radioButton.isChecked(): params.autorecenter = 1
        else: params.autorecenter = 0
        params.RFpulselength = (round(self.RF_Pulselength_spinBox.value()/10)*10)
        params.flippulselength = int(params.RFpulselength / 90 * params.flipangletime)
        
        if params.GSamplitude == 0: params.GSposttime =0
        else: params.GSposttime = int((200*params.GSamplitude + 4*params.flippulselength*params.GSamplitude)/2-200*params.GSamplitude/2)/(params.GSamplitude/2)
        
        params.RFattenuation = self.RF_Attenuation_doubleSpinBox.value()
        params.ROBWscaler = self.Readout_Bandwidth_spinBox.value()
        params.TE = self.TE_doubleSpinBox.value()
        params.TI = self.TI_doubleSpinBox.value()
        params.TR = self.TR_spinBox.value()
        params.TS = self.Samplingtime_spinBox.value()
        params.grad[0] = self.Shim_X_spinBox.value()
        params.grad[1] = self.Shim_Y_spinBox.value()
        params.grad[2] = self.Shim_Z_spinBox.value()
        params.grad[3] = self.Shim_Z2_spinBox.value()
        params.nPE = self.Image_Resolution_spinBox.value()
        
        params.TIstart = self.TI_Start_doubleSpinBox.value()
        params.TIstop = self.TI_Stop_doubleSpinBox.value()
        params.TIsteps = self.TI_Steps_spinBox.value()
        params.TEstart = self.TE_Start_doubleSpinBox.value()
        params.TEstop = self.TE_Stop_doubleSpinBox.value()
        params.TEsteps = self.TE_Steps_spinBox.value()
        
        if self.Projection_X_radioButton.isChecked(): params.projaxis[0] = 1
        else: params.projaxis[0] = 0
        if self.Projection_Y_radioButton.isChecked(): params.projaxis[1] = 1
        else: params.projaxis[1] = 0
        if self.Projection_Z_radioButton.isChecked(): params.projaxis[2] = 1
        else: params.projaxis[2] = 0
        
        params.projectionangle = self.Projection_Angle_spinBox.value()
        params.projectionangleradmod100 = int((math.radians(params.projectionangle) % (2*np.pi))*100)
        
        if self.Average_radioButton.isChecked(): params.average = 1
        else: params.average = 0
        params.averagecount = self.Average_spinBox.value()
        
        if self.Images_Plot_radioButton.isChecked(): params.imagplots = 1
        else: params.imagplots = 0
        if self.Image_Filter_radioButton.isChecked(): params.imagefilter = 1
        else: params.imagefilter = 0
        
        if self.kspace_cut_circ_radioButton.isChecked(): params.cutcirc = 1
        else: params.cutcirc = 0
        if self.kspace_cut_rec_radioButton.isChecked(): params.cutrec = 1
        else: params.cutrec = 0
        
        if self.kSpace_Cut_Center_radioButton.isChecked(): params.cutcenter = 1
        else: params.cutcenter = 0
        if self.kSpace_Cut_Outside_radioButton.isChecked(): params.cutoutside = 1
        else: params.cutoutside = 0
        params.cutcentervalue = self.kSpace_Cut_Center_spinBox.value()
        params.cutoutsidevalue = self.kSpace_Cut_Outside_spinBox.value()
        
        if self.Undersampling_Time_radioButton.isChecked(): params.ustime = 1
        else: params.ustime = 0
        if self.Undersampling_Phase_radioButton.isChecked(): params.usphase = 1
        else: params.usphase = 0
        
        if self.Undersampling_Time_comboBox.currentIndex() == 0:
            params.ustimeidx = 2
        elif self.Undersampling_Time_comboBox.currentIndex() == 1:
            params.ustimeidx = 5
        elif self.Undersampling_Time_comboBox.currentIndex() == 2:
            params.ustimeidx = 10
        elif self.Undersampling_Time_comboBox.currentIndex() == 3:
            params.ustimeidx = 50
        else: params.ustimeidx = 2
            
        if self.Undersampling_Phase_comboBox.currentIndex() == 0:
            params.usphaseidx = 2
        elif self.Undersampling_Phase_comboBox.currentIndex() == 1:
            params.usphaseidx = 4
        elif self.Undersampling_Phase_comboBox.currentIndex() == 2:
            params.usphaseidx = 8
        else:
            params.usphaseidx = 2
            
        if self.Image_Orientation_comboBox.currentIndex() == 0:
            params.imageorientation = 0
        elif self.Image_Orientation_comboBox.currentIndex() == 1:
            params.imageorientation = 1
        elif self.Image_Orientation_comboBox.currentIndex() == 2:
            params.imageorientation = 2
            
        params.FOV = self.FOV_doubleSpinBox.value()
        params.slicethickness = self.Slice_Thickness_doubleSpinBox.value()
        params.GROpretimescaler = self.GRO_Length_Scaler_doubleSpinBox.value()
        params.SPEsteps = self.SPEsteps_spinBox.value()
        
        if params.autograd == 1:
            self.Delta_vpp = params.frequencyrange / (250*params.TS)
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
            self.Gystep = (2* np.pi / params.FOV)/(2 * np.pi * 42.57 * (self.GPEtime/1000000))
            params.GPEstep = int(self.Gystep / self.Gysens * 1000)
            
            self.Achrusher = (4 * np.pi) / (2 * np.pi * 42.57 * params.slicethickness)
            self.Gc = self.Achrusher / ((params.crushertime + 200)/1000000)
            params.crusheramplitude = int(self.Gc / self.Gzsens * 1000)
            
            self.Aspoiler = (4 * np.pi) / (2 * np.pi * 42.57 * params.slicethickness)
            self.Gs = self.Aspoiler / ((params.spoilertime + 200)/1000000)
            params.spoileramplitude = int(self.Gs / self.Gzsens * 1000)
            
            self.Deltaf = 1 / (params.flippulselength) *1000000
            
            self.Gz = (2 * np.pi * self.Deltaf)/(2 * np.pi * 42.57 * (params.slicethickness))
            params.GSamplitude = int(self.Gz / self.Gzsens * 1000)

            self.Gz3D = (2 * np.pi / params.slicethickness)/(2 * np.pi * 42.57 * (self.GPEtime/1000000))
            params.GSPEstep =  int(self.Gz3D / self.Gzsens * 1000)
            print('Auto 3D SlPE max:', params.GSPEstep * params.SPEsteps / 2)
            
            self.update_gradients()
            print('Auto GPE max: ',params.GPEstep * params.nPE / 2)
        
        else:
            self.Gz = 0 
    
        params.Gdiffamplitude = self.GDiffamplitude_spinBox.value()

        params.sliceoffset = self.Slice_Offset_doubleSpinBox.value()
        
        if params.autofreqoffset == 1:
            
            self.Deltafs = (2 * np.pi * 42.57 * self.Gz * params.sliceoffset)/(2 * np.pi)
                
            if self.Deltafs >= 0:
                params.frequencyoffset = int(self.Deltafs)
                params.frequencyoffsetsign = 0
            else:
                params.frequencyoffset = int(abs(self.Deltafs))
                params.frequencyoffsetsign = 1
                
            self.update_freqoffset()
        
        params.phaseoffset = self.Phase_Offset_spinBox.value()
        params.phaseoffsetradmod100 = int((math.radians(params.phaseoffset) % (2*np.pi))*100)
        
        params.radialanglestep = self.Radial_Angle_Step_spinBox.value()
        params.radialanglestepradmod100 = int((math.radians(params.radialanglestep) % (2*np.pi))*100)
        
        if self.ln_kSpace_Magnitude_radioButton.isChecked(): params.lnkspacemag = 1
        else: params.lnkspacemag = 0
        
        if self.RX1_radioButton.isChecked(): params.rx1 = 1
        else: params.rx1 = 0
        if self.RX2_radioButton.isChecked(): params.rx2 = 1
        else: params.rx2 = 0
        
        if params.rx1 == 0 and params.rx2 == 0:
            params.rxmode = 0
            print('\033[1m' + 'Please select RX1 or RX2!' + '\033[0m')
        elif params.rx1 == 1 and params.rx2 == 0:
            params.rxmode = 1
        elif params.rx1 == 0 and params.rx2 == 1:
            params.rxmode = 2
        elif params.rx1 == 1 and params.rx2 == 1:
            params.rxmode = 3
            print('\033[1m' + 'Please select RX1 or RX2!' + '\033[0m')
        print('RX mode: ',params.rxmode)
        
        params.signalmask = self.SignalMask_doubleSpinBox.value()
        
        params.saveFileParameter()
        
    def update_freqoffset(self):
        if params.autofreqoffset == 0:
            
            if self.Frequency_Offset_spinBox.value() >= 0:
                params.frequencyoffset = self.Frequency_Offset_spinBox.value()
                params.frequencyoffsetsign = 0
            else:
                params.frequencyoffset = abs(self.Frequency_Offset_spinBox.value())
                params.frequencyoffsetsign = 1

            params.saveFileParameter()
            
        elif params.autofreqoffset == 1:
            
            if params.frequencyoffsetsign == 0:   
                self.Frequency_Offset_spinBox.setValue(params.frequencyoffset)
            elif params.frequencyoffsetsign == 1:   
                self.Frequency_Offset_spinBox.setValue(-params.frequencyoffset)
        
    def update_gradients(self):
        
        if params.autograd == 0:
        
            params.GPEstep = self.GPEstep_spinBox.value()
            params.GROamplitude = self.GROamplitude_spinBox.value()
            
            params.Gproj[0] = self.GROamplitude_spinBox.value()
            params.Gproj[1] = self.GROamplitude_spinBox.value()
            params.Gproj[2] = self.GROamplitude_spinBox.value()
        
            if params.GROamplitude == 0:
                params.GROpretime = 0
                self.GROfcpretime1 = 0
                self.GROfcpretime2 = 0
            else:
                params.GROpretime = int((params.TS * 1000 / 2 * params.GROamplitude + 200 * params.GROamplitude / 2 - 200 * 2 * params.GROamplitude) / (2 * params.GROamplitude) * params.GROpretimescaler)
                params.GROfcpretime1 = int((((200 * params.GROamplitude + params.TS * 1000 * params.GROamplitude) / 2) - 200 * params.GROamplitude) / params.GROamplitude)
                params.GROfcpretime2 = int(((200 * params.GROamplitude + params.TS * 1000 * params.GROamplitude) - 200 * 2 * params.GROamplitude) / (2 * params.GROamplitude) * params.GROpretimescaler)
        
            params.crusheramplitude = self.Crusher_Amplitude_spinBox.value()
            params.spoileramplitude = self.Spoiler_Amplitude_spinBox.value()
            params.GSamplitude = self.GSamplitude_spinBox.value()
            params.GSPEstep = self.GSPEstep_spinBox.value()
            print('Manual GPE max: ',params.GPEstep * params.nPE / 2)
            
            params.saveFileParameter()
    
        elif params.autograd == 1:
            self.GROamplitude_spinBox.setValue(params.GROamplitude)
            self.GPEstep_spinBox.setValue(params.GPEstep)
            self.Crusher_Amplitude_spinBox.setValue(params.crusheramplitude)
            self.Spoiler_Amplitude_spinBox.setValue(params.spoileramplitude)
            self.GSamplitude_spinBox.setValue(params.GSamplitude)
            self.GSPEstep_spinBox.setValue(params.GSPEstep)
        
        
    def Set_AC_centerfrequency(self):
        params.frequency = params.Reffrequency
        self.Frequency_doubleSpinBox.setValue(params.frequency)
        print('Tool reference frequency applied!')

    def Set_FA_RFattenution(self):
        params.RFattenuation = params.RefRFattenuation
        self.RF_Attenuation_doubleSpinBox.setValue(params.RFattenuation)
        print('Tool reference attenuation applied!')

        
class ToolsWindow(Tools_Window_Form, Tools_Window_Base):

    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ToolsWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.load_params()
        
        self.ui = loadUi('ui/tools.ui')
        self.setWindowTitle('Tools')
        self.setGeometry(10, 40, 800, 850)
        
        self.AC_Start_Frequency_doubleSpinBox.setKeyboardTracking(False)
        self.AC_Start_Frequency_doubleSpinBox.valueChanged.connect(self.update_params)
        self.AC_Stop_Frequency_doubleSpinBox.setKeyboardTracking(False)
        self.AC_Stop_Frequency_doubleSpinBox.valueChanged.connect(self.update_params)
        self.AC_Stepwidth_spinBox.setKeyboardTracking(False)
        self.AC_Stepwidth_spinBox.valueChanged.connect(self.update_params)
        self.FA_Start_Attenuation_doubleSpinBox.setKeyboardTracking(False)
        self.FA_Start_Attenuation_doubleSpinBox.valueChanged.connect(self.update_params)
        self.FA_Stop_Attenuation_doubleSpinBox.setKeyboardTracking(False)
        self.FA_Stop_Attenuation_doubleSpinBox.valueChanged.connect(self.update_params)
        self.FA_Attenuation_Steps_spinBox.setKeyboardTracking(False)
        self.FA_Attenuation_Steps_spinBox.valueChanged.connect(self.update_params)
        self.Autocenter_pushButton.clicked.connect(lambda: self.Autocentertool())
        self.Flipangle_pushButton.clicked.connect(lambda: self.Flipangletool())
        
        self.Tool_Shim_Start_spinBox.setKeyboardTracking(False)
        self.Tool_Shim_Start_spinBox.valueChanged.connect(self.update_params)
        self.Tool_Shim_Stop_spinBox.setKeyboardTracking(False)
        self.Tool_Shim_Stop_spinBox.valueChanged.connect(self.update_params)
        self.Tool_Shim_Steps_spinBox.setKeyboardTracking(False)
        self.Tool_Shim_Steps_spinBox.valueChanged.connect(self.update_params)
        
        self.Tool_Shim_X_radioButton.toggled.connect(self.update_params)
        self.Tool_Shim_Y_radioButton.toggled.connect(self.update_params)
        self.Tool_Shim_Z_radioButton.toggled.connect(self.update_params)
        self.Tool_Shim_Z2_radioButton.toggled.connect(self.update_params)
        
        self.Tool_Shim_pushButton.clicked.connect(lambda: self.Shimtool())
        
        self.Field_Map_B0_pushButton.clicked.connect(lambda: self.Field_Map_B0())
        self.Field_Map_B0_Slice_pushButton.clicked.connect(lambda: self.Field_Map_B0_Slice())
        
        self.Field_Map_B1_pushButton.clicked.connect(lambda: self.Field_Map_B1())
        self.Field_Map_B1_Slice_pushButton.clicked.connect(lambda: self.Field_Map_B1_Slice())
        
        self.Field_Map_Gradient_pushButton.clicked.connect(lambda: self.Field_Map_Gradient())
        self.Field_Map_Gradient_Slice_pushButton.clicked.connect(lambda: self.Field_Map_Gradient_Slice())
        
        self.GradientScaling_XNominal_doubleSpinBox.setKeyboardTracking(False)
        self.GradientScaling_XNominal_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesauto)
        self.GradientScaling_YNominal_doubleSpinBox.setKeyboardTracking(False)
        self.GradientScaling_YNominal_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesauto)
        self.GradientScaling_ZNominal_doubleSpinBox.setKeyboardTracking(False)
        self.GradientScaling_ZNominal_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesauto)
        self.GradientScaling_XMeasured_doubleSpinBox.setKeyboardTracking(False)
        self.GradientScaling_XMeasured_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesauto)
        self.GradientScaling_YMeasured_doubleSpinBox.setKeyboardTracking(False)
        self.GradientScaling_YMeasured_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesauto)
        self.GradientScaling_ZMeasured_doubleSpinBox.setKeyboardTracking(False)
        self.GradientScaling_ZMeasured_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesauto)
        
        self.Gradient_XScaling_doubleSpinBox.setKeyboardTracking(False)
        self.Gradient_XScaling_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesmanual)
        self.Gradient_YScaling_doubleSpinBox.setKeyboardTracking(False)
        self.Gradient_YScaling_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesmanual)
        self.Gradient_ZScaling_doubleSpinBox.setKeyboardTracking(False)
        self.Gradient_ZScaling_doubleSpinBox.valueChanged.connect(self.update_gradsenstoolvaluesmanual)
        
        self.Apply_XScaling_pushButton.clicked.connect(lambda: self.set_gradsens_X())
        self.Apply_YScaling_pushButton.clicked.connect(lambda: self.set_gradsens_Y())
        self.Apply_ZScaling_pushButton.clicked.connect(lambda: self.set_gradsens_Z())
        
    def load_params(self):
        self.AC_Start_Frequency_doubleSpinBox.setValue(params.ACstart)
        self.AC_Stop_Frequency_doubleSpinBox.setValue(params.ACstop)
        self.AC_Stepwidth_spinBox.setValue(params.ACstepwidth)
        self.FA_Start_Attenuation_doubleSpinBox.setValue(params.FAstart)
        self.FA_Stop_Attenuation_doubleSpinBox.setValue(params.FAstop)
        self.FA_Attenuation_Steps_spinBox.setValue(params.FAsteps)
        
        self.Tool_Shim_Start_spinBox.setValue(params.ToolShimStart)
        self.Tool_Shim_Stop_spinBox.setValue(params.ToolShimStop)
        self.Tool_Shim_Steps_spinBox.setValue(params.ToolShimSteps)
        
        if params.ToolShimChannel[0] == 1: self.Tool_Shim_X_radioButton.setChecked(True)
        if params.ToolShimChannel[1] == 1: self.Tool_Shim_Y_radioButton.setChecked(True)
        if params.ToolShimChannel[2] == 1: self.Tool_Shim_Z_radioButton.setChecked(True)
        if params.ToolShimChannel[3] == 1: self.Tool_Shim_Z2_radioButton.setChecked(True)
        
        self.GradientScaling_XNominal_doubleSpinBox.setValue(params.gradnominal[0])
        self.GradientScaling_YNominal_doubleSpinBox.setValue(params.gradnominal[1])
        self.GradientScaling_ZNominal_doubleSpinBox.setValue(params.gradnominal[2])
        
        self.GradientScaling_XMeasured_doubleSpinBox.setValue(params.gradmeasured[0])
        self.GradientScaling_YMeasured_doubleSpinBox.setValue(params.gradmeasured[1])
        self.GradientScaling_ZMeasured_doubleSpinBox.setValue(params.gradmeasured[2])
        
        self.Gradient_XScaling_doubleSpinBox.setValue(params.gradsenstool[0])
        self.Gradient_YScaling_doubleSpinBox.setValue(params.gradsenstool[1])
        self.Gradient_ZScaling_doubleSpinBox.setValue(params.gradsenstool[2])
        
    def update_params(self):
        params.ACstart = self.AC_Start_Frequency_doubleSpinBox.value()
        params.ACstop = self.AC_Stop_Frequency_doubleSpinBox.value()
        params.ACstepwidth = self.AC_Stepwidth_spinBox.value()
        params.FAstart = self.FA_Start_Attenuation_doubleSpinBox.value()
        params.FAstop = self.FA_Stop_Attenuation_doubleSpinBox.value()
        params.FAsteps = self.FA_Attenuation_Steps_spinBox.value()
        
        params.ToolShimStart = self.Tool_Shim_Start_spinBox.value()
        params.ToolShimStop = self.Tool_Shim_Stop_spinBox.value()
        params.ToolShimSteps = self.Tool_Shim_Steps_spinBox.value()
        
        if self.Tool_Shim_X_radioButton.isChecked(): params.ToolShimChannel[0] = 1
        else: params.ToolShimChannel[0] = 0
        if self.Tool_Shim_Y_radioButton.isChecked(): params.ToolShimChannel[1] = 1
        else: params.ToolShimChannel[1] = 0
        if self.Tool_Shim_Z_radioButton.isChecked(): params.ToolShimChannel[2] = 1
        else: params.ToolShimChannel[2] = 0
        if self.Tool_Shim_Z2_radioButton.isChecked(): params.ToolShimChannel[3] = 1
        else: params.ToolShimChannel[3] = 0
        
        params.saveFileParameter()
        
    def update_gradsenstoolvaluesauto(self):
        params.gradnominal[0] = self.GradientScaling_XNominal_doubleSpinBox.value()
        params.gradnominal[1] = self.GradientScaling_YNominal_doubleSpinBox.value()
        params.gradnominal[2] = self.GradientScaling_ZNominal_doubleSpinBox.value()
        params.gradmeasured[0] = self.GradientScaling_XMeasured_doubleSpinBox.value()
        params.gradmeasured[1] = self.GradientScaling_YMeasured_doubleSpinBox.value()
        params.gradmeasured[2] = self.GradientScaling_ZMeasured_doubleSpinBox.value()
        
        params.gradsenstool[0] = params.gradmeasured[0]/params.gradnominal[0] * params.gradsens[0]
        params.gradsenstool[1] = params.gradmeasured[1]/params.gradnominal[1] * params.gradsens[1]
        params.gradsenstool[2] = params.gradmeasured[2]/params.gradnominal[2] * params.gradsens[2]

        self.Gradient_XScaling_doubleSpinBox.setValue(params.gradsenstool[0])
        self.Gradient_YScaling_doubleSpinBox.setValue(params.gradsenstool[1])
        self.Gradient_ZScaling_doubleSpinBox.setValue(params.gradsenstool[2])
        
        params.saveFileParameter()
        
    def update_gradsenstoolvaluesmanual(self):
        params.gradsenstool[0] = self.Gradient_XScaling_doubleSpinBox.value()
        params.gradsenstool[1] = self.Gradient_YScaling_doubleSpinBox.value()
        params.gradsenstool[2] = self.Gradient_ZScaling_doubleSpinBox.value()
        
        params.saveFileParameter()
        
    def set_gradsens_X(self):
        print('Set X gradient sensitivity from ' + str(params.gradsens[0]) + 'mT/m/A to ' + str(params.gradsenstool[0]) + 'mT/m/A!')
        
        params.gradsens[0] = params.gradsenstool[0]
        
        params.saveFileParameter()
        
    def set_gradsens_Y(self):
        print('Set Y gradient sensitivity from ' + str(params.gradsens[1]) + 'mT/m/A to ' + str(params.gradsenstool[1]) + 'mT/m/A!')
        
        params.gradsens[1] = params.gradsenstool[1]
        
        params.saveFileParameter()
        
    def set_gradsens_Z(self):
        print('Set Z gradient sensitivity from ' + str(params.gradsens[2]) + 'mT/m/A to ' + str(params.gradsenstool[2]) + 'mT/m/A!')
        
        params.gradsens[2] = params.gradsenstool[2]
        
        params.saveFileParameter()
        
        
    def Autocentertool(self):
        if params.connectionmode == 1:
            self.flippulselengthtemp = params.flippulselength
            params.flippulselength = params.RFpulselength
        
            proc.Autocentertool()
            
            self.fig = Figure()
            self.fig.set_facecolor("None")
            self.fig_canvas = FigureCanvas(self.fig)
        
            self.ax = self.fig.add_subplot(111);
            self.ax.plot(params.ACvalues[0,:], params.ACvalues[1,:], 'o', color='#000000')
            self.ax.set_xlabel('Frequency [MHz]')
            self.ax.set_ylabel('Signal')
            self.ax.set_title('Autocenter Signals')
            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(820, 40, 800, 750)
            self.fig_canvas.show()
            self.AC_Reffrequency_lineEdit.setText(str(params.Reffrequency))
        
            params.flippulselength = self.flippulselengthtemp
        else: print('Not allowed in offline mode!')
        
    def Flipangletool(self):
        if params.connectionmode == 1:
            self.flippulselengthtemp = params.flippulselength
            params.flippulselength = params.RFpulselength
        
            proc.Flipangletool()
        
            self.fig = Figure()
            self.fig.set_facecolor("None")
            self.fig_canvas = FigureCanvas(self.fig)
        
            self.ax = self.fig.add_subplot(111);
            self.ax.plot(params.FAvalues[0,:], params.FAvalues[1,:], 'o-', color='#000000')
            self.ax.set_xlabel('Attenuation [dB]')
            self.ax.set_ylabel('Signal')
            self.ax.set_title('Flipangle Signals')
            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(820, 40, 800, 750)
            self.fig_canvas.show()
            self.FA_RefRFattenuation_lineEdit.setText(str(params.RefRFattenuation))
        
            params.flippulselength = self.flippulselengthtemp
        else: print('Not allowed in offline mode!')
        
    def Shimtool(self):
        if params.connectionmode == 1:
            if params.ToolShimChannel != [0, 0, 0, 0]:
        
                proc.Shimtool()
                
                self.fig = Figure()
                self.fig.set_facecolor("None")
                self.fig_canvas = FigureCanvas(self.fig)
        
                self.ax = self.fig.add_subplot(111);
                self.ax.plot(np.transpose(params.STvalues[0,:]), np.transpose(params.STvalues[1,:]), 'o-', color='#0072BD')
                self.ax.plot(np.transpose(params.STvalues[0,:]), np.transpose(params.STvalues[2,:]), 'o-', color='#D95319')
                self.ax.plot(np.transpose(params.STvalues[0,:]), np.transpose(params.STvalues[3,:]), 'o-', color='#EDB120')
                self.ax.plot(np.transpose(params.STvalues[0,:]), np.transpose(params.STvalues[4,:]), 'o-', color='#7E2F8E')
                self.ax.set_xlabel('Shim [mA]')
                self.ax.set_ylabel('Signal')
                self.ax.legend(['X','Y','Z','Z²'])
                self.ax.set_title('Shim Signals')
                self.fig_canvas.draw()
                self.fig_canvas.setWindowTitle('Tool Plot')
                self.fig_canvas.setGeometry(820, 40, 800, 750)
                self.fig_canvas.show()
        
                if params.ToolShimChannel[0] == 1:
                    self.Tool_Shim_X_Ref_lineEdit.setText(str(params.STvalues[0,np.argmax(params.STvalues[1,:])]))
                else: self.Tool_Shim_X_Ref_lineEdit.setText(' ')
                if params.ToolShimChannel[1] == 1:
                    self.Tool_Shim_Y_Ref_lineEdit.setText(str(params.STvalues[0,np.argmax(params.STvalues[2,:])]))
                else: self.Tool_Shim_Y_Ref_lineEdit.setText(' ')
                if params.ToolShimChannel[2] == 1:
                    self.Tool_Shim_Z_Ref_lineEdit.setText(str(params.STvalues[0,np.argmax(params.STvalues[3,:])]))
                else: self.Tool_Shim_Z_Ref_lineEdit.setText(' ')
                if params.ToolShimChannel[3] == 1:
                    self.Tool_Shim_Z2_Ref_lineEdit.setText(str(params.STvalues[0,np.argmax(params.STvalues[4,:])]))
                else: self.Tool_Shim_Z2_Ref_lineEdit.setText(' ')
        
            else: print('Please select gradient channel')
        else: print('Not allowed in offline mode!')

    def Field_Map_B0(self):
        if params.connectionmode == 1:
            print('\033[1m' + 'WIP Field_Map_B0' + '\033[0m')
            
            proc.FieldMapB0()
            
            #self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor("None")
            #self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            #self.IMag_ax.imshow(params.img_mag, cmap='viridis'); self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            #self.IMag_ax.set_title('Magnitude Image')
            #self.IMag_canvas.draw()
            #self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            #self.IMag_canvas.setGeometry(820, 40, 400, 355)
            #self.IMag_canvas.show()
            
            self.IPha_fig = Figure(); self.IPha_canvas = FigureCanvas(self.IPha_fig); self.IPha_fig.set_facecolor("None")
            self.IPha_ax = self.IPha_fig.add_subplot(111); self.IPha_ax.grid(False); self.IPha_ax.axis(frameon=False)
            self.IPha_ax.imshow(params.img_pha, cmap='gray'); self.IPha_ax.axis('off'); self.IPha_ax.set_aspect(1.0/self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            self.IPha_canvas.draw()
            self.IPha_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            self.IPha_canvas.setGeometry(820, 40, 400, 355)
            self.IPha_canvas.show()
            
            self.FMB0_fig = Figure(); self.FMB0_canvas = FigureCanvas(self.FMB0_fig); self.FMB0_fig.set_facecolor("None")
            self.FMB0_ax = self.FMB0_fig.add_subplot(111); self.FMB0_ax.grid(False); self.FMB0_ax.axis(frameon=False)
            self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet'); self.FMB0_ax.axis('off'); self.FMB0_ax.set_aspect(1.0/self.FMB0_ax.get_data_ratio())
            self.FMB0_ax.set_title('\u0394 B0 Map')
            self.FMB0_fig_cbar = self.FMB0_fig.colorbar(self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet'))
            self.FMB0_fig_cbar.set_label('\u0394 B0 in µT', rotation=90)
            self.FMB0_canvas.draw()
            self.FMB0_canvas.setWindowTitle('Tool Plot')
            self.FMB0_canvas.setGeometry(1230, 40, 400, 355)
            self.FMB0_canvas.show()

        else: print('Not allowed in offline mode!')

    def Field_Map_B0_Slice(self):
        if params.connectionmode == 1:
            print('\033[1m' + 'WIP Field_Map_B0_Slice' + '\033[0m')
            
            proc.FieldMapB0Slice()
            
            #self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor("None")
            #self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            #self.IMag_ax.imshow(params.img_mag, cmap='viridis'); self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            #self.IMag_ax.set_title('Magnitude Image')
            #self.IMag_canvas.draw()
            #self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            #self.IMag_canvas.setGeometry(820, 40, 400, 355)
            #self.IMag_canvas.show()
            
            self.IPha_fig = Figure(); self.IPha_canvas = FigureCanvas(self.IPha_fig); self.IPha_fig.set_facecolor("None")
            self.IPha_ax = self.IPha_fig.add_subplot(111); self.IPha_ax.grid(False); self.IPha_ax.axis(frameon=False)
            self.IPha_ax.imshow(params.img_pha, cmap='gray'); self.IPha_ax.axis('off'); self.IPha_ax.set_aspect(1.0/self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            self.IPha_canvas.draw()
            self.IPha_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            self.IPha_canvas.setGeometry(820, 40, 400, 355)
            self.IPha_canvas.show()
            
            self.FMB0_fig = Figure(); self.FMB0_canvas = FigureCanvas(self.FMB0_fig); self.FMB0_fig.set_facecolor("None")
            self.FMB0_ax = self.FMB0_fig.add_subplot(111); self.FMB0_ax.grid(False); self.FMB0_ax.axis(frameon=False)
            self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet'); self.FMB0_ax.axis('off'); self.FMB0_ax.set_aspect(1.0/self.FMB0_ax.get_data_ratio())
            self.FMB0_ax.set_title('\u0394 B0 Map')
            self.FMB0_fig_cbar = self.FMB0_fig.colorbar(self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet'))
            self.FMB0_fig_cbar.set_label('\u0394 B0 in uT', rotation=90)
            self.FMB0_canvas.draw()
            self.FMB0_canvas.setWindowTitle('Tool Plot')
            self.FMB0_canvas.setGeometry(1230, 40, 400, 355)
            self.FMB0_canvas.show()
            
        else: print('Not allowed in offline mode!')

    def Field_Map_B1(self):
        if params.connectionmode == 1:
            print('\033[1m' + 'WIP Field_Map_B1' + '\033[0m')
            
            proc.FieldMapB1()
            
            self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor("None");
            self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='viridis')
            else: self.IMag_ax.imshow(params.img_mag, cmap='viridis')
            self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(820, 40, 400, 355)
            self.IMag_canvas.show()
            
            self.FMB1_fig = Figure(); self.FMB1_canvas = FigureCanvas(self.FMB1_fig); self.FMB1_fig.set_facecolor("None");
            self.FMB1_ax = self.FMB1_fig.add_subplot(111); self.FMB1_ax.grid(False); self.FMB1_ax.axis(frameon=False)
            self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet'); self.FMB1_ax.axis('off'); self.FMB1_ax.set_aspect(1.0/self.FMB1_ax.get_data_ratio())
            self.FMB1_ax.set_title('Flip Angle Map')
            self.FMB1_fig_cbar = self.FMB1_fig.colorbar(self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet'))
            self.FMB1_fig_cbar.set_label('\u03B1 in deg', rotation=90)
            self.FMB1_canvas.draw()
            self.FMB1_canvas.setWindowTitle('Tool Plot')
            self.FMB1_canvas.setGeometry(1230, 40, 400, 355)
            self.FMB1_canvas.show()
            
        else: print('Not allowed in offline mode!')

    def Field_Map_B1_Slice(self):
        if params.connectionmode == 1:
            print('\033[1m' + 'WIP Field_Map_B1_Slice' + '\033[0m')
            
            proc.FieldMapB1Slice()
            
            self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor("None")
            self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='viridis')
            else: self.IMag_ax.imshow(params.img_mag, cmap='viridis')
            self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(820, 40, 400, 355)
            self.IMag_canvas.show()
            
            self.FMB1_fig = Figure(); self.FMB1_canvas = FigureCanvas(self.FMB1_fig); self.FMB1_fig.set_facecolor("None")
            self.FMB1_ax = self.FMB1_fig.add_subplot(111); self.FMB1_ax.grid(False); self.FMB1_ax.axis(frameon=False)
            self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet'); self.FMB1_ax.axis('off'); self.FMB1_ax.set_aspect(1.0/self.FMB1_ax.get_data_ratio())
            self.FMB1_ax.set_title('Flip Angle Map')
            self.FMB1_fig_cbar = self.FMB1_fig.colorbar(self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet'))
            self.FMB1_fig_cbar.set_label('\u03B1 in deg', rotation=90)
            self.FMB1_canvas.draw()
            self.FMB1_canvas.setWindowTitle('Tool Plot')
            self.FMB1_canvas.setGeometry(1230, 40, 400, 355)
            self.FMB1_canvas.show()
            
        else: print('Not allowed in offline mode!')

    def Field_Map_Gradient(self):
        if params.connectionmode == 1:
            print('\033[1m' + 'WIP Field_Map_Gradient' + '\033[0m')
            
            proc.FieldMapGradient()
            
            self.IMag_fig = Figure()
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            self.IMag_fig.set_facecolor("None")
            self.IMag_ax = self.IMag_fig.add_subplot(111)
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='viridis', extent=[(-params.FOV/2),(params.FOV/2),(-params.FOV/2),(params.FOV/2)])
            else: self.IMag_ax.imshow(params.img_mag, cmap='viridis', extent=[(-params.FOV/2),(params.FOV/2),(-params.FOV/2),(params.FOV/2)])
            self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.major_ticks = np.linspace(math.ceil((-params.FOV/2)),math.floor((params.FOV/2)),math.floor((params.FOV/2))-math.ceil((-params.FOV/2))+1)
            self.minor_ticks = np.linspace((math.ceil((-params.FOV/2)*5))/5,(math.floor((params.FOV/2)*5))/5,math.floor((params.FOV/2)*5)-math.ceil((-params.FOV/2)*5)+1)
            self.IMag_ax.set_xticks(self.major_ticks)
            self.IMag_ax.set_xticks(self.minor_ticks, minor=True)
            self.IMag_ax.set_yticks(self.major_ticks)
            self.IMag_ax.set_yticks(self.minor_ticks, minor=True)
            self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='--')
            self.IMag_ax.grid(which='minor', color='#CCCCCC', linestyle=':')
            
            if params.imageorientation == 0:
                self.IMag_ax.set_xlabel('X in mm')
                self.IMag_ax.set_ylabel('Y in mm')
            elif params.imageorientation == 1:
                self.IMag_ax.set_xlabel('Y in mm')
                self.IMag_ax.set_ylabel('Z in mm')
            elif params.imageorientation == 2:
                self.IMag_ax.set_xlabel('Z in mm')
                self.IMag_ax.set_ylabel('X in mm')
                
            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(820, 40, 800, 750)
            self.IMag_canvas.show()
            
        else: print('Not allowed in offline mode!')

    def Field_Map_Gradient_Slice(self):
        if params.connectionmode == 1:
            print('\033[1m' + 'WIP Field_Map_Gradient_Slice' + '\033[0m')
            
            proc.FieldMapGradientSlice()
            
            self.IMag_fig = Figure()
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            self.IMag_fig.set_facecolor("None")
            self.IMag_ax = self.IMag_fig.add_subplot(111)
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='viridis', extent=[(-params.FOV/2),(params.FOV/2),(-params.FOV/2),(params.FOV/2)])
            else: self.IMag_ax.imshow(params.img_mag, cmap='viridis', extent=[(-params.FOV/2),(params.FOV/2),(-params.FOV/2),(params.FOV/2)])
            self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.major_ticks = np.linspace(math.ceil((-params.FOV/2)),math.floor((params.FOV/2)),math.floor((params.FOV/2))-math.ceil((-params.FOV/2))+1)
            self.minor_ticks = np.linspace((math.ceil((-params.FOV/2)*5))/5,(math.floor((params.FOV/2)*5))/5,math.floor((params.FOV/2)*5)-math.ceil((-params.FOV/2)*5)+1)
            self.IMag_ax.set_xticks(self.major_ticks)
            self.IMag_ax.set_xticks(self.minor_ticks, minor=True)
            self.IMag_ax.set_yticks(self.major_ticks)
            self.IMag_ax.set_yticks(self.minor_ticks, minor=True)
            self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='--')
            self.IMag_ax.grid(which='minor', color='#CCCCCC', linestyle=':')
            
            if params.imageorientation == 0:
                self.IMag_ax.set_xlabel('X in mm')
                self.IMag_ax.set_ylabel('Y in mm')
            elif params.imageorientation == 1:
                self.IMag_ax.set_xlabel('Y in mm')
                self.IMag_ax.set_ylabel('Z in mm')
            elif params.imageorientation == 2:
                self.IMag_ax.set_xlabel('Z in mm')
                self.IMag_ax.set_ylabel('X in mm')
                
            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(820, 40, 800, 750)
            self.IMag_canvas.show()
            
        else: print('Not allowed in offline mode!')
        
class ProtocolWindow(Protocol_Window_Form, Protocol_Window_Base):

    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ProtocolWindow, self).__init__(parent)
        self.setupUi(self)
        
        #self.load_params()
        self.prot_datapath = 'protocol/Protocol_01'
        
        self.ui = loadUi('ui/protocol.ui')
        self.setWindowTitle('Protocol')
        self.setGeometry(420, 40, 800, 850)
        
        self.Protocol_Datapath_lineEdit.setText(self.prot_datapath)
        self.Protocol_Datapath_lineEdit.editingFinished.connect(lambda: self.set_protocol_datapath())
        
        self.protocol_new_protocol()
        
        self.Protocol_Add_pushButton.clicked.connect(lambda: self.protocol_add())
        self.Protocol_Overwrite_pushButton.clicked.connect(lambda: self.protocol_overwrite())
        self.Protocol_Insert_pushButton.clicked.connect(lambda: self.protocol_insert())
        self.Protocol_Delete_Last_pushButton.clicked.connect(lambda: self.protocol_delete_last())
        self.Protocol_Delete_pushButton.clicked.connect(lambda: self.protocol_delete())
        self.Protocol_Save_Protocol_pushButton.clicked.connect(lambda: self.protocol_save_protocol())
        self.Protocol_New_Protocol_pushButton.clicked.connect(lambda: self.protocol_new_protocol())
        self.Protocol_Load_Protocol_pushButton.clicked.connect(lambda: self.protocol_load_protocol())
        self.Protocol_Execute_Protocol_pushButton.clicked.connect(lambda: self.protocol_execute_protocol())
        
    def set_protocol_datapath(self):
        self.prot_datapath = self.Protocol_Datapath_lineEdit.text()
        #print('Protocol datapath:', self.prot_datapath)
        
    def protocol_add(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0]+1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0],:] = self.protocol[:,:]
        self.protocoltemp[self.protocoltemp.shape[0]-2,0] = params.GUImode
        self.protocoltemp[self.protocoltemp.shape[0]-2,1] = params.sequence
        self.protocol = self.protocoltemp
        
        try:
            shutil.copyfile('parameters.pkl',self.prot_datapath + '_' + str(self.protocol.shape[0]-1) + '_parameters.pkl')
            time.sleep(0.001)
        except: print('No parameter file.')
        
        self.protocol_plot_table()
        
    def protocol_delete_last(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0]-1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0]-1,:] = self.protocol[0:self.protocol.shape[0]-1,:]
        self.protocol = self.protocoltemp
        
        try:
            os.remove(self.prot_datapath + '_' + str(self.protocol.shape[0]) + '_parameters.pkl')
            time.sleep(0.001)
        except: print('No parameter file.')
        
        self.protocol_plot_table()
        
    def protocol_insert(self):
        if self.Protocol_Number_spinBox.value()-1 <= self.protocoltemp.shape[0]-1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0]+1, self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value()-1,:] = self.protocol[0:self.Protocol_Number_spinBox.value()-1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value()-1,0] = params.GUImode
            self.protocoltemp[self.Protocol_Number_spinBox.value()-1,1] = params.sequence
            self.protocoltemp[self.Protocol_Number_spinBox.value():self.protocoltemp.shape[0]-1,:] = self.protocol[self.Protocol_Number_spinBox.value()-1:self.protocol.shape[0]-1,:]
            self.protocol = self.protocoltemp
            
            for n in range(self.Protocol_Number_spinBox.value(),self.protocol.shape[0]-1):
                try:
                    shutil.copyfile(self.prot_datapath + '_' + str(n) + '_parameters.pkl',self.prot_datapath + '_' + str(n) + '_parameters_temp.pkl')
                    time.sleep(0.001)
                except: print('No parameter file.')
            shutil.copyfile('parameters.pkl',self.prot_datapath + '_' + str(self.Protocol_Number_spinBox.value()) + '_parameters.pkl')
            time.sleep(0.001)
            for n in range(self.Protocol_Number_spinBox.value()+1,self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '_' + str(n-1) + '_parameters_temp.pkl',self.prot_datapath + '_' + str(n) + '_parameters.pkl')
                    time.sleep(0.001)
                    os.remove(self.prot_datapath + '_' + str(n-1) + '_parameters_temp.pkl')
                    time.sleep(0.001)
                except: print('No parameter file.')
                
        else: print('Index to high!')
        
        self.protocol_plot_table()
        
    def protocol_delete(self):
        if self.Protocol_Number_spinBox.value() <= self.protocoltemp.shape[0]-1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0], self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value()-1,:] = self.protocol[0:self.Protocol_Number_spinBox.value()-1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value()-1:self.protocoltemp.shape[0]-2,:] = self.protocol[self.Protocol_Number_spinBox.value():self.protocol.shape[0]-1,:]
            self.protocol = np.matrix(np.zeros((self.protocoltemp.shape[0]-1, self.protocoltemp.shape[1])))
            self.protocol = self.protocoltemp[0:self.protocoltemp.shape[0]-1,:]
            
            for n in range(self.Protocol_Number_spinBox.value(),self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '_' + str(n+1) + '_parameters.pkl',self.prot_datapath + '_' + str(n) + '_parameters.pkl')
                    time.sleep(0.001)
                except: print('No parameter file.')
            try:
                os.remove(self.prot_datapath + '_' + str(self.protocol.shape[0]) + '_parameters.pkl')
                time.sleep(0.001)
            except: print('No parameter file.')
        
        else: print('Index to high!')
        
        self.protocol_plot_table()
        
    def protocol_overwrite(self):
        if self.Protocol_Number_spinBox.value()-1 <= self.protocoltemp.shape[0]-2:
            self.protocol[self.Protocol_Number_spinBox.value()-1,0] = params.GUImode
            self.protocol[self.Protocol_Number_spinBox.value()-1,1] = params.sequence
            
            try:
                shutil.copyfile('parameters.pkl',self.prot_datapath + '_' + str(self.Protocol_Number_spinBox.value()) + '_parameters.pkl')
                time.sleep(0.001)
            except: print('No parameter file.')
            
        else: print('Index to high!')
        
        self.protocol_plot_table()
    
    def protocol_plot_table(self):
        self.Protocol_Table_tableWidget.setRowCount(self.protocol.shape[0]-1)
        self.Protocol_Table_tableWidget.setColumnCount(self.protocol.shape[1])
        self.Protocol_Table_tableWidget.setHorizontalHeaderLabels(('Mode','Sequence'))
        for n in range(self.protocol.shape[0]-1):
            for m in range(self.protocol.shape[1]):
                self.Protocol_Table_tableWidget.setItem(n,m,QTableWidgetItem(str(int(self.protocol[n,m]))))
        self.Protocol_Table_tableWidget.show()
        
    def protocol_save_protocol(self):
        np.savetxt(self.prot_datapath + '.txt', self.protocol[0:self.protocol.shape[0]-1,:])
        print('Protocol saved!')
        
    def protocol_new_protocol(self):
        self.protocol = np.matrix([0,0])
        
        self.protocol_plot_table()
        
    def protocol_load_protocol(self):
        self.protocoltemp = np.genfromtxt(self.prot_datapath + '.txt')
        self.protocol = np.matrix(np.zeros((self.protocoltemp.shape[0]+1, self.protocoltemp.shape[1])))
        self.protocol[0:self.protocoltemp.shape[0],:] = self.protocoltemp[:,:]
        print(self.protocol)
        print(self.protocol.shape)
        
        self.protocol_plot_table()
        
    def protocol_execute_protocol(self):
        print('WIP')
        for n in range(self.protocol.shape[0]-1):
            print(n)
            try:
                shutil.copyfile(self.prot_datapath + '_' + str(n+1) + '_parameters.pkl','parameters.pkl')
                time.sleep(0.001)
            except: print('No parameter file.')
            
            params.loadParam()
            
            params.datapath = self.prot_datapath + '_' + str(n+1) + '_rawdata'
            
            self.protocol_acquire()
            
            time.sleep(params.TR/1000)
            
    def protocol_acquire(self):
        if params.connectionmode == 1:
            if params.GUImode == 2 and params.sequence == 0:
                proc.T1measurement_IR_FID()
            elif params.GUImode == 2 and params.sequence == 1:
                proc.T1measurement_IR_SE()
            elif params.GUImode == 2 and params.sequence == 2:
                proc.T1measurement_IR_FID_Gs()
            elif params.GUImode == 2 and params.sequence == 3:
                proc.T1measurement_IR_SE_Gs()
            elif params.GUImode == 2 and params.sequence == 4:
                proc.T1measurement_Image_IR_GRE()
            elif params.GUImode == 2 and params.sequence == 5:
                proc.T1measurement_Image_IR_SE()
            elif params.GUImode == 2 and params.sequence == 6:
                proc.T1measurement_Image_IR_GRE_Gs()
            elif params.GUImode == 2 and params.sequence == 7:
                proc.T1measurement_Image_IR_SE_Gs()
            elif params.GUImode == 3 and params.sequence == 0:
                proc.T2measurement_SE()
            elif params.GUImode == 3 and params.sequence == 1:
                proc.T2measurement_SIR_FID()
            elif params.GUImode == 3 and params.sequence == 2:
                proc.T2measurement_SE_Gs()
            elif params.GUImode == 3 and params.sequence == 3:
                proc.T2measurement_SIR_FID_Gs()
            elif params.GUImode == 3 and params.sequence == 4:
                proc.T2measurement_Image_SE()
            elif params.GUImode == 3 and params.sequence == 5:
                proc.T2measurement_Image_SIR_GRE()
            elif params.GUImode == 3 and params.sequence == 6:
                proc.T2measurement_Image_SE_Gs()
            elif params.GUImode == 3 and params.sequence == 7:
                proc.T2measurement_Image_SIR_GRE_Gs()
            elif params.GUImode == 1:
                if params.autorecenter == 1:
                    if params.sequence == 0 or params.sequence == 2 or params.sequence == 4 \
                       or params.sequence == 7 or params.sequence == 9 or params.sequence == 12 \
                       or params.sequence == 15:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        seq.sequence_upload()
                    elif params.sequence == 17 or params.sequence == 19 or params.sequence == 21 \
                         or params.sequence == 24 or params.sequence == 26 or params.sequence == 29 \
                         or params.sequence == 32:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        seq.sequence_upload()
                    elif params.sequence == 1 or params.sequence == 3 or params.sequence == 5 \
                         or params.sequence == 6 or params.sequence == 8 or params.sequence == 10 \
                         or params.sequence == 11 or params.sequence == 13 or params.sequence == 14 \
                         or params.sequence == 16:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        #seq.sequence_upload()
                    elif params.sequence == 18 or params.sequence == 20 or params.sequence == 22 \
                         or params.sequence == 23 or params.sequence == 25 or params.sequence == 27 \
                         or params.sequence == 28 or params.sequence == 30 or params.sequence == 31 \
                         or params.sequence == 33 or params.sequence == 34 or params.sequence == 35 \
                         or params.sequence == 36:
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
                        if self.dialog_params != None:
                            self.dialog_params.load_params()
                            self.dialog_params.repaint()
                        time.sleep(params.TR/1000)
                        seq.sequence_upload()
                else: seq.sequence_upload()
            else: seq.sequence_upload()
            if self.dialog_params != None:
                self.dialog_params.load_params()
                self.dialog_params.repaint()
        else: print('\033[1m' + 'Not allowed in offline mode!' + '\033[0m')


class PlotWindow(Plot_Window_Form, Plot_Window_Base):

    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(PlotWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.load_params()
        
        self.ui = loadUi('ui/plotview.ui')
        self.setWindowTitle('Plotvalues - ' + params.datapath + '.txt')
        self.setGeometry(10, 490, 400, 400)
          
        if params.GUImode == 0:
            self.spectrum_plot_init()
        elif params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36:
                self.imaging_3D_plot_init()
            elif params.sequence == 14 or params.sequence == 31:
                self.imaging_diff_plot_init()
            else:
                self.imaging_plot_init()
                
        elif params.GUImode == 2:
            if params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3:
                self.T1_plot_init()
            else:
                self.T1_imaging_plot_init()
                
        elif params.GUImode == 3:
            if params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3:
                self.T2_plot_init()
            else:
                self.T2_imaging_plot_init()
            
        elif params.GUImode == 4:
            if params.sequence == 0 or params.sequence == 1:
                params.frequencyplotrange = 250000
                self.Frequncyaxisrange_spinBox.setValue(params.frequencyplotrange)
                self.projection_plot_init()
            elif params.sequence == 2 or params.sequence == 3:
                params.frequencyplotrange = 250000
                self.Frequncyaxisrange_spinBox.setValue(params.frequencyplotrange)
                self.spectrum_plot_init()

        self.Frequncyaxisrange_spinBox.setKeyboardTracking(False)
        self.Frequncyaxisrange_spinBox.valueChanged.connect(self.update_params)
        
        self.Save_Mag_Image_Data_pushButton.clicked.connect(lambda: self.save_mag_image_data())
        self.Save_Pha_Image_Data_pushButton.clicked.connect(lambda: self.save_pha_image_data())
        self.Save_Image_Data_pushButton.clicked.connect(lambda: self.save_image_data())
        
        self.Animation_Step_spinBox.setKeyboardTracking(False)
        self.Animation_Step_spinBox.valueChanged.connect(self.update_params)
        self.Animate_pushButton.clicked.connect(lambda: self.animate())

    def load_params(self):
        if params.GUImode == 0:
            self.Frequncyaxisrange_spinBox.setEnabled(True)
            self.Frequncyaxisrange_spinBox.setValue(params.frequencyplotrange)
            self.Center_Frequency_lineEdit.setText(str(params.centerfrequency))
            self.FWHM_lineEdit.setText(str(params.FWHM))
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Inhomogeneity_lineEdit.setText(str(params.inhomogeneity))
            self.Animation_Step_spinBox.setValue(params.animationstep)
        elif params.GUImode == 1:
            self.Frequncyaxisrange_spinBox.setEnabled(False)
            self.Frequncyaxisrange_spinBox.setValue(250000)
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Animation_Step_spinBox.setValue(params.animationstep)

        
    def update_params(self):
        params.frequencyplotrange = self.Frequncyaxisrange_spinBox.value()
        params.animationstep = self.Animation_Step_spinBox.value()
        
        params.saveFileParameter()
        
        if params.GUImode == 0:
            self.spectrum_plot_init()
        elif params.GUImode == 4:
            self.projection_plot_init()
            
    def spectrum_plot_init(self):
        self.fig = Figure()   
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        
        self.ax1 = self.fig.add_subplot(2,1,1)
        self.ax2 = self.fig.add_subplot(2,1,2)
        
        self.ax1.plot(params.freqencyaxis, params.spectrumfft)
        self.ax1.set_xlim([-params.frequencyplotrange/2,params.frequencyplotrange/2])
        self.ax1.set_title('Spectrum')
        self.ax1.set_ylabel('RX Signal [arb.]')
        self.ax1.set_xlabel('$\Delta$ Frequency [Hz]')                         
        self.ax2.plot(params.timeaxis, params.mag, label='Magnitude')
        self.ax2.plot(params.timeaxis, params.real, label='Real')
        self.ax2.plot(params.timeaxis, params.imag, label='Imaginary')
        self.ax2.set_title('Signal')
        self.ax2.set_ylabel('RX Signal [mV]')
        self.ax2.set_xlabel('time [ms]')
        self.ax2.legend()
        self.ax2.plot(params.timeaxis, params.mag, label='Magnitude')
        
        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 800, 750)
        self.fig_canvas.show()
        
    def projection_plot_init(self):
        self.fig = Figure()   
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        
        if params.projx.shape[0] == params.freqencyaxis.shape[0]:
            self.ax1 = self.fig.add_subplot(6,1,1)
            self.ax2 = self.fig.add_subplot(6,1,2)
            
            self.ax1.plot(params.freqencyaxis, params.projx[:,3])
            self.ax1.set_xlim([-params.frequencyplotrange/2,params.frequencyplotrange/2])
            self.ax1.set_title('X - Spectrum')
            self.ax1.set_ylabel('RX Signal [arb.]')
            self.ax1.set_xlabel('$\Delta$ Frequency [Hz]')                            
            self.ax2.plot(params.timeaxis, params.projx[:,0], label='Magnitude')
            self.ax2.plot(params.timeaxis, params.projx[:,1], label='Real')
            self.ax2.plot(params.timeaxis, params.projx[:,2], label='Imaginary')
            self.ax2.set_title('X - Signal')
            self.ax2.set_ylabel('RX Signal [mV]')
            self.ax2.set_xlabel('time [ms]')
            self.ax2.legend()
            self.ax2.plot(params.timeaxis, params.projx[:,0], label='Magnitude')
            
        if params.projy.shape[0] == params.freqencyaxis.shape[0]:
            self.ax3 = self.fig.add_subplot(6,1,3)
            self.ax4 = self.fig.add_subplot(6,1,4)
            
            self.ax3.plot(params.freqencyaxis, params.projy[:,3])
            self.ax3.set_xlim([-params.frequencyplotrange/2,params.frequencyplotrange/2])
            self.ax3.set_title('Y - Spectrum')
            self.ax3.set_ylabel('RX Signal [arb.]')
            self.ax3.set_xlabel('$\Delta$ Frequency [Hz]')                            
            self.ax4.plot(params.timeaxis, params.projy[:,0], label='Magnitude')
            self.ax4.plot(params.timeaxis, params.projy[:,1], label='Real')
            self.ax4.plot(params.timeaxis, params.projy[:,2], label='Imaginary')
            self.ax4.set_title('Y - Signal')
            self.ax4.set_ylabel('RX Signal [mV]')
            self.ax4.set_xlabel('time [ms]')
            self.ax4.legend()
            self.ax4.plot(params.timeaxis, params.projy[:,0], label='Magnitude')
        
        if params.projz.shape[0] == params.freqencyaxis.shape[0]:
            self.ax5 = self.fig.add_subplot(6,1,5)
            self.ax6 = self.fig.add_subplot(6,1,6)
            self.ax5.plot(params.freqencyaxis, params.projz[:,3])
            self.ax5.set_xlim([-params.frequencyplotrange/2,params.frequencyplotrange/2])
            self.ax5.set_title('Z - Spectrum')
            self.ax5.set_ylabel('RX Signal [arb.]')
            self.ax5.set_xlabel('$\Delta$ Frequency [Hz]')                            
            self.ax6.plot(params.timeaxis, params.projz[:,0], label='Magnitude')
            self.ax6.plot(params.timeaxis, params.projz[:,1], label='Real')
            self.ax6.plot(params.timeaxis, params.projz[:,2], label='Imaginary')
            self.ax6.set_title('Z - Signal')
            self.ax6.set_ylabel('RX Signal [mV]')
            self.ax6.set_xlabel('time [ms]')
            self.ax6.legend()
            self.ax6.plot(params.timeaxis, params.projz[:,0], label='Magnitude')
        
        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 600, 750)
        self.fig_canvas.show()
        
                    
        if os.path.isfile(params.datapath + '_0.txt') == True and os.path.isfile(params.datapath + '_2.txt') == True:
                
            self.projzx = np.matrix(np.zeros((params.projz.shape[0],params.projx.shape[0])))
            self.projzx = params.projx[:,3] * np.transpose(params.projz[:,3])
                
            self.IMag_fig = Figure()
            self.IMag_fig.set_facecolor("None")
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            
            self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            self.IMag_ax.imshow(self.projzx[int(self.projzx.shape[0]/2-params.nPE/2):int(self.projzx.shape[0]/2+params.nPE/2),int(self.projzx.shape[1]/2-params.nPE/2):int(self.projzx.shape[1]/2+params.nPE/2)], cmap='gray'); self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            
            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(1030, 40, 400, 355)
            self.IMag_canvas.show()
            
    def T1_plot_init(self):
        self.fig1 = Figure()
        self.fig1.set_facecolor("None")
        self.fig_canvas1 = FigureCanvas(self.fig1)
        
        self.ax = self.fig1.add_subplot(111);
        
        self.ax.plot(params.T1xvalues, params.T1yvalues1, 'o', color='#000000', label = 'Measurement Data')
        self.ax.plot(params.T1xvalues, params.T1regyvalues1, color='#00BB00', label = 'Fit')
        self.ax.set_xlabel('TI')
        self.ax.set_ylabel('Signal')
        self.ax.legend()
        self.ax.set_title('T1 = ' + str(params.T1) + 'ms, r = '+ str(round(params.T1linregres.rvalue,2)))

        self.fig_canvas1.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas1.setGeometry(420, 40, 400, 355)
        self.fig_canvas1.show()
        
        self.fig2 = Figure()
        self.fig2.set_facecolor("None")
        self.fig_canvas2 = FigureCanvas(self.fig2)
        
        self.ax = self.fig2.add_subplot(111);
        
        self.ax.plot(params.T1xvalues, params.T1yvalues2, 'o', color='#000000', label = 'Measurement Data')
        self.ax.plot(params.T1xvalues, params.T1regyvalues2, color='#00BB00', label = 'Fit')
        self.ax.set_xlabel('TI')
        self.ax.set_ylabel('ln(Signal_max - Signal)')
        self.ax.legend()
        self.ax.set_title('T1 = ' + str(params.T1) + 'ms, r = '+ str(round(params.T1linregres.rvalue,2)))
        
        self.fig_canvas2.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas2.setGeometry(830, 40, 400, 355)
        self.fig_canvas2.show()
        
    def T1_imaging_plot_init(self):
        self.IComb_fig = Figure(); self.IComb_canvas = FigureCanvas(self.IComb_fig); self.IComb_fig.set_facecolor("None");
        self.IComb_ax = self.IComb_fig.add_subplot(111); self.IComb_ax.grid(False); self.IComb_ax.axis(frameon=False)
        if params.imagefilter == 1:
            self.IComb_ax.imshow(params.T1img_mag[params.T1img_mag.shape[0]-1,:,:], interpolation='gaussian', cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T1imgvalues, interpolation='gaussian', cmap='jet', alpha=0.5)
        else:
            self.IComb_ax.imshow(params.T1img_mag[params.T1img_mag.shape[0]-1,:,:], cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T1imgvalues, cmap='jet', alpha=0.5)
        self.IComb_ax.axis('off'); self.IComb_ax.set_aspect(1.0/self.IComb_ax.get_data_ratio())
        self.IComb_ax.set_title('T1')
        self.IComb_fig.colorbar(self.cb, label='T1 in ms')
        self.IComb_canvas.draw()
        self.IComb_canvas.setWindowTitle('Plot - ' + params.datapath + '_Image_Magnitude.txt')
        self.IComb_canvas.setGeometry(420, 40, 800, 750)
        self.IComb_canvas.show()
        
    def T2_plot_init(self):
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        
        self.ax = self.fig.add_subplot(111);
        
        self.ax.plot(params.T2xvalues, params.T2yvalues, 'o', color='#000000', label = 'Measurement Data')
        self.ax.plot(params.T2xvalues, params.T2regyvalues, color='#00BB00', label = 'Fit')
        self.ax.set_xlabel('TE')
        self.ax.set_ylabel('ln(Signal)')
        self.ax.legend()
        self.ax.set_title('T2 = ' + str(params.T2) + 'ms, r = '+ str(round(params.T2linregres.rvalue,2)))
        
        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 400, 355)
        self.fig_canvas.show()
        
    def T2_imaging_plot_init(self):
        self.IComb_fig = Figure(); self.IComb_canvas = FigureCanvas(self.IComb_fig); self.IComb_fig.set_facecolor("None");
        self.IComb_ax = self.IComb_fig.add_subplot(111); self.IComb_ax.grid(False); self.IComb_ax.axis(frameon=False)
        if params.imagefilter == 1:
            self.IComb_ax.imshow(params.T2img_mag[0,:,:], interpolation='gaussian', cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T2imgvalues, interpolation='gaussian', cmap='jet', alpha=0.5)
        else:
            self.IComb_ax.imshow(params.T2img_mag[0,:,:], cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T2imgvalues, cmap='jet', alpha=0.5)
        self.IComb_ax.axis('off'); self.IComb_ax.set_aspect(1.0/self.IComb_ax.get_data_ratio())
        self.IComb_ax.set_title('T2')
        self.IComb_fig.colorbar(self.cb, label='T2 in ms')
        self.IComb_canvas.draw()
        self.IComb_canvas.setWindowTitle('Plot - ' + params.datapath + '_Image_Magnitude.txt')
        self.IComb_canvas.setGeometry(420, 40, 800, 750)
        self.IComb_canvas.show()

    def imaging_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor("None");
            self.IPha_fig = Figure(); self.IPha_canvas = FigureCanvas(self.IPha_fig); self.IPha_fig.set_facecolor("None");
            self.kMag_fig = Figure(); self.kMag_canvas = FigureCanvas(self.kMag_fig); self.kMag_fig.set_facecolor("None");
            self.kPha_fig = Figure(); self.kPha_canvas = FigureCanvas(self.kPha_fig); self.kPha_fig.set_facecolor("None");
            
            self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.IPha_fig.add_subplot(111); self.IPha_ax.grid(False); self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.kMag_fig.add_subplot(111); self.kMag_ax.grid(False); self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.kPha_fig.add_subplot(111); self.kPha_ax.grid(False); self.kPha_ax.axis(frameon=False)
            
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='viridis')
            else: self.IMag_ax.imshow(params.img_mag, cmap='viridis')
            self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IPha_ax.imshow(params.img_pha, cmap='gray'); self.IPha_ax.axis('off'); self.IPha_ax.set_aspect(1.0/self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno'); self.kPha_ax.axis('off'); self.kPha_ax.set_aspect(1.0/self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')
        
            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(420, 40, 400, 355)
            self.IPha_canvas.draw()
            self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IPha_canvas.setGeometry(830, 40, 400, 355)
            self.kMag_canvas.draw()
            self.kMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.kMag_canvas.setGeometry(420, 435, 400, 355)
            self.kPha_canvas.draw()
            self.kPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.kPha_canvas.setGeometry(830, 435, 400, 355)

            self.IMag_canvas.show()
            self.IPha_canvas.show()
            self.kMag_canvas.show()
            self.kPha_canvas.show()
            
        else:
            self.all_fig = Figure(); self.all_canvas = FigureCanvas(self.all_fig); self.all_fig.set_facecolor("None");
            
            gs = GridSpec(2, 2, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(gs[0,0]); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[0,1]); self.IPha_ax.grid(False); self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.all_fig.add_subplot(gs[1,0]); self.kMag_ax.grid(False); self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.all_fig.add_subplot(gs[1,1]); self.kPha_ax.grid(False); self.kPha_ax.axis(frameon=False)
            
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='viridis')
            else: self.IMag_ax.imshow(params.img_mag, cmap='viridis')
            self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IPha_ax.imshow(params.img_pha, cmap='gray'); self.IPha_ax.axis('off'); self.IPha_ax.set_aspect(1.0/self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno'); self.kPha_ax.axis('off'); self.kPha_ax.set_aspect(1.0/self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')
            
            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 800, 750)
            self.all_canvas.show()
            
    def imaging_3D_plot_init(self):
        self.all_fig = Figure(); self.all_canvas = FigureCanvas(self.all_fig); self.all_fig.set_facecolor("None");
            
        gs = GridSpec(4, params.img_mag.shape[0], figure=self.all_fig)
        for n in range(params.img_mag.shape[0]):
            self.IMag_ax = self.all_fig.add_subplot(gs[0,n]); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[1,n]); self.IPha_ax.grid(False); self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.all_fig.add_subplot(gs[2,n]); self.kMag_ax.grid(False); self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.all_fig.add_subplot(gs[3,n]); self.kPha_ax.grid(False); self.kPha_ax.axis(frameon=False)
            
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag[n,:,:], interpolation='gaussian', cmap='viridis')
            else: self.IMag_ax.imshow(params.img_mag[n,:,:], cmap='viridis')
            self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
        #self.IMag_ax.set_title('Magnitude Image')
            self.IPha_ax.imshow(params.img_pha[n,:,:], cmap='gray'); self.IPha_ax.axis('off'); self.IPha_ax.set_aspect(1.0/self.IPha_ax.get_data_ratio())
        #self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp[n,:,:]), cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
            else:
                self.kMag_ax.imshow(params.k_amp[n,:,:], cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
        #self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha[n,:,:], cmap='inferno'); self.kPha_ax.axis('off'); self.kPha_ax.set_aspect(1.0/self.kPha_ax.get_data_ratio())
        #self.kPha_ax.set_title('k-Space Phase')
            
        self.all_canvas.draw()
        self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.all_canvas.setGeometry(420, 40, 800, 750)
        self.all_canvas.show()
        
    def imaging_diff_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor("None");
            self.IDiff_fig = Figure(); self.IDiff_canvas = FigureCanvas(self.IDiff_fig); self.IDiff_fig.set_facecolor("None");
            self.IComb_fig = Figure(); self.IComb_canvas = FigureCanvas(self.IComb_fig); self.IComb_fig.set_facecolor("None");
            self.IPha_fig = Figure(); self.IPha_canvas = FigureCanvas(self.IPha_fig); self.IPha_fig.set_facecolor("None");
            self.kMag_fig = Figure(); self.kMag_canvas = FigureCanvas(self.kMag_fig); self.kMag_fig.set_facecolor("None");
            self.kPha_fig = Figure(); self.kPha_canvas = FigureCanvas(self.kPha_fig); self.kPha_fig.set_facecolor("None");
            
            self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            self.IDiff_ax = self.IDiff_fig.add_subplot(111); self.IDiff_ax.grid(False); self.IDiff_ax.axis(frameon=False)
            self.IComb_ax = self.IComb_fig.add_subplot(111); self.IComb_ax.grid(False); self.IComb_ax.axis(frameon=False)
            self.IPha_ax = self.IPha_fig.add_subplot(111); self.IPha_ax.grid(False); self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.kMag_fig.add_subplot(111); self.kMag_ax.grid(False); self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.kPha_fig.add_subplot(111); self.kPha_ax.grid(False); self.kPha_ax.axis(frameon=False)
            
            
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
            else: self.IMag_ax.imshow(params.img_mag, cmap='gray')
            self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:self.IDiff_aximshow(params.img_mag_diff, interpolation='gaussian', cmap='jet')
            else: self.IDiff_ax.imshow(params.img_mag_diff, cmap='jet')
            self.IDiff_ax.axis('off'); self.IDiff_ax.set_aspect(1.0/self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, interpolation='gaussian', cmap='jet', alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap='jet', alpha=0.5)
            self.IComb_ax.axis('off'); self.IComb_ax.set_aspect(1.0/self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
            self.IPha_ax.imshow(params.img_pha, cmap='gray'); self.IPha_ax.axis('off'); self.IPha_ax.set_aspect(1.0/self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno'); self.kPha_ax.axis('off'); self.kPha_ax.set_aspect(1.0/self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')
        
            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(420, 40, 400, 355)
            self.IDiff_canvas.draw()
            self.IDiff_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IDiff_canvas.setGeometry(830, 40, 400, 355)
            self.IComb_canvas.draw()
            self.IComb_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IComb_canvas.setGeometry(1240, 40, 400, 355)
            self.IPha_canvas.draw()
            self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IPha_canvas.setGeometry(420, 435, 400, 355)
            self.kMag_canvas.draw()
            self.kMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.kMag_canvas.setGeometry(830, 435, 400, 355)
            self.kPha_canvas.draw()
            self.kPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.kPha_canvas.setGeometry(1240, 435, 400, 355)

            self.IMag_canvas.show()
            self.IDiff_canvas.show()
            self.IComb_canvas.show()
            self.IPha_canvas.show()
            self.kMag_canvas.show()
            self.kPha_canvas.show()
            
        else:
            self.all_fig = Figure(); self.all_canvas = FigureCanvas(self.all_fig); self.all_fig.set_facecolor("None");
            
            gs = GridSpec(2, 3, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(gs[0,0]); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
            self.IDiff_ax = self.all_fig.add_subplot(gs[0,1]); self.IDiff_ax.grid(False); self.IDiff_ax.axis(frameon=False)
            self.IComb_ax = self.all_fig.add_subplot(gs[0,2]); self.IComb_ax.grid(False); self.IComb_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[1,0]); self.IPha_ax.grid(False); self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.all_fig.add_subplot(gs[1,1]); self.kMag_ax.grid(False); self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.all_fig.add_subplot(gs[1,2]); self.kPha_ax.grid(False); self.kPha_ax.axis(frameon=False)
            
            if params.imagefilter == 1:self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
            else: self.IMag_ax.imshow(params.img_mag, cmap='gray')
            self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:self.IDiff_aximshow(params.img_mag_diff, interpolation='gaussian', cmap='jet')
            else: self.IDiff_ax.imshow(params.img_mag_diff, cmap='jet')
            self.IDiff_ax.axis('off'); self.IDiff_ax.set_aspect(1.0/self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, interpolation='gaussian', cmap='jet', alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap='jet', alpha=0.5)
            self.IComb_ax.axis('off'); self.IComb_ax.set_aspect(1.0/self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
            self.IPha_ax.imshow(params.img_pha, cmap='gray'); self.IPha_ax.axis('off'); self.IPha_ax.set_aspect(1.0/self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno'); self.kMag_ax.axis('off'); self.kMag_ax.set_aspect(1.0/self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno'); self.kPha_ax.axis('off'); self.kPha_ax.set_aspect(1.0/self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')
            
            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1300, 750)
            self.all_canvas.show()
            
    def save_mag_image_data(self):
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 0:
            self.datatxt = np.matrix(np.zeros((params.freqencyaxis.shape[0],2)))
            self.datatxt[:,0] = params.freqencyaxis.reshape(params.freqencyaxis.shape[0],1)
            self.datatxt[:,1] = params.spectrumfft
            np.savetxt('imagedata/' + params.dataTimestamp + '_Spectrum_Image_Data.txt', self.datatxt)
            print('Spectrum image data saved!')
        elif params.GUImode == 1:
            if params.sequence == 32 or params.sequence == 33 or params.sequence == 34:
                self.datatxt = np.matrix(np.zeros((params.img_mag.shape[1],params.img_mag.shape[0]*params.img_mag.shape[2])))
                for m in range(params.img_mag.shape[0]):
                    self.datatxt[:,m*params.img_mag.shape[2]:m*params.img_mag.shape[2]+params.img_mag.shape[2]] = params.img_mag[m,:,:]
                np.savetxt('imagedata/' + params.dataTimestamp + '_3D_' + str(params.img_mag.shape[0]) + '_Magnitude_Image_Data.txt', self.datatxt)
                print('Magnitude 3D image data saved!')
            elif params.sequence == 13 or params.sequence == 29:
                print('WIP!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Data.txt', params.img_mag)
                print('Magnitude image data saved!')
        elif params.GUImode == 2:
            self.datatxt = np.matrix(np.zeros((params.T1xvalues.shape[0],3)))
            self.datatxt[:,0] = params.T1xvalues.reshape(params.T1xvalues.shape[0],1)
            self.datatxt[:,1] = params.T1yvalues1.reshape(params.T1yvalues1.shape[0],1)
            self.datatxt[:,2] = params.T1regyvalues1.reshape(params.T1regyvalues1.shape[0],1)
            np.savetxt('imagedata/' + params.dataTimestamp + '_T1_Image_Data.txt', self.datatxt)
            print('T1 image data saved!')
        elif params.GUImode == 3:
            self.datatxt = np.matrix(np.zeros((params.T2xvalues.shape[0],3)))
            self.datatxt[:,0] = params.T2xvalues.reshape(params.T2xvalues.shape[0],1)
            self.datatxt[:,1] = params.T2yvalues.reshape(params.T2yvalues.shape[0],1)
            self.datatxt[:,2] = params.T2regyvalues.reshape(params.T2regyvalues.shape[0],1)
            np.savetxt('imagedata/' + params.dataTimestamp + '_T2_Image_Data.txt', self.datatxt)
            print('T2 image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
            
    def save_pha_image_data(self):
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 0:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 1:
            if params.sequence == 32 or params.sequence == 33 or params.sequence == 34:
                self.datatxt = np.matrix(np.zeros((params.img_pha.shape[1],params.img_pha.shape[0]*params.img_pha.shape[2])))
                for m in range(params.img_pha.shape[0]):
                    self.datatxt[:,m*params.img_pha.shape[2]:m*params.img_pha.shape[2]+params.img_pha.shape[2]] = params.img_pha[m,:,:]
                np.savetxt('imagedata/' + params.dataTimestamp + '_3D_' + str(params.img_pha.shape[0]) + '_Phase_Image_Data.txt', self.datatxt)
                print('Magnitude 3D image data saved!')
            elif params.sequence == 13 or params.sequence == 29:
                print('WIP!')
            else:
                np.savetxt('imagedata/'+ params.dataTimestamp + '_Phase_Image_Data.txt', params.img_pha)
                print('Phase image data saved!')
        elif params.GUImode == 2:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 3:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 4:
            print('WIP!')
            
    def save_image_data(self):
        timestamp = datetime.now() 
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 0:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 1:
            if params.sequence == 32 or params.sequence == 33 or params.sequence == 34:
                self.datatxt = np.matrix(np.zeros((params.img.shape[1],params.img.shape[0]*params.img.shape[2]), dtype = np.complex64))
                for m in range(params.img.shape[0]):
                    self.datatxt[:,m*params.img.shape[2]:m*params.img.shape[2]+params.img.shape[2]] = params.img[m,:,:]
                np.savetxt('imagedata/' + params.dataTimestamp + '_3D_' + str(params.img.shape[0]) + '_Image_Data.txt', self.datatxt)
                print('Magnitude 3D image data saved!')
            elif params.sequence == 13 or params.sequence == 29:
                print('WIP!')
            else:
                np.savetxt('imagedata/'+ params.dataTimestamp + '_Image_Data.txt', params.img)
                print('Image data saved!')
        elif params.GUImode == 2:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 3:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 4:
            print('WIP!')
            
    def animate(self):
        proc.animation_image_process()
        
        import matplotlib.animation as animation
        
        fig = plt.figure()
       
        im = plt.imshow(params.animationimage[params.kspace.shape[0]-1,:,:], cmap='gray',animated=True)
        plt.axis('off')
        def updatefig(i):
            im.set_array(params.animationimage[i,:,:])
            return im,
        ani = animation.FuncAnimation(fig, updatefig, frames = params.kspace.shape[0], interval = params.animationstep, blit=True)
        plt.show()
        
        
        

class ConnectionDialog(Conn_Dialog_Base, Conn_Dialog_Form):

    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ConnectionDialog, self).__init__(parent)
        self.setupUi(self)

        self.ui = loadUi('ui/connDialog.ui')
        self.setGeometry(10, 40, 500, 250)
        self.ui.closeEvent = self.closeEvent
        self.conn_help = QPixmap('ui/connection_help.png')
        self.help.setVisible(False)

        self.conn_btn.clicked.connect(self.connect_event) 
        self.addIP_btn.clicked.connect(self.add_IP)
        self.rmIP_btn.clicked.connect(self.remove_IP)
        self.offmod_btn.clicked.connect(self.offlinemode)
        self.status_label.setVisible(False)

        IPvalidator = QRegExp(
            '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)'
            '{3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
        self.ip_box.setValidator(QRegExpValidator(IPvalidator, self))
        for item in params.hosts: self.ip_box.addItem(item)

        self.mainwindow = parent

    def connect_event(self):
        params.ip = self.ip_box.currentText()
        print(params.ip)

        connection = seq.conn_client()

        if connection:
            params.connectionmode = 1
            params.saveFileParameter()
            self.status_label.setText('Connected.')
            self.connected.emit()
            self.mainwindow.show()
            self.close()

        elif not connection:
            params.connectionmode = 0
            params.saveFileParameter()
            self.status_label.setText('Not connected.')
            self.conn_btn.setText('Retry')
            self.help.setPixmap(self.conn_help)
            self.help.setVisible(True)
        else:
            params.connectionmode = 0
            params.saveFileParameter()
            self.status_label.setText('Not connected with status: '+str(connection))
            self.conn_btn.setText('Retry')
            self.help.setPixmap(self.conn_help)
            self.help.setVisible(True)

        self.status_label.setVisible(True)

    def add_IP(self):
        print("Add ip address.")
        ip = self.ip_box.currentText()

        if not ip in params.hosts: self.ip_box.addItem(ip)
        else: return

        params.hosts = [self.ip_box.itemText(i) for i in range(self.ip_box.count())]
        print(params.hosts)

    def remove_IP(self):
        idx = self.ip_box.currentIndex()
        try:
            del params.hosts[idx]
            self.ip_box.removeItem(idx)
        except: pass
        print(params.hosts)
        
    def offlinemode(self):
        self.mainwindow.show()
        self.close()

def run():

    print("\n________________________________________________________\n",\
    "Relax 2.0. \n",\
    "Programmed by Marcus Prier and David Schote, Magdeburg, 2021\n",\
    "\n________________________________________________________\n")

    app = QApplication(sys.argv)
    gui = MainWindow()

    sys.exit(app.exec_())

if __name__ == '__main__':
    run()
