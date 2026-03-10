################################################################################
#
# Author: Marcus Prier
# Date: 2026
#
################################################################################

import sys
import csv
import numpy as np
import os
import math
import time
import datetime
import shutil

import serial
import serial.tools.list_ports
import asyncio
import zlib
import struct
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtWidgets import QDesktopWidget
from enum import Enum

import json

# import PyQt5 packages
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtSerialPort import QSerialPortInfo, QSerialPort
from PyQt5.QtWidgets import QMessageBox, QApplication, QFileDialog, QDesktopWidget, QFrame, QTableWidget, QTableWidgetItem
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QRegExp, pyqtSignal, QStandardPaths, QIODevice, QObject, QTimer, QUrl
from PyQt5.QtGui import QRegExpValidator, QPixmap, QDesktopServices

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.image import NonUniformImage

print('________________________________________________________\n')
print('Relax 2.0')
print('Marcus Prier, Magdeburg, 2026')
print('________________________________________________________\n')

from parameter_handler import params
params.loadParam()
params.loadData()
from sequence_handler import seq
from process_handler import proc
from data_logger import logger

plt.rc('axes', prop_cycle=params.cycler)
plt.rcParams['lines.linewidth'] = 2
plt.rcParams['axes.grid'] = True
plt.rcParams['figure.autolayout'] = True
plt.rcParams['figure.dpi'] = 75
plt.rcParams['legend.loc'] = 'upper right'
plt.rcParams['toolbar'] = 'toolbar2'

Main_Window_Form, Main_Window_Base = loadUiType('ui/mainwindow.ui')
Conn_Dialog_Form, Conn_Dialog_Base = loadUiType('ui/connDialog.ui')
Para_Window_Form, Para_Window_Base = loadUiType('ui/parameters.ui')
Config_Window_Form, Config_Window_Base = loadUiType('ui/config.ui')
AgriMRI_Window_Form, AgriMRI_Window_Base = loadUiType('ui/agriMRI.ui')
Plot_Window_Form, Plot_Window_Base = loadUiType('ui/plotview.ui')
Tools_Window_Form, Tools_Window_Base = loadUiType('ui/tools.ui')
Protocol_Window_Form, Protocol_Window_Base = loadUiType('ui/protocol.ui')
SAR_Window_Form, SAR_Window_Base = loadUiType('ui/sar.ui')
Motor_Window_Form, Motor_Window_Base = loadUiType('ui/motor_tools.ui')
View3D_Dialog_Form, View3D_Dialog_Base = loadUiType('ui/view_3D.ui')


class MainWindow(Main_Window_Base, Main_Window_Form):
    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.dialog_params = None
        self.dialog_config = None
        self.dialog_plot = None
        self.dialog_tools = None
        self.dialog_prot = None
        self.dialog_sarmonitor = None
        self.dialog_motortools = None
        self.dialog_agri = None

        self.ui = loadUi('ui/mainwindow.ui')
        self.setWindowTitle('Relax 2.0')
        params.load_GUItheme()
        self.setStyleSheet(params.stylesheet)
        self.setStyleSheet(self.styleSheet() + "\n* { font-family: 'Piboto Condensed', 'Arial Narrow'; font-size: 16px;}")
        self.setGeometry(10, 40, 400, 410)
        
        params.GUImode = 0
        params.sequence = 0
        params.sequencefile = ''
        params.projaxis = np.zeros(3)
        params.usmethode = 1
        params.ustime = 0
        params.usphase = 0
        params.ustimeidx = 2
        params.usphaseidx = 2
        params.flipangletime = 90
        params.flipangleamplitude = 90
        params.RFpulseamplitude = 16382
        params.flippulseamplitude = 16382
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
        params.ToolAutoShimMode = 0
        params.STgrad = [0, 0, 0, 0, 0]
        params.SAR_status = 1
        params.motor_available = 0
        params.motor_actual_position = 0
        params.motor_goto_position = 0
        
        if params.agriMRI_mode == 1:
            params.AgriMRI_var_init()
        
        self.motor = None
        self.motor_reader = None
        
        if params.motor_enable:
            self.motor_connect()
            
        self.establish_conn()

        if params.GSamplitude == 0:
            params.GSposttime = 0
        else:
            params.GSposttime = int((200 * params.GSamplitude + 4 * params.flippulselength * params.GSamplitude) / 2 - 200 * params.GSamplitude / 2) / (params.GSamplitude / 2)

        self.Mode_Spectroscopy_pushButton.clicked.connect(lambda: self.switch_GUImode(0))
        self.Mode_Imaging_pushButton.clicked.connect(lambda: self.switch_GUImode(1))
        self.Mode_T1_Measurement_pushButton.clicked.connect(lambda: self.switch_GUImode(2))
        self.Mode_T2_Measurement_pushButton.clicked.connect(lambda: self.switch_GUImode(3))
        self.Mode_Projections_pushButton.clicked.connect(lambda: self.switch_GUImode(4))
        self.Mode_Image_Stitching_pushButton.clicked.connect(lambda: self.switch_GUImode(5))
        self.Tools_pushButton.clicked.connect(lambda: self.tools())
        self.Protocol_pushButton.clicked.connect(lambda: self.protocol())
        
        self.AgriMRI_Metadata_pushButton.clicked.connect(lambda: self.agri_window())

        self.Sequence_comboBox.clear()
        self.Sequence_comboBox.addItems(['Please select mode!'])
        self.Sequence_comboBox.currentIndexChanged.connect(self.set_sequence)
        
        self.Parameters_pushButton.clicked.connect(lambda: self.parameter_window())
        self.Acquire_pushButton.clicked.connect(lambda: self.acquire())
        self.Data_Process_pushButton.clicked.connect(lambda: self.dataprocess())

        self.Config_pushButton.clicked.connect(lambda: self.config_window())
        self.SAR_Monitor_pushButton.clicked.connect(lambda: self.sarmonitor())
        self.Motor_Tools_pushButton.clicked.connect(lambda: self.motor_tools())

        self.Datapath_lineEdit.editingFinished.connect(lambda: self.set_Datapath())

    def motor_connect(self):
        ports = list(serial.tools.list_ports.comports())
        
        for port in ports:
            try:
                self.motor = serial.Serial(port.device, 115200, timeout=0.5)
                time.sleep(1)
                mes = 'M115\r\n'
                
                if self.motor.inWaiting() == 0:
                    self.motor.write(mes.encode('utf-8'))
                    response = self.motor.readline()
                    
                    if 'MRI-Patient-Motor-Control' in response.decode('utf-8'):
                        mes_limit = 'M203 ' + str(params.motor_axis_limit_negative) + ' ' + str(params.motor_axis_limit_positive) + '\r\n'
                        self.motor.write(mes_limit.encode('utf-8'))
                        
                        self.motor_reader = SerialReader(self.motor, type=SerialReader.Type.MOTOR)
                        self.motor_reader.data_received.connect(lambda msg: self.motor_read(msg))
                        
                        mes_home = 'G28\r\n'
                        self.motor.write(mes_home.encode('utf-8'))
                        mes_home_response = 'M118 R0: homing finished\r\n'
                        self.motor.write(mes_home_response.encode('utf-8'))
                        
                        print(f'Motor connected to port: {port}')
                        return
                    else:
                        self.motor.close()
                        print(f'Motor not available on port: {port}')
                else:
                    self.motor.close()
                    print(f'Motor not available on port: {port}')
            except Exception as e:
                print(f'Could not write to port: {port} - {e}')

    def motor_read(self, msg):
        if 'R0: homing finished' in msg:
            params.motor_available = 1

            if self.dialog_motortools is not None:
                self.dialog_motortools.load_params()
                self.dialog_motortools.repaint()

            print('Motor Control: Homing finished.')
        elif 'R0: finished moving' in msg:
            params.motor_available = 1

            if self.dialog_motortools is not None:
                self.dialog_motortools.load_params()
                self.dialog_motortools.repaint()
        elif 'E0' in msg:
            self.motor_error(-1, message=msg[4:])

    def motor_error(self, error, message=''):
        # 0: there is no error, 12: not defined but can also occur during normal operation
        if error != 12 and error != 0:
            params.motor_available = False

            if self.dialog_motortools is not None:
                self.dialog_motortools.load_params()
                self.dialog_motortools.repaint()

            if error == -1:
                error_message = 'Device Side Error: ' + message
            elif error == 1:
                error_message = 'Device not found.'
            elif error == 2:
                error_message = 'Permission Error - Device already open somewhere else.'
            elif error == 3:
                error_message = 'Open Error - Device already open in this object.'
            elif error == 4:
                error_message = 'Write Error.'
            elif error == 5:
                error_message = 'Read Error.'
            elif error == 6:
                error_message = 'Resource Error - Device probably disconnected.'
            elif error == 7:
                error_message = 'Unsupported Operation.'
            elif error == 9:
                error_message = 'Timeout Error.'
            elif error == 10:
                error_message = 'Not Open Error.'
            else:
                error_message = 'Unknown Error.'

            print('Motor Control: Error detected, Control will be unavailable until at least the next restart of relax2, Error Number: ' + str(error) + ', Message: ' + error_message)
        else:
            self.motor.clearError()
            self.motor.blockSignals(False)

    def establish_conn(self):
        self.dialog_con = ConnectionDialog(self)
        self.dialog_con.show()
        self.dialog_con.connected.connect(self.start_com)

    def start_com(self):
        logger.init()

    def switch_GUImode(self, mode):
        params.GUImode = mode

        print('GUImode: ' + str(params.GUImode))

        if params.GUImode == 0:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Free Induction Decay', 'Spin Echo', 'Inversion Recovery (FID)' \
                                            , 'Inversion Recovery (SE)', 'Saturation Inversion Recovery (FID)', 'Saturation Inversion Recovery (SE)' \
                                            , 'Echo Planar Spectrum (FID, 4 Echos)', 'Echo Planar Spectrum (SE, 4 Echos)', 'Turbo Spin Echo (4 Echos)' \
                                            , 'Free Induction Decay (Slice)', 'Spin Echo (Slice)', 'Inversion Recovery (FID, Slice)' \
                                            , 'Inversion Recovery (SE, Slice)', 'Saturation Inversion Recovery (FID, Slice)', 'Saturation Inversion Recovery (SE, Slice)' \
                                            , 'Echo Planar Spectrum (FID, 4 Echos, Slice)', 'Echo Planar Spectrum (SE, 4 Echos, Slice)', 'Turbo Spin Echo (4 Echos, Slice)' \
                                            , 'RF Loopback Test Sequence (Rect, Flip)', 'RF Loopback Test Sequence (Rect, 180°)', 'RF Loopback Test Sequence (Sinc, Flip)' \
                                            , 'RF Loopback Test Sequence (Sinc, 180°)', 'RF Loopback Test Sequence (Rect, inverse Flip)', 'RF Loopback Test Sequence (Rect, inverse 180°)' \
                                            , 'RF Loopback Test Sequence (Sinc, inverse Flip)', 'RF Loopback Test Sequence (Sinc, inverse 180°)', 'Gradient Test Sequence' \
                                            , 'RF SAR Calibration Test Sequence'])
            self.Sequence_comboBox.setCurrentIndex(0)
            if params.agriMRI_mode == 1: params.datapath = 'Spectrum_rawdata'
            else: params.datapath = 'rawdata/Spectrum_rawdata'
            self.Datapath_lineEdit.setText(params.datapath)
        elif params.GUImode == 1:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['2D Radial (GRE, Full)', '2D Radial (SE, Full)', '2D Radial (GRE, Half)' \
                                            , '2D Radial (SE, Half)', '2D Gradient Echo', '2D Spin Echo' \
                                            , '2D Spin Echo (InOut)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                            , '2D Saturation Inversion Recovery (GRE)', 'WIP 2D Saturation Inversion Recovery (SE)' \
                                            , '2D Turbo Spin Echo (4 Echos)', '2D Echo Planar Imaging (GRE, 4 Echos)', '2D Echo Planar Imaging (SE, 4 Echos)' \
                                            , '2D Diffusion (SE)', '2D Flow Compensation (GRE)', '2D Flow Compensation (SE)' \
                                            , '2D Radial (Slice, GRE, Full)', '2D Radial (Slice, SE, Full)', '2D Radial (Slice, GRE, Half)' \
                                            , '2D Radial (Slice, SE, Half)', '2D Gradient Echo (Slice)', '2D Spin Echo (Slice)' \
                                            , '2D Spin Echo (Slice, InOut)', '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)' \
                                            , 'WIP 2D Saturation Inversion Recovery (Slice, GRE)', 'WIP 2D Saturation Inversion Recovery (Slice, SE)', '2D Turbo Spin Echo (Slice, 4 Echos)' \
                                            , 'WIP 2D Echo Planar Imaging (Slice, GRE, 4 Echos)', 'WIP 2D Echo Planar Imaging (Slice, SE, 4 Echos)', '2D Diffusion (Slice, SE)' \
                                            , 'WIP 2D Flow Compensation (Slice, GRE)', 'WIP 2D Flow Compensation (Slice, SE)', 'WIP 3D FFT Gradient Echo (Slab)' \
                                            , '3D FFT Spin Echo (Slab)', '3D FFT Turbo Spin Echo (Slab)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            if params.agriMRI_mode == 1: params.datapath = 'Image_rawdata'
            else: params.datapath = 'rawdata/Image_rawdata'
            self.Datapath_lineEdit.setText(params.datapath)
        elif params.GUImode == 2:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Inversion Recovery (FID)', 'Inversion Recovery (SE)', 'Inversion Recovery (Slice, FID)' \
                                            , 'Inversion Recovery (Slice, SE)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            if params.agriMRI_mode == 1: params.datapath = 'T1_rawdata'
            else: params.datapath = 'rawdata/T1_rawdata'
            self.Datapath_lineEdit.setText(params.datapath)
        elif params.GUImode == 3:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Spin Echo', 'Saturation Inversion Recovery (FID)', 'Spin Echo (Slice)' \
                                            , 'Saturation Inversion Recovery (Slice, FID)', '2D Spin Echo', '2D Saturation Inversion Recovery (GRE)' \
                                            , '2D Spin Echo (Slice)', '2D Saturation Inversion Recovery (Slice, GRE)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            if params.agriMRI_mode == 1: params.datapath = 'T2_rawdata'
            else: params.datapath = 'rawdata/T2_rawdata'
            self.Datapath_lineEdit.setText(params.datapath)
        elif params.GUImode == 4:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Gradient Echo (On Axis)', 'Spin Echo (On Axis)', 'Gradient Echo (On Angle)' \
                                            , 'Spin Echo (On Angle)', 'Gradient Echo (Slice, On Axis)', 'Spin Echo (Slice, On Axis)' \
                                            , 'Gradient Echo (Slice, On Angle)', 'Spin Echo (Slice, On Angle)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            if params.agriMRI_mode == 1: params.datapath = 'Projection_rawdata'
            else: params.datapath = 'rawdata/Projection_rawdata'
            self.Datapath_lineEdit.setText(params.datapath)
        elif params.GUImode == 5:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['2D Gradient Echo', '2D Inversion Recovery (GRE)', '2D Spin Echo' \
                                            , '2D Inversion Recovery (SE)', '2D Turbo Spin Echo (4 Echos)', '2D Gradient Echo (Slice)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Spin Echo (Slice)', '2D Inversion Recovery (Slice, SE)' \
                                            , '2D Turbo Spin Echo (Slice, 4 Echos)', '3D FFT Spin Echo (Slab)', '3D FFT Turbo Spin Echo (Slab)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            if params.agriMRI_mode == 1: params.datapath = 'Image_Stitching_rawdata'
            else: params.datapath = 'rawdata/Image_Stitching_rawdata'
            self.Datapath_lineEdit.setText(params.datapath)

    def set_sequence(self, idx):
        params.sequence = idx
        if params.sequence != -1: print('Sequence: ' + str(params.sequence))

        params.saveFileParameter()

    def acquire(self):
        self.Acquire_pushButton.setEnabled(False)
        if params.autodataprocess == 1: self.Data_Process_pushButton.setEnabled(False)
        self.repaint()
        
        if params.agriMRI_mode == 1:
            self.datapath_temp = ''
            self.datapath_temp = params.datapath
            self.agriMRI_folder_structure_temp = ''
            self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
            
            if params.agriMRI_folder_structure != 'rawdata/':
                if os.path.isfile(params.agriMRI_folder_structure + 'AgriMRI_Metadata.json') == True:
                    msg_box_agriMRI_header = QMessageBox()
                    msg_box_agriMRI_header.setText('AgriMRI_Metadata.json detected in folder. Do you want to overwrite the file?')
                    msg_box_agriMRI_header.setIcon(QMessageBox.Warning)
                    msg_box_agriMRI_header.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    reply_msg_box_agriMRI_header = msg_box_agriMRI_header.exec()
                    if reply_msg_box_agriMRI_header == QMessageBox.Ok:
                        params.save_AgriMRI_Metadata_file_json()
                        print('\033[1m' + 'AgriMRI_Metadata.json overwritten.' + '\033[0m')
                    else: print('\033[1m' + 'AgriMRI_Metadata.json not overwritten.' + '\033[0m')
            else:
                print('\033[1m' + 'No experiment ID set!! Save data to rawdata folder.' + '\033[0m')
            
            params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_rawdata'
            if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
            params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/'
            params.datapath = params.agriMRI_folder_structure + params.datapath
            
        if params.GUImode == 5:
            self.datapath_2_temp = ''
            self.datapath_2_temp = params.datapath
            params.datapath + '/Image_Stitching'

            if params.headerfileformat == 0:
                if os.path.isfile(params.datapath + '_Header.txt') == True:
                    msg_box_data = QMessageBox()
                    msg_box_data.setText('Stitching data with same name detected in folder. Do you want to overwrite the data?')
                    msg_box_data.setIcon(QMessageBox.Warning)
                    msg_box_data.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    reply_msg_box_data = msg_box_data.exec()
                    if reply_msg_box_data == QMessageBox.Ok: print('\033[1m' + 'Overwriting data.' + '\033[0m')
                    else:
                        print('\033[1m' + 'Acquisition canceled.' + '\033[0m')
                        if params.agriMRI_mode == 1:
                            params.datapath = self.datapath_temp
                            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                        self.Acquire_pushButton.setEnabled(True)
                        self.Data_Process_pushButton.setEnabled(True)
                        self.repaint()
                        return
                else: print('\033[1m' + 'Starting new acquisition.' + '\033[0m')
            else:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    msg_box_data = QMessageBox()
                    msg_box_data.setText('Stitching data with same name detected in folder. Do you want to overwrite the data?')
                    msg_box_data.setIcon(QMessageBox.Warning)
                    msg_box_data.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    reply_msg_box_data = msg_box_data.exec()
                    if reply_msg_box_data == QMessageBox.Ok: print('\033[1m' + 'Overwriting data.' + '\033[0m')
                    else:
                        print('\033[1m' + 'Acquisition canceled.' + '\033[0m')
                        if params.agriMRI_mode == 1:
                            params.datapath = self.datapath_temp
                            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                        self.Acquire_pushButton.setEnabled(True)
                        self.Data_Process_pushButton.setEnabled(True)
                        self.repaint()
                        return
                else: print('\033[1m' + 'Starting new acquisition.' + '\033[0m')

            params.datapath = self.datapath_2_temp

        else:
            if params.headerfileformat == 0:
                if os.path.isfile(params.datapath + '_Header.txt') == True:
                    msg_box_data = QMessageBox()
                    msg_box_data.setText('Data with same name detected in folder. Do you want to overwrite the data?')
                    msg_box_data.setIcon(QMessageBox.Warning)
                    msg_box_data.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    reply_msg_box_data = msg_box_data.exec()
                    if reply_msg_box_data == QMessageBox.Ok: print('\033[1m' + 'Overwriting data.' + '\033[0m')
                    else:
                        print('\033[1m' + 'Acquisition canceled.' + '\033[0m')
                        if params.agriMRI_mode == 1:
                            params.datapath = self.datapath_temp
                            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                        self.Acquire_pushButton.setEnabled(True)
                        self.Data_Process_pushButton.setEnabled(True)
                        self.repaint()
                        return
                else: print('\033[1m' + 'Starting new acquisition.' + '\033[0m')
            else:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    msg_box_data = QMessageBox()
                    msg_box_data.setText('Data with same name detected in folder. Do you want to overwrite the data?')
                    msg_box_data.setIcon(QMessageBox.Warning)
                    msg_box_data.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    reply_msg_box_data = msg_box_data.exec()
                    if reply_msg_box_data == QMessageBox.Ok: print('\033[1m' + 'Overwriting data.' + '\033[0m')
                    else:
                        print('\033[1m' + 'Acquisition canceled.' + '\033[0m')
                        if params.agriMRI_mode == 1:
                            params.datapath = self.datapath_temp
                            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                        self.Acquire_pushButton.setEnabled(True)
                        self.Data_Process_pushButton.setEnabled(True)
                        self.repaint()
                        return
                else: print('\033[1m' + 'Starting new acquisition.' + '\033[0m')
                        
        if params.GUImode == 2:
            if params.sequence == 0:
                proc.T1measurement_IR_FID()
            elif params.sequence == 1:
                proc.T1measurement_IR_SE()
            elif params.sequence == 2:
                proc.T1measurement_IR_FID_Gs()
            elif params.sequence == 3:
                proc.T1measurement_IR_SE_Gs()
            elif params.sequence == 4:
                proc.T1measurement_Image_IR_GRE()
            elif params.sequence == 5:
                proc.T1measurement_Image_IR_SE()
            elif params.sequence == 6:
                proc.T1measurement_Image_IR_GRE_Gs()
            elif params.sequence == 7:
                proc.T1measurement_Image_IR_SE_Gs()
        elif params.GUImode == 3:
            if params.sequence == 0:
                proc.T2measurement_SE()
            elif params.sequence == 1:
                proc.T2measurement_SIR_FID()
            elif params.sequence == 2:
                proc.T2measurement_SE_Gs()
            elif params.sequence == 3:
                proc.T2measurement_SIR_FID_Gs()
            elif params.sequence == 4:
                proc.T2measurement_Image_SE()
            elif params.sequence == 5:
                proc.T2measurement_Image_SIR_GRE()
            elif params.sequence == 6:
                proc.T2measurement_Image_SE_Gs()
            elif params.sequence == 7:
                proc.T2measurement_Image_SIR_GRE_Gs()
        elif params.GUImode == 5:
            if params.motor_enable == 1:
                if params.motor_available:
                    self.motor_reader.blockSignals(True)
                    if params.sequence == 0:
                        proc.image_stitching_2D_GRE(motor=self.motor)
                    if params.sequence == 1:
                        proc.image_stitching_2D_GRE(motor=self.motor)
                    if params.sequence == 2:
                        proc.image_stitching_2D_SE(motor=self.motor)
                    if params.sequence == 3:
                        proc.image_stitching_2D_SE(motor=self.motor)
                    if params.sequence == 4:
                        proc.image_stitching_2D_SE(motor=self.motor)
                    if params.sequence == 5:
                        proc.image_stitching_2D_GRE_slice(motor=self.motor)
                    if params.sequence == 6:
                        proc.image_stitching_2D_GRE_slice(motor=self.motor)
                    if params.sequence == 7:
                        proc.image_stitching_2D_SE_slice(motor=self.motor)
                    if params.sequence == 8:
                        proc.image_stitching_2D_SE_slice(motor=self.motor)
                    if params.sequence == 9:
                        proc.image_stitching_2D_SE_slice(motor=self.motor)
                    if params.sequence == 10:
                        proc.image_stitching_3D_slab(motor=self.motor)
                    if params.sequence == 11:
                        proc.image_stitching_3D_TSE_slab(motor=self.motor)
                    self.motor_reader.blockSignals(False)
                else:
                    print('Motor Control: Motor not available, maybe it is still homing?')
            else:
                if params.sequence == 0:
                    proc.image_stitching_2D_GRE()
                if params.sequence == 1:
                    proc.image_stitching_2D_GRE()
                if params.sequence == 2:
                    proc.image_stitching_2D_SE()
                if params.sequence == 3:
                    proc.image_stitching_2D_SE()
                if params.sequence == 4:
                    proc.image_stitching_2D_SE()
                if params.sequence == 5:
                    proc.image_stitching_2D_GRE_slice()
                if params.sequence == 6:
                    proc.image_stitching_2D_GRE_slice()
                if params.sequence == 7:
                    proc.image_stitching_2D_SE_slice()
                if params.sequence == 8:
                    proc.image_stitching_2D_SE_slice()
                if params.sequence == 9:
                    proc.image_stitching_2D_SE_slice()
                if params.sequence == 10:
                    proc.image_stitching_3D_slab()
                if params.sequence == 11:
                    proc.image_stitching_3D_TSE_slab()

        elif params.GUImode == 1:
            if params.autorecenter == 1:
                self.frequencyoffsettemp = 0
                self.frequencyoffsettemp = params.frequencyoffset
                params.frequencyoffset = 0
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
                    seq.sequence_upload()
                elif params.sequence == 17 or params.sequence == 19 or params.sequence == 21 \
                        or params.sequence == 24 or params.sequence == 26 or params.sequence == 29 \
                        or params.sequence == 32 or params.sequence == 34:
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
                    seq.sequence_upload()
                elif params.sequence == 18 or params.sequence == 20 or params.sequence == 22 \
                        or params.sequence == 23 or params.sequence == 25 or params.sequence == 27 \
                        or params.sequence == 28 or params.sequence == 30 or params.sequence == 31 \
                        or params.sequence == 33 or params.sequence == 35 or params.sequence == 36:
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
                    seq.sequence_upload()
            else:
                seq.sequence_upload()
        else:
            seq.sequence_upload()

        params.saveFileParameter()
        params.saveFileData()

        if params.GUImode == 5:
            self.datapath_2_temp = ''
            self.datapath_2_temp = params.datapath
            params.datapath + '/Image_Stitching'

            if params.headerfileformat == 0:
                params.save_header_file_txt()
            else:
                params.save_header_file_json()

            params.datapath = self.datapath_2_temp

        else:
            if params.headerfileformat == 0:
                params.save_header_file_txt()
            else:
                params.save_header_file_json()

        if self.dialog_params != None:
            self.SIR_TEtemp = 0
            self.SIR_TEtemp = params.SIR_TE
            self.dialog_params.load_params()
            params.SIR_TE = self.SIR_TEtemp
            self.dialog_params.load_params()
            self.dialog_params.repaint()

        if self.dialog_config != None:
            self.dialog_config.load_params()
            self.dialog_config.repaint()

        if self.dialog_motortools != None:
            self.dialog_motortools.load_params()
            self.dialog_motortools.repaint()

        if params.agriMRI_mode == 1:
            params.datapath = self.datapath_temp
            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp

        if params.autodataprocess == 1: self.dataprocess()

        self.Acquire_pushButton.setEnabled(True)
        self.Data_Process_pushButton.setEnabled(True)
        self.repaint()

    def load_params(self):
        self.Sequence_comboBox.clear()
        self.switch_GUImode(params.GUImode)

    def parameter_window(self):
        if self.dialog_params == None:
            self.dialog_params = ParametersWindow(self)
            self.dialog_params.show()
        else:
            self.dialog_params.hide()
            self.dialog_params.show()

    def config_window(self):
        if self.dialog_config == None:
            self.dialog_config = ConfigWindow(self)
            self.dialog_config.show()
        else:
            self.dialog_config.hide()
            self.dialog_config.show()

    def motor_tools(self):
        if self.dialog_motortools == None:
            self.dialog_motortools = MotorToolsWindow(self, motor=self.motor)
            self.dialog_motortools.show()
        else:
            self.dialog_motortools.hide()
            self.dialog_motortools.show()
            
    def agri_window(self):
        if self.dialog_agri == None:
            self.dialog_agri = AgriMRIMetadataWindow(self)
            self.dialog_agri.show()
        else:
            self.dialog_agri.hide()
            self.dialog_agri.show()

    def set_Datapath(self):
        params.datapath = self.Datapath_lineEdit.text()
        params.saveFileParameter()

    def dataprocess(self):
        self.Data_Process_pushButton.setEnabled(False)
        self.repaint()
        
        if params.agriMRI_mode == 1:
            self.datapath_temp = ''
            self.datapath_temp = params.datapath
            self.agriMRI_folder_structure_temp = ''
            self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
            params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_rawdata/'
            params.datapath = params.agriMRI_folder_structure + params.datapath
            
        self.dataprocess_header_flag = 0
        
        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.imageorientation_temp = ''
        self.imageorientation_temp = params.imageorientation
        self.FOV_temp = 0
        self.FOV_temp = params.FOV
        self.SPEsteps_temp = 0
        self.SPEsteps_temp = params.SPEsteps
        self.nPE_temp = 0
        self.nPE_temp = params.nPE
        self.motor_image_count_temp = 0
        self.motor_image_count_temp = params.motor_image_count
        self.motor_movement_step_temp = 0
        self.motor_movement_step_temp = params.motor_movement_step
        self.slicethickness_temp = 0
        self.slicethickness_temp = params.slicethickness
        self.motor_total_image_length_temp = 0
        self.motor_total_image_length_temp = params.motor_total_image_length
        self.motor_start_position_temp = 0
        self.motor_start_position_temp = params.motor_start_position
        self.motor_end_position_temp = 0
        self.motor_end_position_temp = params.motor_end_position
        self.radialanglestep_temp = 0
        self.radialanglestep_temp = params.radialanglestep
        self.radialosfactor_temp = 0
        self.radialosfactor_temp = params.radialosfactor
        self.autofreqoffset_temp = 0
        self.autofreqoffset_temp = params.autofreqoffset
        self.sliceoffset_temp = 0
        self.sliceoffset_temp = params.sliceoffset
        
        if params.headerfileformat == 0:
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_Header.txt') == True:
                    f = open(params.datapath + '/Image_Stitching_Header.txt', 'r+')
                    headerlines = f.readlines()
                    f.close()
                    self.dataprocess_header_flag = 1
                else: print('No .txt header file!!')
            elif os.path.isdir(params.datapath) == False:
                if os.path.isfile(params.datapath + '_Header.txt') == True:
                    f = open(params.datapath + '_Header.txt', 'r+')
                    headerlines = f.readlines()
                    f.close()
                    self.dataprocess_header_flag = 1
                else: print('No .txt header file!!')
            else: print('No directory or .txt header file!!')
            
            if self.dataprocess_header_flag == 1:
                self.headerline_string_split = headerlines[2].split(': ')
                params.GUImode = int(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[3].split(': ')
                params.sequence = int(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[30].split(': ')
                params.imageorientation = self.headerline_string_split[1]
                self.headerline_string_split = params.imageorientation.split('\n')
                params.imageorientation = self.headerline_string_split[0]
                self.headerline_string_split = headerlines[70].split(': ')
                params.FOV = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[54].split(': ')
                params.SPEsteps = int(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[32].split(': ')
                params.nPE = int(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[91].split(': ')
                params.motor_image_count = int(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[90].split(': ')
                params.motor_movement_step = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[71].split(': ')
                params.slicethickness = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[89].split(': ')
                params.motor_total_image_length = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[87].split(': ')
                params.motor_start_position = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[88].split(': ')
                params.motor_end_position = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[66].split(': ')
                params.radialanglestep = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[67].split(': ')
                params.radialosfactor = float(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[73].split(': ')
                params.autofreqoffset = int(self.headerline_string_split[1])
                self.headerline_string_split = headerlines[74].split(': ')
                params.sliceoffset = float(self.headerline_string_split[1])
                     
        else:
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_Header.json') == True:
                    with open(params.datapath + '/Image_Stitching_Header.json', 'r', encoding='utf-8') as j:
                        jsonparams = json.loads(j.read())
                    self.dataprocess_header_flag = 1
                else: print('No .json header file!!')
            elif os.path.isdir(params.datapath) == False:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    with open(params.datapath + '_Header.json', 'r', encoding='utf-8') as j:
                        jsonparams = json.loads(j.read())
                    self.dataprocess_header_flag = 1
                else: print('No .json header file!!')
            else: print('No directory or .json header file!!')
            
            if self.dataprocess_header_flag == 1:
                params.GUImode = int(jsonparams['GUI mode'])
                params.sequence = int(jsonparams['Sequence'])
                params.imageorientation = jsonparams['Image orientation']
                params.FOV = jsonparams['FOV [mm]']
                params.SPEsteps = int(jsonparams['3D phase steps'])
                params.nPE = int(jsonparams['Image resolution [pixel]'])
                params.motor_image_count = int(jsonparams['Motor image count'])
                params.motor_movement_step = np.abs(jsonparams['Motor movement step [mm]'])
                params.slicethickness = jsonparams['Slice/Slab thickness [mm]']
                params.motor_total_image_length = jsonparams['Motor total image length [mm]']
                params.motor_start_position = jsonparams['Motor start position [mm]']
                params.motor_end_position = jsonparams['Motor end position [mm]']
                params.radialanglestep = jsonparams['Radial angle [°]']
                params.radialosfactor = jsonparams['Radial oversampling factor']
                params.autofreqoffset = jsonparams['Auto frequency offset']
                params.sliceoffset = jsonparams['Slice offset [mm]']
        
        if self.dataprocess_header_flag == 1:
            if self.dialog_plot != None:
                if self.dialog_plot.dialog_3D_layers != None:
                    self.dialog_plot.dialog_3D_layers.hide()
            
        if params.single_plot == 1:
            if self.dialog_plot != None:
                for attr_name in dir(self.dialog_plot):
                    if 'canvas' in attr_name.lower():
                        canvas = getattr(self.dialog_plot, attr_name)
                        if canvas != None:
                            plt.close(canvas.figure)
                            canvas.setParent(None)
                            canvas.deleteLater()
                            setattr(self.dialog_plot, attr_name, None)
                self.dialog_plot.setAttribute(QtCore.Qt.WA_DeleteOnClose)
                self.dialog_plot.close()
                self.dialog_plot = None
            
        if params.GUImode == 0:
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.spectrum_process()
                proc.spectrum_analytics()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()

            else: print('No spectrum rawdata file!!')
                
        elif params.GUImode == 1 and (params.sequence == 34 or params.sequence == 35 or params.sequence == 36):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.image_3D_process()
                proc.image_3D_analytics()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No 3D rawdata file!!')
            
        elif params.GUImode == 1 and (params.sequence == 14 or params.sequence == 31):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.image_diff_process()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No 2D diffusion rawdata file!!')
        elif params.GUImode == 1 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 \
                                      or params.sequence == 3 or params.sequence == 17 or params.sequence == 18 \
                                      or params.sequence == 19 or params.sequence == 20):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.radial_process()
                proc.image_analytics()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No 2D radial rawdata file!!')
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
            else: print('No 2D rawdata file!!')

        elif params.GUImode == 2 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.T1process()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No T1 file!!')
        elif params.GUImode == 2 and (params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7):
            if os.path.isfile(params.datapath + '_Image_TI_steps.txt') == True:
                if os.path.isfile(params.datapath + '_Image_Magnitude.txt') == True:
                    proc.T1imageprocess()
                    
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
                else: print('No T1 rawdata file!!')
            else: print('No TI steps file!!')

        elif params.GUImode == 3 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.T2process()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No T2 file!!')
        elif params.GUImode == 3 and (params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7):
            if os.path.isfile(params.datapath + '_Image_TE_steps.txt') == True:
                if os.path.isfile(params.datapath + '_Image_Magnitude.txt') == True:
                    proc.T2imageprocess()
                    
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
                else: print('No T2 rawdata file!!')
            else: print('No TE steps file!!')

        elif params.GUImode == 4 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 4 or params.sequence == 5):
            self.datapathtemp = params.datapath
            params.projx = np.matrix(np.zeros((1, 4)))
            params.projy = np.matrix(np.zeros((1, 4)))
            params.projz = np.matrix(np.zeros((1, 4)))
            for m in range(params.projaxis.shape[0]):
                params.datapath = self.datapathtemp + '_' + str(m)
                if os.path.isfile(params.datapath + '.txt') == True:
                    proc.spectrum_process()
                    if m == 0:
                        params.projx = np.matrix(np.zeros((params.timeaxis.shape[0], 4)))
                        params.projx[:, 0] = np.reshape(params.mag, (params.timeaxis.shape[0], 1))
                        params.projx[:, 1] = np.reshape(params.real, (params.timeaxis.shape[0], 1))
                        params.projx[:, 2] = np.reshape(params.imag, (params.timeaxis.shape[0], 1))
                        params.projx[:, 3] = params.spectrumfft
                    elif m == 1:
                        params.projy = np.matrix(np.zeros((params.timeaxis.shape[0], 4)))
                        params.projy[:, 0] = np.reshape(params.mag, (params.timeaxis.shape[0], 1))
                        params.projy[:, 1] = np.reshape(params.real, (params.timeaxis.shape[0], 1))
                        params.projy[:, 2] = np.reshape(params.imag, (params.timeaxis.shape[0], 1))
                        params.projy[:, 3] = params.spectrumfft
                    elif m == 2:
                        params.projz = np.matrix(np.zeros((params.timeaxis.shape[0], 4)))
                        params.projz[:, 0] = np.reshape(params.mag, (params.timeaxis.shape[0], 1))
                        params.projz[:, 1] = np.reshape(params.real, (params.timeaxis.shape[0], 1))
                        params.projz[:, 2] = np.reshape(params.imag, (params.timeaxis.shape[0], 1))
                        params.projz[:, 3] = params.spectrumfft
                else: print('No projection spectrum rawdata file!!')
            params.datapath = self.datapathtemp
            
            self.dialog_plot = PlotWindow(self)
            self.dialog_plot.show()
        elif params.GUImode == 4 and (params.sequence == 2 or params.sequence == 3 or params.sequence == 6 or params.sequence == 7):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.spectrum_process()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No projection spectrum rawdata file!!')

        elif params.GUImode == 5 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3 \
                                      or params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                                      or params.sequence == 8 or params.sequence == 9):
            if os.path.isfile(params.datapath + '/Image_Stitching_1.txt') == True:
                proc.image_stitching_2D_process()
                proc.image_stitching_analytics()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No 2D stitching rawdata file!!')
        elif params.GUImode == 5 and (params.sequence == 10  or params.sequence == 11):
            if os.path.isfile(params.datapath + '/Image_Stitching_1.txt') == True:
                proc.image_stitching_3D_process()
                proc.image_stitching_3D_analytics()
                
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
            else: print('No 3D stitching rawdata file!!')
    
        params.saveFileData()
        
        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.imageorientation = self.imageorientation_temp
        params.FOV = self.FOV_temp
        params.SPEsteps = self.SPEsteps_temp
        params.nPE = self.nPE_temp
        params.motor_image_count = self.motor_image_count_temp
        params.motor_movement_step = self.motor_movement_step_temp
        params.slicethickness = self.slicethickness_temp
        params.motor_total_image_length = self.motor_total_image_length_temp
        params.motor_start_position = self.motor_start_position_temp
        params.motor_end_position = self.motor_end_position_temp
        params.radialanglestep = self.radialanglestep_temp
        params.radialosfactor = self.radialosfactor_temp
        params.autofreqoffset = self.autofreqoffset_temp
        params.sliceoffset = self.sliceoffset_temp
            
        if params.agriMRI_mode == 1:
            params.datapath = self.datapath_temp
            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
        
        self.Data_Process_pushButton.setEnabled(True)
        self.repaint()

    def tools(self):
        if self.dialog_tools == None:
            self.dialog_tools = ToolsWindow(self)
            self.dialog_tools.show()
        else:
            self.dialog_tools.hide()
            self.dialog_tools.show()

    def protocol(self):
        if self.dialog_prot == None:
            self.dialog_prot = ProtocolWindow(self, motor = self.motor, motor_reader=self.motor_reader)
            self.dialog_prot.show()
        else:
            self.dialog_prot.hide()
            self.dialog_prot.show()

    def sarmonitor(self):
        if self.dialog_sarmonitor == None:
            self.dialog_sarmonitor = SARMonitorWindow(self)
            self.dialog_sarmonitor.trigger_no_sar.connect(self.set_sar_none)
            
            self.dialog_sarmonitor.show()
        else:
            self.dialog_sarmonitor.hide()
            self.dialog_sarmonitor.show()

    def set_sar_none(self):
        self.dialog_sarmonitor = None
    
    def update_gui(self):
        QApplication.processEvents()

    def closeEvent(self, event):
        choice = QMessageBox.question(self, 'Close Relax 2.0', 'Are you sure that you want to quit Relax 2.0?', QMessageBox.Cancel | QMessageBox.Close, QMessageBox.Cancel)

        if choice == QMessageBox.Close:
            params.GUImode = 0
            params.sequence = 0
            params.saveFileParameter()
            params.saveFileData()
            event.accept()
            raise SystemExit
        else:
            event.ignore()


class ParametersWindow(Para_Window_Form, Para_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ParametersWindow, self).__init__(parent)
        self.setupUi(self)

        if params.autograd == 1: self.recalculate_gradients()   
        self.load_params()

        self.ui = loadUi('ui/parameters.ui')
        self.setWindowTitle('Parameters')
        self.setGeometry(420, 40, 1160, 900)

        self.Samplingtime_spinBox.setKeyboardTracking(False)
        self.Samplingtime_spinBox.valueChanged.connect(self.update_params)
        self.label_6.setToolTip('The duration of the sampling window where the MRI signal is measured.')
        self.TE_doubleSpinBox.setKeyboardTracking(False)
        self.TE_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_4.setToolTip('The time between the center of the RF flip pulse and the center of the sampling window (also in FID and GRE sequences).')
        self.TI_doubleSpinBox.setKeyboardTracking(False)
        self.TI_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_13.setToolTip('The time between the center of the RF 180° inversion pulse and the center of the RF flip pulse.')
        self.TR_spinBox.setKeyboardTracking(False)
        self.TR_spinBox.valueChanged.connect(self.update_params)
        self.label_5.setToolTip('The time between repetitions for aquirering k-space lines in images or averages in spectra.')
        self.SIR_TE_doubleSpinBox.setKeyboardTracking(False)
        self.SIR_TE_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.Image_Resolution_comboBox.clear()
        self.Image_Resolution_comboBox.addItems(['8', '16', '32', '64', '128', '256', '512'])
        self.Image_Resolution_comboBox.setCurrentIndex(params.imageresolution)
        self.Image_Resolution_comboBox.currentIndexChanged.connect(self.update_params)

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
        
        self.TI_Stepping_Linear_radioButton.toggled.connect(self.update_TI_stepping_linear)
        self.TI_Stepping_Log_radioButton.toggled.connect(self.update_TI_stepping_log)
        self.TE_Stepping_Linear_radioButton.toggled.connect(self.update_TE_stepping_linear)
        self.TE_Stepping_Log_radioButton.toggled.connect(self.update_TE_stepping_log)

        self.Projection_X_radioButton.toggled.connect(self.update_params)
        self.Projection_Y_radioButton.toggled.connect(self.update_params)
        self.Projection_Z_radioButton.toggled.connect(self.update_params)

        self.Projection_Angle_spinBox.setKeyboardTracking(False)
        self.Projection_Angle_spinBox.valueChanged.connect(self.update_params)

        self.Average_spinBox.setKeyboardTracking(False)
        self.Average_spinBox.valueChanged.connect(self.update_params)
        self.Average_radioButton.toggled.connect(self.update_params)
        self.Average_radioButton.setToolTip('Averaging of MRI spectra.')

        self.Auto_Gradients_radioButton.toggled.connect(self.auto_gradients)
        
        self.Recalculate_Gradients_pushButton.clicked.connect(lambda: self.recalculate_gradients())

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
        self.label_39.setToolTip('Amplitude of a 3D slice phase gradient step.\nThe total amplitude add up to (3D slab steps / 2) * 3D slice phase gradient step.')
        self.SPEsteps_spinBox.setKeyboardTracking(False)
        self.SPEsteps_spinBox.valueChanged.connect(self.update_params)
        self.label_40.setToolTip('Number of 3D FFT slices.')

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
        # self.Image_Orientation_comboBox.addItems(['XY', 'YZ', 'ZX'])
        self.Image_Orientation_comboBox.addItems(['XY', 'YZ', 'ZX', 'YX', 'ZY', 'XZ'])
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

        self.Radial_Angle_Step_spinBox.setKeyboardTracking(False)
        self.Radial_Angle_Step_spinBox.valueChanged.connect(self.update_params)
        self.Radial_Oversampling_Factor_spinBox.setKeyboardTracking(False)
        self.Radial_Oversampling_Factor_spinBox.valueChanged.connect(self.update_params)

        self.FOV_doubleSpinBox.setKeyboardTracking(False)
        self.FOV_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Slice_Thickness_doubleSpinBox.setKeyboardTracking(False)
        self.Slice_Thickness_doubleSpinBox.valueChanged.connect(self.update_params)

        self.Motor_Start_Position_doubleSpinBox.setKeyboardTracking(False)
        self.Motor_Start_Position_doubleSpinBox.valueChanged.connect(self.update_motor_start_position)
        self.Motor_End_Position_doubleSpinBox.setKeyboardTracking(False)
        self.Motor_End_Position_doubleSpinBox.valueChanged.connect(self.update_motor_end_Position)
        self.Motor_Total_Image_Length_doubleSpinBox.setKeyboardTracking(False)
        self.Motor_Total_Image_Length_doubleSpinBox.valueChanged.connect(self.update_motor_total_image_length)
        self.Motor_Movement_Step_doubleSpinBox.setKeyboardTracking(False)
        self.Motor_Movement_Step_doubleSpinBox.valueChanged.connect(self.update_motor_movement_step)
        self.Motor_Image_Count_spinBox.setKeyboardTracking(False)
        self.Motor_Image_Count_spinBox.valueChanged.connect(self.update_motor_image_count)
        self.Motor_Start_Here_pushButton.clicked.connect(lambda: self.motor_start_here())
        self.Motor_End_Here_pushButton.clicked.connect(lambda: self.motor_end_here())
        self.Motor_Settling_Time_doubleSpinBox.setKeyboardTracking(False)
        self.Motor_Settling_Time_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Motor_AC_Position_doubleSpinBox.setKeyboardTracking(False)
        self.Motor_AC_Position_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Motor_AC_Here_pushButton.clicked.connect(lambda: self.motor_AC_here())
        self.Motor_AC_Position_Center_radioButton.toggled.connect(self.update_params)
        self.Motor_AC_Inbetween_radioButton.toggled.connect(self.update_params)
        self.Motor_AC_Inbetween_Step_spinBox.valueChanged.connect(self.update_params)

        self.Motor_Start_Position_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        self.Motor_Start_Position_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.Motor_End_Position_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        self.Motor_End_Position_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        
    def update_motor_start_position(self):
        params.motor_start_position = self.Motor_Start_Position_doubleSpinBox.value()

        self.Motor_Total_Image_Length_doubleSpinBox.setMaximum(params.motor_axis_limit_positive - params.motor_start_position)
        self.Motor_Total_Image_Length_doubleSpinBox.setMinimum(params.motor_axis_limit_negative - params.motor_start_position)

        params.motor_total_image_length = round(params.motor_end_position - params.motor_start_position, 1)
        params.motor_image_count = int(round(params.motor_total_image_length / params.motor_movement_step) + 1)
        params.motor_total_image_length = (params.motor_image_count - 1) * params.motor_movement_step
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        
        if params.motor_end_position > params.motor_axis_limit_positive:
            params.motor_end_position = params.motor_axis_limit_positive
            params.motor_start_position = params.motor_end_position - params.motor_total_image_length
        
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        self.Motor_Image_Count_spinBox.setValue(params.motor_image_count)
        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
        
        if params.motor_AC_position_center == 1:
            params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
            self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

        params.saveFileParameter()

    def update_motor_end_Position(self):
        params.motor_end_position = self.Motor_End_Position_doubleSpinBox.value()

        params.motor_total_image_length = round(params.motor_end_position - params.motor_start_position, 1)
        params.motor_image_count = int(round(params.motor_total_image_length / params.motor_movement_step) + 1)
        params.motor_total_image_length = (params.motor_image_count - 1) * params.motor_movement_step
        params.motor_start_position = params.motor_end_position - params.motor_total_image_length
        
        if params.motor_start_position < params.motor_axis_limit_negative:
            params.motor_start_position = params.motor_axis_limit_negative
            params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        self.Motor_Image_Count_spinBox.setValue(params.motor_image_count)
        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)

        if params.motor_AC_position_center == 1:
            params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
            self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

        params.saveFileParameter()

    def update_motor_total_image_length(self):
        params.motor_total_image_length = self.Motor_Total_Image_Length_doubleSpinBox.value()
        
        params.motor_image_count = int(round(params.motor_total_image_length / params.motor_movement_step) + 1)
        params.motor_total_image_length = (params.motor_image_count - 1) * params.motor_movement_step
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        
        if params.motor_end_position > params.motor_axis_limit_positive:
            params.motor_end_position = params.motor_axis_limit_positive
            params.motor_start_position = params.motor_end_position - params.motor_total_image_length
        
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        self.Motor_Image_Count_spinBox.setValue(params.motor_image_count)
        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
        
        if params.motor_AC_position_center == 1:
            params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
            self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

        params.saveFileParameter()

    def update_motor_movement_step(self):
        params.motor_movement_step = self.Motor_Movement_Step_doubleSpinBox.value()
        
        params.motor_image_count = int(round(params.motor_total_image_length / params.motor_movement_step) + 1)
        params.motor_total_image_length = (params.motor_image_count - 1) * params.motor_movement_step
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        
        if params.motor_end_position > params.motor_axis_limit_positive:
            params.motor_end_position = params.motor_axis_limit_positive
            params.motor_start_position = params.motor_end_position - params.motor_total_image_length
        
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        self.Motor_Image_Count_spinBox.setValue(params.motor_image_count)
        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)

        params.saveFileParameter()

    def update_motor_image_count(self):
        params.motor_image_count = self.Motor_Image_Count_spinBox.value()
        
        params.motor_total_image_length = (params.motor_image_count - 1) * params.motor_movement_step
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        
        if params.motor_total_image_length > params.motor_axis_limit_positive - params.motor_start_position:
            params.motor_total_image_length = params.motor_axis_limit_positive - params.motor_start_position
            params.motor_image_count = int(np.floor(params.motor_total_image_length / params.motor_movement_step) + 1)
            params.motor_total_image_length = (params.motor_image_count - 1) * params.motor_movement_step
            params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        self.Motor_Image_Count_spinBox.setValue(params.motor_image_count)
        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
        
        params.saveFileParameter()

    def motor_start_here(self):
        if params.motor_actual_position != params.motor_end_position:
            params.motor_start_position = params.motor_actual_position
            self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
            if params.motor_AC_position_center == 1:
                params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
                self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

            params.saveFileParameter()

    def motor_end_here(self):
        if params.motor_actual_position != params.motor_start_position:
            params.motor_end_position = params.motor_actual_position
            self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
            if params.motor_AC_position_center == 1:
                params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
                self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

            params.saveFileParameter()
            
    def motor_AC_here(self):
        params.motor_AC_position_center = 0
        self.Motor_AC_Position_Center_radioButton.setChecked(False)
        params.motor_AC_position = params.motor_actual_position
        self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

        params.saveFileParameter()

    def load_params(self):
        self.TE_doubleSpinBox.setValue(params.TE)
        self.TI_doubleSpinBox.setValue(params.TI)
        self.TR_spinBox.setValue(params.TR)
        self.SIR_TE_doubleSpinBox.setValue(params.SIR_TE)
        
        self.Image_Resolution_comboBox.setCurrentIndex(params.imageresolution)

        self.Samplingtime_spinBox.setValue(params.TS)
        self.TI_Start_doubleSpinBox.setValue(params.TIstart)
        self.TI_Stop_doubleSpinBox.setValue(params.TIstop)
        self.TI_Steps_spinBox.setValue(params.TIsteps)
        self.TE_Start_doubleSpinBox.setValue(params.TEstart)
        self.TE_Stop_doubleSpinBox.setValue(params.TEstop)
        self.TE_Steps_spinBox.setValue(params.TEsteps)
        
        if params.TIstepping == 1:
            self.TI_Stepping_Log_radioButton.setChecked(True)
            self.TI_Stepping_Linear_radioButton.setChecked(False)
        else:
            self.TI_Stepping_Log_radioButton.setChecked(False)
            self.TI_Stepping_Linear_radioButton.setChecked(True)
            
        if params.TEstepping == 1:
            self.TE_Stepping_Log_radioButton.setChecked(True)
            self.TE_Stepping_Linear_radioButton.setChecked(False)
        else:
            self.TE_Stepping_Log_radioButton.setChecked(False)
            self.TE_Stepping_Linear_radioButton.setChecked(True)

        if params.projaxis[0] == 1: self.Projection_X_radioButton.setChecked(True)
        if params.projaxis[1] == 1: self.Projection_Y_radioButton.setChecked(True)
        if params.projaxis[2] == 1: self.Projection_Z_radioButton.setChecked(True)

        self.Projection_Angle_spinBox.setValue(params.projectionangle)
        
        if params.average == 1: self.Average_radioButton.setChecked(True)
        self.Average_spinBox.setValue(params.averagecount)

        self.GROamplitude_spinBox.setValue(params.GROamplitude)
        if round(params.GROamplitude) < 300: self.GROamplitude_spinBox.setStyleSheet('color: yellow')
        elif round(2*params.GROamplitude) > 8500: self.GROamplitude_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.GROamplitude_spinBox.setStyleSheet('color: #31363B')
            else: self.GROamplitude_spinBox.setStyleSheet('color: #eff0f1')
        
        self.GPEstep_spinBox.setValue(params.GPEstep)
        if round(params.GPEstep * params.nPE/2) > 8500: self.GPEstep_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.GPEstep_spinBox.setStyleSheet('color: #31363B')
            else: self.GPEstep_spinBox.setStyleSheet('color: #eff0f1')
        
        self.GSamplitude_spinBox.setValue(params.GSamplitude)
        if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B')
            else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1')

        self.Flipangle_Time_spinBox.setValue(params.flipangletime)
        self.Flipangle_Amplitude_spinBox.setValue(params.flipangleamplitude)

        self.GSPEstep_spinBox.setValue(params.GSPEstep)
        self.SPEsteps_spinBox.setValue(params.SPEsteps)
        if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B')
            else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1')

        self.GDiffamplitude_spinBox.setValue(params.Gdiffamplitude)
        if round(params.Gdiffamplitude) > 8500: self.GDiffamplitude_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.GDiffamplitude_spinBox.setStyleSheet('color: #31363B')
            else: self.GDiffamplitude_spinBox.setStyleSheet('color: #eff0f1')

        self.Crusher_Amplitude_spinBox.setValue(params.crusheramplitude)
        if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B')
            else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1')
        
        self.Spoiler_Amplitude_spinBox.setValue(params.spoileramplitude)
        if round(params.spoileramplitude) > 8500: self.GSpoiler_Amplitude_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #31363B')
            else: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #eff0f1')

        self.Image_Orientation_comboBox.setCurrentIndex(params.imageorientation)

        if params.frequencyoffsetsign == 0:
            self.Frequency_Offset_spinBox.setValue(params.frequencyoffset)
        elif params.frequencyoffsetsign == 1:
            self.Frequency_Offset_spinBox.setValue(-1 * params.frequencyoffset)

        self.Phase_Offset_spinBox.setValue(params.phaseoffset)
        self.Radial_Angle_Step_spinBox.setValue(params.radialanglestep)
        self.Radial_Oversampling_Factor_spinBox.setValue(params.radialosfactor)
        self.FOV_doubleSpinBox.setValue(params.FOV)
        self.Slice_Thickness_doubleSpinBox.setValue(params.slicethickness)

        if params.autograd == 1: self.Auto_Gradients_radioButton.setChecked(True)

        self.Slice_Offset_doubleSpinBox.setValue(params.sliceoffset)

        if params.autofreqoffset == 1: self.Auto_Frequency_Offset_radioButton.setChecked(True)

        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)
        self.Motor_Image_Count_spinBox.setValue(params.motor_image_count)
        self.Motor_Settling_Time_doubleSpinBox.setValue(params.motor_settling_time)
        if params.motor_AC_position_center == 1: params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
        self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)
        if params.motor_AC_position_center == 1: self.Motor_AC_Position_Center_radioButton.setChecked(True)
        if params.motor_AC_inbetween == 1: self.Motor_AC_Inbetween_radioButton.setChecked(True)
        self.Motor_AC_Inbetween_Step_spinBox.setValue(params.motor_AC_inbetween_step)
    
        
    def update_flippulselength(self):
        params.flipangletime = self.Flipangle_Time_spinBox.value()

        if params.flipangletime != 90:
            params.flipangleamplitude = 90
            self.Flipangle_Amplitude_spinBox.setValue(params.flipangleamplitude)

        params.flippulselength = int(params.RFpulselength / 90 * params.flipangletime)
        
        if params.GSamplitude == 0: params.GSposttime = 0
        else: params.GSposttime = int((200 * params.GSamplitude + 4 * params.flippulselength * params.GSamplitude) / 2 - 200 * params.GSamplitude / 2) / (params.GSamplitude / 2)

        if params.autograd == 1:
            self.Deltaf = 1 / (params.flippulselength) * 1000000
            
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
                
            self.GPEtime = params.GROpretime + 200

            self.Gz = (2 * np.pi * self.Deltaf) / (2 * np.pi * 42.57 * (params.slicethickness))
            params.GSamplitude = int(self.Gz / self.Gzsens * 1000)
            
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1')

            if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1')

            if round(params.spoileramplitude) > 8500: self.GSpoiler_Amplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #eff0f1')

            self.Gz3D = (2 * np.pi / params.slicethickness) / (2 * np.pi * 42.57 * (self.GPEtime / 1000000))
            params.GSPEstep = int(self.Gz3D / self.Gzsens * 1000)
            
            if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B')
                else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1')

            self.update_gradients()

        if params.autofreqoffset == 1:

            self.Deltafs = (2 * np.pi * 42.57 * self.Gz * params.sliceoffset) / (2 * np.pi)

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
        
    def update_TI_stepping_linear(self):
        if self.TI_Stepping_Linear_radioButton.isChecked():
            params.TIstepping = 0
            self.TI_Stepping_Log_radioButton.setChecked(False)
        elif self.TI_Stepping_Linear_radioButton.isChecked() == False and self.TI_Stepping_Log_radioButton.isChecked() == False:
            params.TIstepping = 0
            self.TI_Stepping_Linear_radioButton.setChecked(True)
        params.saveFileParameter()

    def update_TI_stepping_log(self):
        if self.TI_Stepping_Log_radioButton.isChecked():
            params.TIstepping = 1
            self.TI_Stepping_Linear_radioButton.setChecked(False)
        elif self.TI_Stepping_Linear_radioButton.isChecked() == False and self.TI_Stepping_Log_radioButton.isChecked() == False:
            params.TIstepping = 0
            self.TI_Stepping_Linear_radioButton.setChecked(True)
        params.saveFileParameter()
        
    def update_TE_stepping_linear(self):
        if self.TE_Stepping_Linear_radioButton.isChecked():
            params.TEstepping = 0
            self.TE_Stepping_Log_radioButton.setChecked(False)
        elif self.TE_Stepping_Linear_radioButton.isChecked() == False and self.TE_Stepping_Log_radioButton.isChecked() == False:
            params.TEstepping = 0
            self.TE_Stepping_Linear_radioButton.setChecked(True)
        params.saveFileParameter()

    def update_TE_stepping_log(self):
        if self.TE_Stepping_Log_radioButton.isChecked():
            params.TEstepping = 1
            self.TE_Stepping_Linear_radioButton.setChecked(False)
        elif self.TE_Stepping_Linear_radioButton.isChecked() == False and self.TE_Stepping_Log_radioButton.isChecked() == False:
            params.TEstepping = 0
            self.TE_Stepping_Linear_radioButton.setChecked(True)
        params.saveFileParameter()

    def auto_freqoffset(self):

        if self.Auto_Frequency_Offset_radioButton.isChecked():
            params.autofreqoffset = 1
            self.update_params()
        else:
            params.autofreqoffset = 0

        params.saveFileParameter()

    def auto_gradients(self):

        if self.Auto_Gradients_radioButton.isChecked():
            params.autograd = 1
            self.update_params()
        else:
            params.autograd = 0

        params.saveFileParameter()
        
    def recalculate_gradients(self):
        proc.recalc_gradients()
        
        self.update_gradients()
        
    def update_params(self):
        params.flippulselength = int(params.RFpulselength / 90 * params.flipangletime)

        if params.GSamplitude == 0: params.GSposttime = 0
        else: params.GSposttime = int((200 * params.GSamplitude + 4 * params.flippulselength * params.GSamplitude) / 2 - 200 * params.GSamplitude / 2) / (params.GSamplitude / 2)

        params.TE = self.TE_doubleSpinBox.value()
        params.TI = self.TI_doubleSpinBox.value()
        params.TR = self.TR_spinBox.value()
        params.TS = self.Samplingtime_spinBox.value()
        params.SIR_TE = self.SIR_TE_doubleSpinBox.value()

        params.imageresolution = self.Image_Resolution_comboBox.currentIndex()

        if params.imageresolution == 0: params.nPE = 8
        elif params.imageresolution == 1: params.nPE = 16
        elif params.imageresolution == 2: params.nPE = 32
        elif params.imageresolution == 3: params.nPE = 64
        elif params.imageresolution == 4: params.nPE = 128
        elif params.imageresolution == 5: params.nPE = 256
        elif params.imageresolution == 6: params.nPE = 512

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
        params.projectionangleradmod100 = int((math.radians(params.projectionangle) % (2 * np.pi)) * 100)

        if self.Average_radioButton.isChecked(): params.average = 1
        else: params.average = 0
        
        params.averagecount = self.Average_spinBox.value()

        params.imageorientation = self.Image_Orientation_comboBox.currentIndex()

        params.FOV = self.FOV_doubleSpinBox.value()
        params.slicethickness = self.Slice_Thickness_doubleSpinBox.value()
        params.SPEsteps = self.SPEsteps_spinBox.value()
        params.radialosfactor = self.Radial_Oversampling_Factor_spinBox.value()

        if params.autograd == 1:
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

            self.update_gradients()

        else:
            self.Gz = 0

        params.Gdiffamplitude = self.GDiffamplitude_spinBox.value()
        if round(params.Gdiffamplitude) > 8500: self.GDiffamplitude_spinBox.setStyleSheet('color: red')
        else:
            if params.GUItheme == 0: self.GDiffamplitude_spinBox.setStyleSheet('color: #31363B')
            else: self.GDiffamplitude_spinBox.setStyleSheet('color: #eff0f1')

        params.sliceoffset = self.Slice_Offset_doubleSpinBox.value()

        if params.autofreqoffset == 1:

            self.Deltafs = (2 * np.pi * 42.57 * self.Gz * params.sliceoffset) / (2 * np.pi)

            if self.Deltafs >= 0:
                params.frequencyoffset = int(self.Deltafs)
                params.frequencyoffsetsign = 0
            else:
                params.frequencyoffset = int(abs(self.Deltafs))
                params.frequencyoffsetsign = 1

            self.update_freqoffset()

        params.phaseoffset = self.Phase_Offset_spinBox.value()
        params.phaseoffsetradmod100 = int((math.radians(params.phaseoffset) % (2 * np.pi)) * 100)

        params.radialanglestep = self.Radial_Angle_Step_spinBox.value()
        params.radialanglestepradmod100 = int((math.radians(params.radialanglestep) % (2 * np.pi)) * 100)
        
        params.motor_settling_time = self.Motor_Settling_Time_doubleSpinBox.value()
        self.Motor_AC_Position_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.Motor_AC_Position_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        params.motor_AC_position = self.Motor_AC_Position_doubleSpinBox.value()
        if self.Motor_AC_Position_Center_radioButton.isChecked():
            params.motor_AC_position_center = 1
            params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
            self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)
        else: params.motor_AC_position_center = 0
        if self.Motor_AC_Inbetween_radioButton.isChecked():params.motor_AC_inbetween= 1
        else: params.motor_AC_inbetween = 0
        params.motor_AC_inbetween_step = self.Motor_AC_Inbetween_Step_spinBox.value()

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
            if round(params.GROamplitude) < 300: self.GROamplitude_spinBox.setStyleSheet('color: yellow')
            elif round(2*params.GROamplitude) > 8500: self.GROamplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GROamplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.GROamplitude_spinBox.setStyleSheet('color: #eff0f1')

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
            if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1')
            
            params.spoileramplitude = self.Spoiler_Amplitude_spinBox.value()
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1')
            
            params.GSamplitude = self.GSamplitude_spinBox.value()
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1')
            
            params.GSPEstep = self.GSPEstep_spinBox.value()
            if round(params.GPEstep * params.nPE/2) > 8500: self.GPEstep_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GPEstep_spinBox.setStyleSheet('color: #31363B')
                else: self.GPEstep_spinBox.setStyleSheet('color: #eff0f1')
                
            if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B')
                else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1')

            params.saveFileParameter()

        elif params.autograd == 1:
            self.GROamplitude_spinBox.setValue(params.GROamplitude)
            if round(params.GROamplitude) < 300: self.GROamplitude_spinBox.setStyleSheet('color: yellow')
            elif round(2*params.GROamplitude) > 8500: self.GROamplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GROamplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.GROamplitude_spinBox.setStyleSheet('color: #eff0f1')
                
            self.GPEstep_spinBox.setValue(params.GPEstep)
            if round(params.GPEstep * params.nPE/2) > 8500: self.GPEstep_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GPEstep_spinBox.setStyleSheet('color: #31363B')
                else: self.GPEstep_spinBox.setStyleSheet('color: #eff0f1')
                
            self.Crusher_Amplitude_spinBox.setValue(params.crusheramplitude)
            if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1')
            
            self.Spoiler_Amplitude_spinBox.setValue(params.spoileramplitude)
            if round(params.spoileramplitude) > 8500: self.GSpoiler_Amplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #eff0f1')
            
            self.GSamplitude_spinBox.setValue(params.GSamplitude)
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1')
            
            self.GSPEstep_spinBox.setValue(params.GSPEstep)
            if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red')
            else:
                if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B')
                else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1')
            

class ConfigWindow(Config_Window_Form, Config_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ConfigWindow, self).__init__(parent)
        self.setupUi(self)

        self.load_params()

        self.ui = loadUi('ui/config.ui')
        self.setWindowTitle('Config')
        self.setGeometry(420, 40, 760, 940)

        # self.label_3.setToolTip('<img src='tooltip/test.png'>')
        self.Frequency_doubleSpinBox.setKeyboardTracking(False)
        self.Frequency_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label.setToolTip('Frequency of the RF carrier signal. Needs to be set to the Larmor frequency of the MRI system.')
        self.Center_pushButton.clicked.connect(lambda: self.frequency_center())
        self.Center_pushButton.setToolTip('Sets the RF frequency to the peak frequency of the last measured and processed spectrum.')
        self.auto_recenter_radioButton.toggled.connect(self.update_params)
        self.auto_recenter_radioButton.setToolTip('A spectrum is performed and the RF carrier frequency will recentered before imaging.')
        
        self.RF_Pulselength_spinBox.setKeyboardTracking(False)
        self.RF_Pulselength_spinBox.valueChanged.connect(self.update_params)
        self.label_2.setToolTip('The reference duration of a 90° RF hard pulse.\nThe 180° hard pulse is 2x this duration.\nThe 90° sinc pulse main peak is 2x this duration and has a total duration of 4x.\nThe 180° sinc pulse main peak is 4x this duration and has a total duration of 8x')
        self.RF_Attenuation_doubleSpinBox.setKeyboardTracking(False)
        self.RF_Attenuation_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_3.setToolTip('The attenuation of the OCRA1 RF attenuator.\nThis determinants the reference amplitude of the 90° and 180° pulse.')
        self.Readout_Bandwidth_spinBox.setKeyboardTracking(False)
        self.Readout_Bandwidth_spinBox.valueChanged.connect(self.update_params)
        self.label_11.setToolTip('Scales the image in readout direction.\nThis happens after the reconstruction.\nLike a digital zoom. Standard is 1.')
        self.Shim_X_spinBox.setKeyboardTracking(False)
        self.Shim_X_spinBox.valueChanged.connect(self.update_params)
        self.Shim_Y_spinBox.setKeyboardTracking(False)
        self.Shim_Y_spinBox.valueChanged.connect(self.update_params)
        self.Shim_Z_spinBox.setKeyboardTracking(False)
        self.Shim_Z_spinBox.valueChanged.connect(self.update_params)
        self.Shim_Z2_spinBox.setKeyboardTracking(False)
        self.Shim_Z2_spinBox.valueChanged.connect(self.update_params)
        self.Gradient_Scaling_X_doubleSpinBox.setKeyboardTracking(False)
        self.Gradient_Scaling_X_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Gradient_Scaling_Y_doubleSpinBox.setKeyboardTracking(False)
        self.Gradient_Scaling_Y_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Gradient_Scaling_Z_doubleSpinBox.setKeyboardTracking(False)
        self.Gradient_Scaling_Z_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.Average_Abs_radioButton.toggled.connect(self.update_average_abs)
        self.Average_Complex_radioButton.toggled.connect(self.update_average_complex)

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
        
        self.Undersampling_Methode_1_radioButton.toggled.connect(self.update_undersampling_methode1)
        self.Undersampling_Methode_2_radioButton.toggled.connect(self.update_undersampling_methode2)
        self.Undersampling_Time_spinBox.setKeyboardTracking(False)
        self.Undersampling_Time_spinBox.valueChanged.connect(self.update_params)
        self.Undersampling_Phase_spinBox.setKeyboardTracking(False)
        self.Undersampling_Phase_spinBox.valueChanged.connect(self.update_params)

        self.Undersampling_Time_radioButton.toggled.connect(self.update_params)
        self.Undersampling_Phase_radioButton.toggled.connect(self.update_params)

        self.GRO_Length_Scaler_doubleSpinBox.setKeyboardTracking(False)
        self.GRO_Length_Scaler_doubleSpinBox.valueChanged.connect(self.update_params)

        self.ln_kSpace_Magnitude_radioButton.toggled.connect(self.update_params)

        self.AC_Apply_pushButton.clicked.connect(lambda: self.Set_AC_centerfrequency())
        self.FA_Apply_pushButton.clicked.connect(lambda: self.Set_FA_RFattenution())
        self.Shim_Apply_pushButton.clicked.connect(lambda: self.Set_shim())
        self.Scaling_X_Apply_pushButton.clicked.connect(lambda: self.Set_scaling_X())
        self.Scaling_Y_Apply_pushButton.clicked.connect(lambda: self.Set_scaling_Y())
        self.Scaling_Z_Apply_pushButton.clicked.connect(lambda: self.Set_scaling_Z())

        self.RX1_radioButton.toggled.connect(self.update_params)
        self.RX2_radioButton.toggled.connect(self.update_params)

        self.SignalMask_doubleSpinBox.setKeyboardTracking(False)
        self.SignalMask_doubleSpinBox.valueChanged.connect(self.update_params)
        self.label_28.setToolTip('Image mask for overlays like T1, T2 or field maps. Draw all pixels with a signal strength above the value times the maximum pixel signal strength. Default value is 0.5.')

        self.GUI_Light_radioButton.clicked.connect(self.update_light)
        self.GUI_Dark_radioButton.clicked.connect(self.update_dark)

        self.Header_File_Format_comboBox.clear()
        self.Header_File_Format_comboBox.addItems(['.txt', '.json'])
        self.Header_File_Format_comboBox.setCurrentIndex(params.headerfileformat)

        self.Header_File_Format_comboBox.currentIndexChanged.connect(self.update_params)
        
        self.Auto_Data_Process_radioButton.toggled.connect(self.update_params)
        self.Single_Plot_radioButton.toggled.connect(self.update_params)
        self.Measurement_Time_Dialog_radioButton.toggled.connect(self.update_params)
        self.Image_Grid_radioButton.toggled.connect(self.update_params)
        
        self.Projection3D_radioButton.toggled.connect(self.update_params)
        self.Projection3D_Quality_Low_radioButton.toggled.connect(self.update_proj3D_quality_low)
        self.Projection3D_Quality_High_radioButton.toggled.connect(self.update_proj3D_quality_high)
        
        self.Image_Colormap_comboBox.clear()
        self.Image_Colormap_comboBox.addItems(['viridis', 'jet', 'gray', 'bone', 'inferno', 'plasma'])
        if params.imagecolormap == 'viridis': self.Image_Colormap_comboBox.setCurrentIndex(0)
        elif params.imagecolormap == 'jet': self.Image_Colormap_comboBox.setCurrentIndex(1)
        elif params.imagecolormap == 'gray': self.Image_Colormap_comboBox.setCurrentIndex(2)
        elif params.imagecolormap == 'bone': self.Image_Colormap_comboBox.setCurrentIndex(3)
        elif params.imagecolormap == 'inferno': self.Image_Colormap_comboBox.setCurrentIndex(4)
        elif params.imagecolormap == 'plasma': self.Image_Colormap_comboBox.setCurrentIndex(5)
        self.Image_Colormap_comboBox.currentIndexChanged.connect(self.update_params)
        
        self.PB_Marker_IsoCenter_Distance_doubleSpinBox.setKeyboardTracking(False)
        self.PB_Marker_IsoCenter_Distance_doubleSpinBox.valueChanged.connect(self.update_params)
        self.PB_IsoCenter_Position_doubleSpinBox.setKeyboardTracking(False)
        self.PB_IsoCenter_Position_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.PB_Marker_Cal_Apply_pushButton.clicked.connect(lambda: self.Set_PB_Marker_IsoCenter_Distance())
        
        self.AgriMRI_Mode_radioButton.toggled.connect(self.update_params)
        
        self.label_16.setStyleSheet('font-size: 12px')
        self.label_17.setStyleSheet('font-size: 12px')
        self.label_18.setStyleSheet('font-size: 12px')
        self.label_32.setStyleSheet('font-size: 12px')
        
        self.label_25.setStyleSheet('font-size: 14px')
        self.label_47.setStyleSheet('font-size: 14px')

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
        self.Shim_X_spinBox.setValue(params.grad[0])
        self.Shim_Y_spinBox.setValue(params.grad[1])
        self.Shim_Z_spinBox.setValue(params.grad[2])
        self.Shim_Z2_spinBox.setValue(params.grad[3])
        self.Gradient_Scaling_X_doubleSpinBox.setValue(params.gradsens[0])
        self.Gradient_Scaling_Y_doubleSpinBox.setValue(params.gradsens[1])
        self.Gradient_Scaling_Z_doubleSpinBox.setValue(params.gradsens[2])

        if params.imagplots == 1: self.Images_Plot_radioButton.setChecked(True)
        if params.imagefilter == 1: self.Image_Filter_radioButton.setChecked(True)
        
        if params.average_complex == 1:
            self.Average_Complex_radioButton.setChecked(True)
            self.Average_Abs_radioButton.setChecked(False)
        else:
            self.Average_Complex_radioButton.setChecked(False)
            self.Average_Abs_radioButton.setChecked(True)
            
        if params.usmethode == 1:
            self.Undersampling_Methode_1_radioButton.setChecked(True)
            self.Undersampling_Methode_2_radioButton.setChecked(False)
        else:
            self.Undersampling_Methode_1_radioButton.setChecked(False)
            self.Undersampling_Methode_2_radioButton.setChecked(True)
        
        self.Undersampling_Time_spinBox.setValue(params.ustimeidx)
        self.Undersampling_Phase_spinBox.setValue(params.usphaseidx)
        if params.ustime == 1: self.Undersampling_Time_radioButton.setChecked(True)
        if params.usphase == 1: self.Undersampling_Phase_radioButton.setChecked(True)
        
        self.kSpace_Cut_Center_spinBox.setValue(params.cutcentervalue)
        self.kSpace_Cut_Center_spinBox.setValue(params.cutcentervalue)
        if params.cutcirc == 1: self.kspace_cut_circ_radioButton.setChecked(True)
        if params.cutrec == 1: self.kspace_cut_rec_radioButton.setChecked(True)
        if params.cutcenter == 1: self.kSpace_Cut_Center_radioButton.setChecked(True)
        if params.cutoutside == 1: self.kSpace_Cut_Outside_radioButton.setChecked(True)

        self.GRO_Length_Scaler_doubleSpinBox.setValue(params.GROpretimescaler)

        if params.lnkspacemag == 1: self.ln_kSpace_Magnitude_radioButton.setChecked(True)

        if params.rx1 == 1: self.RX1_radioButton.setChecked(True)
        if params.rx2 == 1: self.RX2_radioButton.setChecked(True)

        self.SignalMask_doubleSpinBox.setValue(params.signalmask)

        if params.GUItheme == 0: self.GUI_Light_radioButton.setChecked(True)
        if params.GUItheme == 1: self.GUI_Dark_radioButton.setChecked(True)
        
        if params.autodataprocess == 1: self.Auto_Data_Process_radioButton.setChecked(True)
        if params.single_plot == 1: self.Single_Plot_radioButton.setChecked(True)
        if params.measurement_time_dialog == 1: self.Measurement_Time_Dialog_radioButton.setChecked(True)
        if params.image_grid == 1: self.Image_Grid_radioButton.setChecked(True)
        
        if params.projection3D == 1: self.Projection3D_radioButton.setChecked(True)
        if params.projection3D_quality == 1:
            self.Projection3D_Quality_High_radioButton.setChecked(True)
            self.Projection3D_Quality_Low_radioButton.setChecked(False)
        else:
            self.Projection3D_Quality_High_radioButton.setChecked(False)
            self.Projection3D_Quality_Low_radioButton.setChecked(True)
        
        if params.imagecolormap == 'viridis': self.Image_Colormap_comboBox.setCurrentIndex(0)
        elif params.imagecolormap == 'jet': self.Image_Colormap_comboBox.setCurrentIndex(1)
        elif params.imagecolormap == 'gray': self.Image_Colormap_comboBox.setCurrentIndex(2)
        elif params.imagecolormap == 'bone': self.Image_Colormap_comboBox.setCurrentIndex(3)
        elif params.imagecolormap == 'inferno': self.Image_Colormap_comboBox.setCurrentIndex(4)
        elif params.imagecolormap == 'plasma': self.Image_Colormap_comboBox.setCurrentIndex(5)

        self.PB_Marker_IsoCenter_Distance_doubleSpinBox.setValue(params.PB_marker_isocenter_distance)
        self.PB_Marker_IsoCenter_Distance_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.PB_Marker_IsoCenter_Distance_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        self.PB_IsoCenter_Position_doubleSpinBox.setValue(params.PB_isocenter_position)
        self.PB_IsoCenter_Position_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.PB_IsoCenter_Position_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        
        if params.agriMRI_mode == 1: self.AgriMRI_Mode_radioButton.setChecked(True)

    def update_params(self):
        params.frequency = self.Frequency_doubleSpinBox.value()
        if self.auto_recenter_radioButton.isChecked(): params.autorecenter = 1
        else: params.autorecenter = 0
        params.RFpulselength = (round(self.RF_Pulselength_spinBox.value() / 10) * 10)
        params.flippulselength = int(params.RFpulselength / 90 * params.flipangletime)

        if params.GSamplitude == 0: params.GSposttime = 0
        else: params.GSposttime = int((200 * params.GSamplitude + 4 * params.flippulselength * params.GSamplitude) / 2 - 200 * params.GSamplitude / 2) / (params.GSamplitude / 2)

        params.RFattenuation = self.RF_Attenuation_doubleSpinBox.value()
        params.ROBWscaler = self.Readout_Bandwidth_spinBox.value()
        params.grad[0] = self.Shim_X_spinBox.value()
        params.grad[1] = self.Shim_Y_spinBox.value()
        params.grad[2] = self.Shim_Z_spinBox.value()
        params.grad[3] = self.Shim_Z2_spinBox.value()
        params.gradsens[0] = self.Gradient_Scaling_X_doubleSpinBox.value()
        params.gradsens[1] = self.Gradient_Scaling_Y_doubleSpinBox.value()
        params.gradsens[2] = self.Gradient_Scaling_Z_doubleSpinBox.value()

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

        params.ustimeidx = self.Undersampling_Time_spinBox.value()
        params.usphaseidx = self.Undersampling_Phase_spinBox.value()

        params.GROpretimescaler = self.GRO_Length_Scaler_doubleSpinBox.value()

        if self.ln_kSpace_Magnitude_radioButton.isChecked(): params.lnkspacemag = 1
        else: params.lnkspacemag = 0

        if self.RX1_radioButton.isChecked(): params.rx1 = 1
        else: params.rx1 = 0
        if self.RX2_radioButton.isChecked(): params.rx2 = 1
        else: params.rx2 = 0

        if params.rx1 == 0 and params.rx2 == 0:
            params.rxmode = 3
            print('\033[1m' + 'No RX port selected!' + '\033[0m')
        elif params.rx1 == 1 and params.rx2 == 0:
            params.rxmode = 1
        elif params.rx1 == 0 and params.rx2 == 1:
            params.rxmode = 2
        elif params.rx1 == 1 and params.rx2 == 1:
            params.rxmode = 0
            print('\033[1m' + 'Mixed signal!' + '\033[0m')

        params.signalmask = self.SignalMask_doubleSpinBox.value()

        if self.Header_File_Format_comboBox.currentIndex() == 0: params.headerfileformat = 0
        elif self.Header_File_Format_comboBox.currentIndex() == 1: params.headerfileformat = 1
            
        if self.Auto_Data_Process_radioButton.isChecked(): params.autodataprocess = 1
        else: params.autodataprocess = 0
        
        if self.Single_Plot_radioButton.isChecked(): params.single_plot = 1
        else: params.single_plot = 0
        
        if self.Measurement_Time_Dialog_radioButton.isChecked(): params.measurement_time_dialog = 1
        else: params.measurement_time_dialog = 0
        
        if self.Image_Grid_radioButton.isChecked(): params.image_grid = 1
        else: params.image_grid = 0
        
        if self.Projection3D_radioButton.isChecked(): params.projection3D = 1
        else: params.projection3D = 0
        
        if self.Image_Colormap_comboBox.currentIndex() == 0: params.imagecolormap = 'viridis'
        elif self.Image_Colormap_comboBox.currentIndex() == 1: params.imagecolormap = 'jet'
        elif self.Image_Colormap_comboBox.currentIndex() == 2: params.imagecolormap = 'gray'
        elif self.Image_Colormap_comboBox.currentIndex() == 3: params.imagecolormap = 'bone'
        elif self.Image_Colormap_comboBox.currentIndex() == 4: params.imagecolormap = 'inferno'
        elif self.Image_Colormap_comboBox.currentIndex() == 5: params.imagecolormap = 'plasma'
        
        params.PB_marker_isocenter_distance = self.PB_Marker_IsoCenter_Distance_doubleSpinBox.value()
        params.PB_isocenter_position = self.PB_IsoCenter_Position_doubleSpinBox.value()
        
        if self.AgriMRI_Mode_radioButton.isChecked(): params.agriMRI_mode = 1
        else: params.agriMRI_mode = 0
        
        params.saveFileParameter()

    def update_light(self):
        if self.GUI_Light_radioButton.isChecked():
            params.GUItheme = 0
            self.GUI_Dark_radioButton.setChecked(False)
        elif self.GUI_Light_radioButton.isChecked() == False and self.GUI_Dark_radioButton.isChecked() == False:
            params.GUItheme = 0
            self.GUI_Light_radioButton.setChecked(True)
        params.saveFileParameter()

    def update_dark(self):
        if self.GUI_Dark_radioButton.isChecked():
            params.GUItheme = 1
            self.GUI_Light_radioButton.setChecked(False)
        elif self.GUI_Light_radioButton.isChecked() == False and self.GUI_Dark_radioButton.isChecked() == False:
            params.GUItheme = 0
            self.GUI_Light_radioButton.setChecked(True)
        params.saveFileParameter()

    def Set_AC_centerfrequency(self):
        params.frequency = params.Reffrequency
        params.saveFileParameter()
        self.Frequency_doubleSpinBox.setValue(params.frequency)
        print('Tool reference frequency applied!')

    def Set_FA_RFattenution(self):
        params.RFattenuation = params.RefRFattenuation
        params.saveFileParameter()
        self.RF_Attenuation_doubleSpinBox.setValue(params.RFattenuation)
        print('Tool reference attenuation applied!')
        
    def Set_shim(self):
        if params.STgrad[0] == 1:
            if params.ToolShimChannel[0] == 1:
                if np.max(params.STvalues[1, :]) != 0:
                    self.Shim_X_spinBox.setValue(int(params.STgrad[1]))
                    print('Tool reference X shim applied')
                else: print('No reference X shim value')
            if params.ToolShimChannel[1] == 1:
                if np.max(params.STvalues[2, :]) != 0:
                    self.Shim_Y_spinBox.setValue(int(params.STgrad[2]))
                    print('Tool reference Y shim applied')
                else: print('No reference Y shim value')
            if params.ToolShimChannel[2] == 1:
                if np.max(params.STvalues[3, :]) != 0:
                    self.Shim_Z_spinBox.setValue(int(params.STgrad[3]))
                    print('Tool reference Z shim applied')
                else: print('No reference Z shim value')
            if params.ToolShimChannel[3] == 1:
                if np.max(params.STvalues[4, :]) != 0:
                    self.Shim_Z2_spinBox.setValue(int(params.STgrad[4]))
                    print('Tool reference Z2 shim applied')
                else: print('No reference Z2 shim value')
            if params.ToolShimChannel == [0, 0, 0, 0]:
                print('Please select shim channel in Tools!')
        elif params.STgrad[0] == 2:
            if params.ToolShimChannel[0] == 1:
                if np.max(params.AutoSTvalues[1, :]) != 0:
                    self.Shim_X_spinBox.setValue(int(params.STgrad[1]))
                    print('Tool reference X shim applied')
                else: print('No reference X shim value')
            if params.ToolShimChannel[1] == 1:
                if np.max(params.AutoSTvalues[3, :]) != 0:
                    self.Shim_Y_spinBox.setValue(int(params.STgrad[2]))
                    print('Tool reference Y shim applied')
                else: print('No reference Y shim value')
            if params.ToolShimChannel[2] == 1:
                if np.max(params.AutoSTvalues[5, :]) != 0:
                    self.Shim_Z_spinBox.setValue(int(params.STgrad[3]))
                    print('Tool reference Z shim applied')
                else: print('No reference Z shim value')
            if params.ToolShimChannel[3] == 1:
                if np.max(params.AutoSTvalues[7, :]) != 0:
                    self.Shim_Z2_spinBox.setValue(int(params.STgrad[4]))
                    print('Tool reference Z2 shim applied')
                else: print('No reference Z2 shim value')
            if params.ToolShimChannel == [0, 0, 0, 0]:
                print('Please select shim channel in Tools!')
        else: print('No tool reference shim data!')
        
    def Set_scaling_X(self):
        params.gradsens[0] = round(params.gradsenstool[0], 1)
        params.saveFileParameter()
        self.Gradient_Scaling_X_doubleSpinBox.setValue(params.gradsens[0])
        print('Tool reference scaling X applied!')
        
    def Set_scaling_Y(self):
        params.gradsens[1] = round(params.gradsenstool[1], 1)
        params.saveFileParameter()
        self.Gradient_Scaling_Y_doubleSpinBox.setValue(params.gradsens[1])
        print('Tool reference scaling Y applied!')
        
    def Set_scaling_Z(self):
        params.gradsens[2] = round(params.gradsenstool[2], 1)
        params.saveFileParameter()
        self.Gradient_Scaling_Z_doubleSpinBox.setValue(params.gradsens[2])
        print('Tool reference scaling Z applied!')
        
    def Set_PB_Marker_IsoCenter_Distance(self):
        params.PB_marker_isocenter_distance = params.Ref_PB_marker_isocenter_distance
        params.saveFileParameter()
        self.PB_Marker_IsoCenter_Distance_doubleSpinBox.setValue(params.PB_marker_isocenter_distance)
        print('Tool reference marker-IsoCenter distance applied!')
        
    def update_average_abs(self):
        if self.Average_Abs_radioButton.isChecked():
            params.average_complex = 0
            self.Average_Complex_radioButton.setChecked(False)
        elif self.Average_Abs_radioButton.isChecked() == False and self.Average_Complex_radioButton.isChecked() == False:
            params.average_complex = 0
            self.Average_Complex_radioButton.setChecked(True)
        params.saveFileParameter()

    def update_average_complex(self):
        if self.Average_Complex_radioButton.isChecked():
            params.average_complex = 1
            self.Average_Abs_radioButton.setChecked(False)
        elif self.Average_Abs_radioButton.isChecked() == False and self.Average_Complex_radioButton.isChecked() == False:
            params.average_complex = 0
            self.Average_Complex_radioButton.setChecked(True)
        params.saveFileParameter()
            
    def update_undersampling_methode1(self):
        if self.Undersampling_Methode_1_radioButton.isChecked():
            params.usmethode = 1
            self.Undersampling_Methode_2_radioButton.setChecked(False)
        elif self.Undersampling_Methode_1_radioButton.isChecked() == False and self.Undersampling_Methode_2_radioButton.isChecked() == False:
            params.usmethode = 1
            self.Undersampling_Methode_1_radioButton.setChecked(True)
        params.saveFileParameter()

    def update_undersampling_methode2(self):
        if self.Undersampling_Methode_2_radioButton.isChecked():
            params.usmethode = 2
            self.Undersampling_Methode_1_radioButton.setChecked(False)
        elif self.Undersampling_Methode_1_radioButton.isChecked() == False and self.Undersampling_Methode_2_radioButton.isChecked() == False:
            params.usmethode = 1
            self.Undersampling_Methode_1_radioButton.setChecked(True)
        params.saveFileParameter()
            
    def update_proj3D_quality_low(self):
        if self.Projection3D_Quality_Low_radioButton.isChecked():
            params.projection3D_quality = 0
            self.Projection3D_Quality_High_radioButton.setChecked(False)
        elif self.Projection3D_Quality_Low_radioButton.isChecked() == False and self.Projection3D_Quality_High_radioButton.isChecked() == False:
            params.projection3D_quality = 0
            self.Projection3D_Quality_Low_radioButton.setChecked(True)
        params.saveFileParameter()

    def update_proj3D_quality_high(self):
        if self.Projection3D_Quality_High_radioButton.isChecked():
            params.projection3D_quality = 1
            self.Projection3D_Quality_Low_radioButton.setChecked(False)
        elif self.Projection3D_Quality_Low_radioButton.isChecked() == False and self.Projection3D_Quality_High_radioButton.isChecked() == False:
            params.projection3D_quality = 0
            self.Projection3D_Quality_Low_radioButton.setChecked(True)
        params.saveFileParameter()
        
class AgriMRIMetadataWindow(AgriMRI_Window_Form, AgriMRI_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(AgriMRIMetadataWindow, self).__init__(parent)
        self.setupUi(self)
                
        self.load_params()

        self.ui = loadUi('ui/agriMRI.ui')
        self.setWindowTitle('AgriMRI Metadata')
        self.setGeometry(420, 40, 750, 1000)
        
        self.Experiment_ID_lineEdit.editingFinished.connect(lambda: self.set_Experiment_ID())
        self.Plant_ID_lineEdit.editingFinished.connect(lambda: self.set_Plant_ID())
        self.Plant_Part_ID_lineEdit.editingFinished.connect(lambda: self.set_Plant_Part_ID())
        
        self.Plant_Species_comboBox.clear()
        self.Plant_Species_comboBox.addItems(params.plant_species_list)
        self.Plant_Species_comboBox.setCurrentIndex(0)
        self.Plant_Species_comboBox.currentIndexChanged.connect(lambda: self.set_Species())
        
        self.Plant_Cultivated_Variant_lineEdit.editingFinished.connect(lambda: self.update_params())
        self.Plant_Part_Name_lineEdit.editingFinished.connect(lambda: self.update_params())
        self.Plant_Date_Of_Sowing_dateEdit.userDateChanged.connect(lambda: self.set_Date_Of_Sowing())
        self.Plant_Measurement_Date_dateEdit.userDateChanged.connect(lambda: self.set_Measurement_Date())
        self.Plant_Measurement_Date_Today_pushButton.clicked.connect(lambda: self.set_Measurement_Date_Today())
        self.Plant_Measurement_DAS_spinBox.setKeyboardTracking(False)
        self.Plant_Measurement_DAS_spinBox.valueChanged.connect(lambda: self.set_Measurement_DAS())
        
        self.Plant_Phenological_Phase_comboBox.clear()
        self.Plant_Phenological_Phase_comboBox.addItems(params.plant_phenological_phases_list)
        self.Plant_Phenological_Phase_comboBox.setCurrentIndex(0)
        self.Plant_Phenological_Phase_comboBox.currentIndexChanged.connect(lambda: self.set_Phenological_Phase())
        
        self.Plant_Show_Phase_Images_pushButton.clicked.connect(lambda: self.show_Phase_Images())
        
        self.Plant_Environment_Outside_radioButton.toggled.connect(self.update_params)
        self.Plant_Environment_Inside_radioButton.toggled.connect(self.update_params)
        
        self.Plant_Light_Source_Sun_radioButton.toggled.connect(self.update_params)
        self.Plant_Light_Source_Grow_Light_radioButton.toggled.connect(self.update_params)
        self.Plant_Light_Source_Artificial_radioButton.toggled.connect(self.update_params)
        self.Plant_Light_Availability_spinBox.setKeyboardTracking(False)
        self.Plant_Light_Availability_spinBox.valueChanged.connect(self.update_params)
        
        self.Plant_Water_Availability_spinBox.setKeyboardTracking(False)
        self.Plant_Water_Availability_spinBox.valueChanged.connect(self.update_params)
        
        self.Plant_Seed_Coating_lineEdit.editingFinished.connect(lambda: self.update_params())
        
        self.Plant_Nutrient_Application_comboBox.clear()
        self.Plant_Nutrient_Application_comboBox.addItems(['1', '2', '3', '4','5', '6', '7', '8','9', '10'])
        self.Plant_Nutrient_Application_comboBox.setCurrentIndex(0)
        self.Plant_Nutrient_Application_comboBox.currentIndexChanged.connect(lambda: self.set_Nutrient_Application())
        self.Plant_Nutrient_Date_dateEdit.userDateChanged.connect(lambda: self.set_Nutrient_Date())
        self.Plant_Nutrient_DAS_spinBox.setKeyboardTracking(False)
        self.Plant_Nutrient_DAS_spinBox.valueChanged.connect(lambda: self.set_Nutrient_DAS())
        self.Plant_Nitrogen_spinBox.setKeyboardTracking(False)
        self.Plant_Nitrogen_spinBox.valueChanged.connect(self.update_params)
        self.Plant_Phosphorus_spinBox.setKeyboardTracking(False)
        self.Plant_Phosphorus_spinBox.valueChanged.connect(self.update_params)
        self.Plant_Potassium_spinBox.setKeyboardTracking(False)
        self.Plant_Potassium_spinBox.valueChanged.connect(self.update_params)
        
        self.Plant_Stimulant_Application_comboBox.clear()
        self.Plant_Stimulant_Application_comboBox.addItems(['1', '2', '3', '4','5', '6', '7', '8','9', '10'])
        self.Plant_Stimulant_Application_comboBox.setCurrentIndex(0)
        self.Plant_Stimulant_Application_comboBox.currentIndexChanged.connect(lambda: self.set_Stimulant_Application())
        self.Plant_Stimulant_Product_Name_lineEdit.editingFinished.connect(lambda: self.update_params())
        self.Plant_Stimulant_Date_dateEdit.userDateChanged.connect(lambda: self.set_Stimulant_Date())
        self.Plant_Stimulant_DAS_spinBox.setKeyboardTracking(False)
        self.Plant_Stimulant_DAS_spinBox.valueChanged.connect(lambda: self.set_Stimulant_DAS())
        self.Plant_Stimulant_Dose_spinBox.setKeyboardTracking(False)
        self.Plant_Stimulant_Dose_spinBox.valueChanged.connect(self.update_params)
        
        self.Plant_Protection_Application_comboBox.clear()
        self.Plant_Protection_Application_comboBox.addItems(['1', '2', '3', '4','5', '6', '7', '8','9', '10'])
        self.Plant_Protection_Application_comboBox.setCurrentIndex(0)
        self.Plant_Protection_Application_comboBox.currentIndexChanged.connect(lambda: self.set_Protection_Application())
        self.Plant_Protection_Product_Name_lineEdit.editingFinished.connect(lambda: self.update_params())
        self.Plant_Protection_Date_dateEdit.userDateChanged.connect(lambda: self.set_Protection_Date())
        self.Plant_Protection_DAS_spinBox.setKeyboardTracking(False)
        self.Plant_Protection_DAS_spinBox.valueChanged.connect(lambda: self.set_Protection_DAS())
        self.Plant_Protection_Dose_spinBox.setKeyboardTracking(False)
        self.Plant_Protection_Dose_spinBox.valueChanged.connect(self.update_params)
        
        self.Experiment_Description_textEdit.textChanged.connect(lambda: self.set_Experiment_Description())
        self.Plant_Description_textEdit.textChanged.connect(lambda: self.set_Plant_Description())
    
    def load_params(self):
        self.Experiment_ID_lineEdit.blockSignals(True)
        self.Plant_ID_lineEdit.blockSignals(True)
        self.Plant_Part_ID_lineEdit.blockSignals(True)
        self.Plant_Cultivated_Variant_lineEdit.blockSignals(True)
        self.Plant_Part_Name_lineEdit.blockSignals(True)
        self.Plant_Species_comboBox.blockSignals(True)
        self.Plant_Date_Of_Sowing_dateEdit.blockSignals(True)
        self.Plant_Measurement_Date_dateEdit.blockSignals(True)
        self.Plant_Measurement_DAS_spinBox.blockSignals(True)
        self.Plant_Phenological_Phase_comboBox.blockSignals(True)
        self.Plant_Environment_Outside_radioButton.blockSignals(True)
        self.Plant_Environment_Inside_radioButton.blockSignals(True)
        self.Plant_Light_Source_Sun_radioButton.blockSignals(True)
        self.Plant_Light_Source_Grow_Light_radioButton.blockSignals(True)
        self.Plant_Light_Source_Artificial_radioButton.blockSignals(True)
        self.Plant_Light_Availability_spinBox.blockSignals(True)
        self.Plant_Water_Availability_spinBox.blockSignals(True)
        self.Plant_Seed_Coating_lineEdit.blockSignals(True)
        self.Plant_Nutrient_Application_comboBox.blockSignals(True)
        self.Plant_Nutrient_Date_dateEdit.blockSignals(True)
        self.Plant_Nutrient_DAS_spinBox.blockSignals(True)
        self.Plant_Nitrogen_spinBox.blockSignals(True)
        self.Plant_Phosphorus_spinBox.blockSignals(True)
        self.Plant_Potassium_spinBox.blockSignals(True)
        self.Plant_Stimulant_Application_comboBox.blockSignals(True)
        self.Plant_Stimulant_Product_Name_lineEdit.blockSignals(True) 
        self.Plant_Stimulant_Date_dateEdit.blockSignals(True)
        self.Plant_Stimulant_DAS_spinBox.blockSignals(True)
        self.Plant_Stimulant_Dose_spinBox.blockSignals(True)
        self.Plant_Protection_Application_comboBox.blockSignals(True)
        self.Plant_Protection_Product_Name_lineEdit.blockSignals(True) 
        self.Plant_Protection_Date_dateEdit.blockSignals(True)
        self.Plant_Protection_DAS_spinBox.blockSignals(True)
        self.Plant_Protection_Dose_spinBox.blockSignals(True)
        self.Plant_Species_comboBox.setCurrentIndex(params.plant_species_index)
        self.Plant_Scientific_Name_lineEdit.setText(params.plant_scientific_name)
        self.Plant_Taxonomy_lineEdit.setText(params.plant_taxonomy)
        
        self.Experiment_ID_lineEdit.setText(params.experiment_ID)
        self.Plant_ID_lineEdit.setText(params.plant_ID)
        self.Plant_Part_ID_lineEdit.setText(params.plant_part_ID)
        self.Plant_Cultivated_Variant_lineEdit.setText(params.plant_cultivated_variant)
        self.Plant_Part_Name_lineEdit.setText(params.plant_part_name)
        
        self.Plant_Date_Of_Sowing_dateEdit.setDate(params.plant_date_of_sowing)
        self.Plant_Measurement_Date_dateEdit.setDate(params.plant_measurement_date)
        self.Plant_Measurement_DAS_spinBox.setValue(params.plant_measurement_das)

        self.Plant_Phenological_Phase_comboBox.clear()
        self.Plant_Phenological_Phase_comboBox.addItems(params.plant_phenological_phases_list)
        self.Plant_Phenological_Phase_comboBox.setCurrentIndex(params.plant_phenological_phase_index)
        if params.plant_BBCH_scale == 'General': self.Plant_Phenological_Phase_comboBox.setStyleSheet('color: orange;')
        else: 
            if params.GUItheme == 0: self.Plant_Phenological_Phase_comboBox.setStyleSheet('color: #31363B')
            else: self.Plant_Phenological_Phase_comboBox.setStyleSheet('color: #eff0f1')
        
        if params.plant_environment_outside == 1: self.Plant_Environment_Outside_radioButton.setChecked(True)
        else: self.Plant_Environment_Outside_radioButton.setChecked(False)
        if params.plant_environment_inside == 1: self.Plant_Environment_Inside_radioButton.setChecked(True)
        else: self.Plant_Environment_Inside_radioButton.setChecked(False)
            
        if params.plant_light_source_sun == 1: self.Plant_Light_Source_Sun_radioButton.setChecked(True)
        else: self.Plant_Light_Source_Sun_radioButton.setChecked(False)
        if params.plant_light_source_grow_light == 1: self.Plant_Light_Source_Grow_Light_radioButton.setChecked(True)
        else: self.Plant_Light_Source_Grow_Light_radioButton.setChecked(False)
        if params.plant_light_source_artificial == 1: self.Plant_Light_Source_Artificial_radioButton.setChecked(True)
        else: self.Plant_Light_Source_Artificial_radioButton.setChecked(False)

        self.Plant_Light_Availability_spinBox.setValue(params.plant_light_availability)
        self.Plant_Water_Availability_spinBox.setValue(params.plant_water_availability)
        
        self.Plant_Seed_Coating_lineEdit.setText(params.plant_seed_coating)
        
        self.Plant_Nutrient_Application_comboBox.setCurrentIndex(params.plant_nutrient_application_index)
        try: self.Plant_Nutrient_Date_dateEdit.setDate(params.plant_nutrient_date[params.plant_nutrient_application_index])
        except: self.Plant_Nutrient_Date_dateEdit.setDate(datetime.datetime.strptime('2025-01-01','%Y-%m-%d'))
        self.Plant_Nutrient_DAS_spinBox.setValue(params.plant_nutrient_das[params.plant_nutrient_application_index])
        self.Plant_Nitrogen_spinBox.setValue(params.plant_nitrogen[params.plant_nutrient_application_index])
        self.Plant_Phosphorus_spinBox.setValue(params.plant_phosphorus[params.plant_nutrient_application_index])
        self.Plant_Potassium_spinBox.setValue(params.plant_potassium[params.plant_nutrient_application_index])
        
        self.Plant_Stimulant_Application_comboBox.setCurrentIndex(params.plant_stimulant_application_index)
        self.Plant_Stimulant_Product_Name_lineEdit.setText(params.plant_stimulant_product_name[params.plant_stimulant_application_index])
        try: self.Plant_Stimulant_Date_dateEdit.setDate(params.plant_stimulant_date[params.plant_stimulant_application_index])
        except: self.Plant_Stimulant_Date_dateEdit.setDate(datetime.datetime.strptime('2025-01-01','%Y-%m-%d'))
        self.Plant_Stimulant_DAS_spinBox.setValue(params.plant_stimulant_das[params.plant_stimulant_application_index])
        self.Plant_Stimulant_Dose_spinBox.setValue(params.plant_stimulant_dose[params.plant_stimulant_application_index])
        
        self.Plant_Protection_Application_comboBox.setCurrentIndex(params.plant_protection_application_index)
        self.Plant_Protection_Product_Name_lineEdit.setText(str(params.plant_protection_product_name[params.plant_protection_application_index]))
        try: self.Plant_Protection_Date_dateEdit.setDate(params.plant_protection_date[params.plant_protection_application_index])
        except: self.Plant_Protection_Date_dateEdit.setDate(datetime.datetime.strptime('2025-01-01','%Y-%m-%d'))
        self.Plant_Protection_DAS_spinBox.setValue(params.plant_protection_das[params.plant_protection_application_index])
        self.Plant_Protection_Dose_spinBox.setValue(params.plant_protection_dose[params.plant_protection_application_index])
        
        self.Experiment_Description_textEdit.setText(params.experiment_description)
        self.Plant_Description_textEdit.setText(params.plant_description)
        
        self.Experiment_ID_lineEdit.blockSignals(False)
        self.Plant_ID_lineEdit.blockSignals(False)
        self.Plant_Part_ID_lineEdit.blockSignals(False)
        self.Plant_Cultivated_Variant_lineEdit.blockSignals(False)
        self.Plant_Part_Name_lineEdit.blockSignals(False)
        self.Plant_Species_comboBox.blockSignals(False)
        self.Plant_Date_Of_Sowing_dateEdit.blockSignals(False)
        self.Plant_Measurement_Date_dateEdit.blockSignals(False)
        self.Plant_Measurement_DAS_spinBox.blockSignals(False)
        self.Plant_Phenological_Phase_comboBox.blockSignals(False)
        self.Plant_Environment_Outside_radioButton.blockSignals(False)
        self.Plant_Environment_Inside_radioButton.blockSignals(False)
        self.Plant_Light_Source_Sun_radioButton.blockSignals(False)
        self.Plant_Light_Source_Grow_Light_radioButton.blockSignals(False)
        self.Plant_Light_Source_Artificial_radioButton.blockSignals(False)
        self.Plant_Light_Availability_spinBox.blockSignals(False)
        self.Plant_Water_Availability_spinBox.blockSignals(False)
        self.Plant_Seed_Coating_lineEdit.blockSignals(False)
        self.Plant_Nutrient_Application_comboBox.blockSignals(False)
        self.Plant_Nutrient_Date_dateEdit.blockSignals(False)
        self.Plant_Nutrient_DAS_spinBox.blockSignals(False)
        self.Plant_Nitrogen_spinBox.blockSignals(False)
        self.Plant_Phosphorus_spinBox.blockSignals(False)
        self.Plant_Potassium_spinBox.blockSignals(False)
        self.Plant_Stimulant_Application_comboBox.blockSignals(False)
        self.Plant_Stimulant_Product_Name_lineEdit.blockSignals(False) 
        self.Plant_Stimulant_Date_dateEdit.blockSignals(False)
        self.Plant_Stimulant_DAS_spinBox.blockSignals(False)
        self.Plant_Stimulant_Dose_spinBox.blockSignals(False)
        self.Plant_Protection_Application_comboBox.blockSignals(False)
        self.Plant_Protection_Product_Name_lineEdit.blockSignals(False) 
        self.Plant_Protection_Date_dateEdit.blockSignals(False)
        self.Plant_Protection_DAS_spinBox.blockSignals(False)
        self.Plant_Protection_Dose_spinBox.blockSignals(False)
        
    def update_params(self):
        params.plant_cultivated_variant = self.Plant_Cultivated_Variant_lineEdit.text()
        params.plant_part_name = self.Plant_Part_Name_lineEdit.text()
        
        if self.Plant_Environment_Outside_radioButton.isChecked(): params.plant_environment_outside = 1
        else: params.plant_environment_outside = 0
        if self.Plant_Environment_Inside_radioButton.isChecked(): params.plant_environment_inside = 1
        else: params.plant_environment_inside = 0
        
        if self.Plant_Light_Source_Sun_radioButton.isChecked(): params.plant_light_source_sun = 1
        else: params.plant_light_source_sun = 0
        if self.Plant_Light_Source_Grow_Light_radioButton.isChecked(): params.plant_light_source_grow_light = 1
        else: params.plant_light_source_grow_light = 0
        if self.Plant_Light_Source_Artificial_radioButton.isChecked(): params.plant_light_source_artificial = 1
        else: params.plant_light_source_artificial = 0
        params.plant_light_availability = self.Plant_Light_Availability_spinBox.value()
        
        params.plant_water_availability = self.Plant_Water_Availability_spinBox.value()
        
        params.plant_seed_coating = self.Plant_Seed_Coating_lineEdit.text()
        
        params.plant_nitrogen[params.plant_nutrient_application_index] = self.Plant_Nitrogen_spinBox.value()
        params.plant_phosphorus[params.plant_nutrient_application_index] = self.Plant_Phosphorus_spinBox.value()
        params.plant_potassium[params.plant_nutrient_application_index] = self.Plant_Potassium_spinBox.value()
        
        params.plant_stimulant_product_name[params.plant_stimulant_application_index] = self.Plant_Stimulant_Product_Name_lineEdit.text()
        params.plant_stimulant_dose[params.plant_stimulant_application_index] = self.Plant_Stimulant_Dose_spinBox.value()
        
        params.plant_protection_product_name[params.plant_protection_application_index] = self.Plant_Protection_Product_Name_lineEdit.text()
        params.plant_protection_dose[params.plant_protection_application_index] = self.Plant_Protection_Dose_spinBox.value()
        
        params.saveFileAgriMRIParameter()
        
    def set_Experiment_ID(self):
        params.experiment_ID = self.Experiment_ID_lineEdit.text()
        proc.set_agriMRI_folder_structure()
        
        if os.path.isfile(params.agriMRI_folder_structure + 'AgriMRI_Metadata.json') == True:
            params.load_AgriMRI_Metadata_file_json()
            params.laod_phenological_phases_library()
            self.load_params()
        else:
            print('No .json AgriMRI metadata file!!')
            params.AgriMRI_var_reset()
            self.load_params()
        
        params.saveFileAgriMRIParameter()
        
    def set_Plant_ID(self):
        params.plant_ID = self.Plant_ID_lineEdit.text()
        proc.set_agriMRI_folder_structure()
        if params.experiment_ID == '' or params.experiment_ID == 'Please set ID!': self.Experiment_ID_lineEdit.setText('Please set ID!')
        
        if os.path.isfile(params.agriMRI_folder_structure + 'AgriMRI_Metadata.json') == True:
            params.load_AgriMRI_Metadata_file_json()
            params.laod_phenological_phases_library()
            self.load_params()
        else: print('No .json AgriMRI metadata file!!')
        
        params.saveFileAgriMRIParameter()
        
    def set_Plant_Part_ID(self):
        params.plant_part_ID = self.Plant_Part_ID_lineEdit.text()
        proc.set_agriMRI_folder_structure()
        if params.experiment_ID == '' or params.experiment_ID == 'Please set ID!': self.Experiment_ID_lineEdit.setText('Please set ID!')
        if params.plant_ID == '' or params.plant_ID == 'Please set ID!': self.Plant_ID_lineEdit.setText('Please set ID!')
        
        if os.path.isfile(params.agriMRI_folder_structure + 'AgriMRI_Metadata.json') == True:
            params.load_AgriMRI_Metadata_file_json()
            params.laod_phenological_phases_library()
            self.load_params()
        else: print('No .json AgriMRI metadata file!!')
        
        params.saveFileAgriMRIParameter()
        
    def set_Species(self):
        params.plant_species_index = self.Plant_Species_comboBox.currentIndex()
        params.plant_species = params.plant_species_list[self.Plant_Species_comboBox.currentIndex()]
        params.plant_scientific_name = params.plant_species_library[self.Plant_Species_comboBox.currentIndex()][2]
        params.plant_taxonomy = params.plant_species_library[self.Plant_Species_comboBox.currentIndex()][3]
        params.plant_BBCH_scale = params.plant_species_library[self.Plant_Species_comboBox.currentIndex()][4]
        
        params.laod_phenological_phases_library()
        
        params.plant_phenological_phase_index = 0
        params.plant_phenological_phase = params.plant_phenological_phases_library [0][1]
        
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Phenological_Phase(self):
        params.plant_phenological_phase_index = self.Plant_Phenological_Phase_comboBox.currentIndex()
        params.plant_phenological_phase = params.plant_phenological_phases_library [self.Plant_Phenological_Phase_comboBox.currentIndex()][1]
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def show_Phase_Images(self):
        if params.plant_BBCH_scale == 'Cereals': page_number = 18
        elif params.plant_BBCH_scale == 'Rice': page_number = 23
        elif params.plant_BBCH_scale == 'Maize': page_number = 27
        elif params.plant_BBCH_scale == 'Cucurbits': page_number = 134
        elif params.plant_BBCH_scale == 'Soybean': page_number = 99
        else: page_number = 10
        QDesktopServices.openUrl(QUrl('https://www.openagrar.de/servlets/MCRFileNodeServlet/openagrar_derivate_00010428/BBCH-Skala_en.pdf#page=' + str(page_number)))
        
    def set_Date_Of_Sowing(self):
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_measurement_date = self.Plant_Measurement_Date_dateEdit.date().toPyDate()
        params.plant_measurement_das = (params.plant_measurement_date - params.plant_date_of_sowing).days
        for n in range(10):
            if params.plant_nutrient_date[n] != '':
                params.plant_nutrient_das[n] = (params.plant_nutrient_date[n] - params.plant_date_of_sowing).days
            if params.plant_stimulant_date[n] != '':
                params.plant_stimulant_das[n] = (params.plant_stimulant_date[n] - params.plant_date_of_sowing).days
            if params.plant_protection_date[n] != '':
                params.plant_protection_das[n] = (params.plant_protection_date[n] - params.plant_date_of_sowing).days
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Measurement_Date(self):
        params.plant_measurement_date = self.Plant_Measurement_Date_dateEdit.date().toPyDate()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_measurement_das = (params.plant_measurement_date - params.plant_date_of_sowing).days
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Measurement_Date_Today(self):
        params.plant_measurement_date = datetime.date.today()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_measurement_das = (params.plant_measurement_date - params.plant_date_of_sowing).days
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Measurement_DAS(self):
        params.plant_measurement_das = self.Plant_Measurement_DAS_spinBox.value()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_measurement_date = params.plant_date_of_sowing + datetime.timedelta(days = params.plant_measurement_das)
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Nutrient_Application(self):
        params.plant_nutrient_application_index = self.Plant_Nutrient_Application_comboBox.currentIndex()
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Nutrient_Date(self):
        params.plant_nutrient_date[params.plant_nutrient_application_index] = self.Plant_Nutrient_Date_dateEdit.date().toPyDate()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_nutrient_das[params.plant_nutrient_application_index] = (params.plant_nutrient_date[params.plant_nutrient_application_index] - params.plant_date_of_sowing).days
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Nutrient_DAS(self):
        params.plant_nutrient_das[params.plant_nutrient_application_index] = self.Plant_Nutrient_DAS_spinBox.value()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_nutrient_date[params.plant_nutrient_application_index] = params.plant_date_of_sowing + datetime.timedelta(days = params.plant_nutrient_das[params.plant_nutrient_application_index])
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Stimulant_Application(self):
        params.plant_stimulant_application_index = self.Plant_Stimulant_Application_comboBox.currentIndex()
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Stimulant_Date(self):
        params.plant_stimulant_date[params.plant_stimulant_application_index] = self.Plant_Stimulant_Date_dateEdit.date().toPyDate()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_stimulant_das[params.plant_stimulant_application_index] = (params.plant_stimulant_date[params.plant_stimulant_application_index] - params.plant_date_of_sowing).days
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Stimulant_DAS(self):
        params.plant_stimulant_das[params.plant_stimulant_application_index] = self.Plant_Stimulant_DAS_spinBox.value()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_stimulant_date[params.plant_stimulant_application_index] = params.plant_date_of_sowing + datetime.timedelta(days = params.plant_stimulant_das[params.plant_stimulant_application_index])
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Protection_Application(self):
        params.plant_protection_application_index = self.Plant_Protection_Application_comboBox.currentIndex()
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Protection_Date(self):
        params.plant_protection_date[params.plant_protection_application_index] = self.Plant_Protection_Date_dateEdit.date().toPyDate()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_protection_das[params.plant_protection_application_index] = (params.plant_protection_date[params.plant_protection_application_index] - params.plant_date_of_sowing).days
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Protection_DAS(self):
        params.plant_protection_das[params.plant_protection_application_index] = self.Plant_Protection_DAS_spinBox.value()
        params.plant_date_of_sowing = self.Plant_Date_Of_Sowing_dateEdit.date().toPyDate()
        params.plant_protection_date[params.plant_protection_application_index] = params.plant_date_of_sowing + datetime.timedelta(days = params.plant_protection_das[params.plant_protection_application_index])
        self.load_params()
        params.saveFileAgriMRIParameter()
        
    def set_Experiment_Description(self):
        params.experiment_description = self.Experiment_Description_textEdit.toPlainText()
        params.saveFileAgriMRIParameter()
        
    def set_Plant_Description(self):
        params.plant_description = self.Plant_Description_textEdit.toPlainText()
        params.saveFileAgriMRIParameter()
        

class ToolsWindow(Tools_Window_Form, Tools_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ToolsWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.fig_canvas = None
        self.IMag_canvas = None
        self.IPha_canvas = None
        self.FMB0_canvas = None
        self.FMB1_canvas = None
        
        self.load_params()

        self.ui = loadUi('ui/tools.ui')
        self.setWindowTitle('Tools')
        self.setGeometry(420, 40, 760, 940)
        
        self.Tool_Auto_Sequence_radioButton.toggled.connect(self.update_params)

        self.Autocenter_pushButton.setEnabled(params.connectionmode)
        self.Flipangle_pushButton.setEnabled(params.connectionmode)
        self.Flip_Angle_Check_pushButton.setEnabled(params.connectionmode)
        self.Tool_Shim_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B0_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B0_Slice_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B1_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B1_Slice_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_Gradient_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_Gradient_Slice_pushButton.setEnabled(params.connectionmode)
        self.PB_Marker_Cal_pushButton.setEnabled(params.connectionmode)

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
        self.Flip_Angle_Check_pushButton.clicked.connect(lambda: self.FAchecktool())

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
        
        self.Tool_Auto_Shim_Rough_radioButton.clicked.connect(self.update_auto_shim_rough)
        self.Tool_Auto_Shim_Fine_radioButton.clicked.connect(self.update_auto_shim_fine)
        
        self.Tool_Auto_Shim_pushButton.clicked.connect(lambda: self.Auto_Shimtool())

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
        
        self.PB_Marker_Cal_pushButton.clicked.connect(lambda: self.PB_Marker_Calibration())
        
        self.ErnstAngleCalculator_T1_spinBox.valueChanged.connect(self.update_ernstanglecalc)
        self.ErnstAngleCalculator_TR_spinBox.valueChanged.connect(self.update_ernstanglecalc)
        self.update_ernstanglecalc()
        
        self.label_27.setStyleSheet('font-size: 12px')
        self.label_29.setStyleSheet('font-size: 12px')
        
        self.label_36.setStyleSheet('font-size: 14px')
        
    def load_params(self):
        if params.toolautosequence == 1: self.Tool_Auto_Sequence_radioButton.setChecked(True)
        
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
        
        if params.ToolAutoShimMode == 0: self.Tool_Auto_Shim_Rough_radioButton.setChecked(True)
        if params.ToolAutoShimMode == 1: self.Tool_Auto_Shim_Fine_radioButton.setChecked(True)

        self.GradientScaling_XNominal_doubleSpinBox.setValue(params.gradnominal[0])
        self.GradientScaling_YNominal_doubleSpinBox.setValue(params.gradnominal[1])
        self.GradientScaling_ZNominal_doubleSpinBox.setValue(params.gradnominal[2])

        self.GradientScaling_XMeasured_doubleSpinBox.setValue(params.gradmeasured[0])
        self.GradientScaling_YMeasured_doubleSpinBox.setValue(params.gradmeasured[1])
        self.GradientScaling_ZMeasured_doubleSpinBox.setValue(params.gradmeasured[2])

        self.Gradient_XScaling_lineEdit.setText(str(round(params.gradsenstool[0], 1)))
        self.Gradient_YScaling_lineEdit.setText(str(round(params.gradsenstool[1], 1)))
        self.Gradient_ZScaling_lineEdit.setText(str(round(params.gradsenstool[2], 1)))
        
        self.ErnstAngleCalculator_T1_spinBox.setValue(params.ernstanglecalc_T1)
        self.ErnstAngleCalculator_TR_spinBox.setValue(params.ernstanglecalc_TR)

    def update_params(self):
        if self.Tool_Auto_Sequence_radioButton.isChecked(): params.toolautosequence = 1
        else: params.toolautosequence = 0
        
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

        params.gradsenstool[0] = params.gradmeasured[0] / params.gradnominal[0] * params.gradsens[0]
        params.gradsenstool[1] = params.gradmeasured[1] / params.gradnominal[1] * params.gradsens[1]
        params.gradsenstool[2] = params.gradmeasured[2] / params.gradnominal[2] * params.gradsens[2]

        self.Gradient_XScaling_lineEdit.setText(str(round(params.gradsenstool[0], 1)))
        self.Gradient_YScaling_lineEdit.setText(str(round(params.gradsenstool[1], 1)))
        self.Gradient_ZScaling_lineEdit.setText(str(round(params.gradsenstool[2], 1)))

        params.saveFileParameter()
        
    def update_ernstanglecalc(self):
        params.ernstanglecalc_T1 = self.ErnstAngleCalculator_T1_spinBox.value()
        params.ernstanglecalc_TR = self.ErnstAngleCalculator_TR_spinBox.value()
        
        params.ernstanglecalc_EA = round(math.degrees(np.arccos(math.exp(-(params.ernstanglecalc_TR/params.ernstanglecalc_T1)))))
        self.ErnstAngleCalculator_ErnstAngle_lineEdit.setText(str(params.ernstanglecalc_EA))
        
        params.saveFileParameter()
        
    def update_auto_shim_rough(self):
        if self.Tool_Auto_Shim_Rough_radioButton.isChecked():
            params.ToolAutoShimMode = 0
            self.Tool_Auto_Shim_Fine_radioButton.setChecked(False)
        elif self.Tool_Auto_Shim_Rough_radioButton.isChecked() == False and self.Tool_Auto_Shim_Fine_radioButton.isChecked() == False:
            params.ToolAutoShimMode = 0
            self.Tool_Auto_Shim_Rough_radioButton.setChecked(True)

        params.saveFileParameter()

    def update_auto_shim_fine(self):
        if self.Tool_Auto_Shim_Fine_radioButton.isChecked():
            params.ToolAutoShimMode = 1
            self.Tool_Auto_Shim_Rough_radioButton.setChecked(False)
        elif self.Tool_Auto_Shim_Rough_radioButton.isChecked() == False and self.Tool_Auto_Shim_Fine_radioButton.isChecked() == False:
            params.ToolAutoShimMode = 0
            self.Tool_Auto_Shim_Rough_radioButton.setChecked(True)

        params.saveFileParameter()

    def Autocentertool(self):
        self.Autocenter_pushButton.setEnabled(False)
        self.AC_Reffrequency_lineEdit.setText('')
        self.repaint()
        
        if params.toolautosequence == 1 or params.GUImode == 0:
            self.flippulselength_temp = 0
            self.flippulselength_temp = params.flippulselength
            params.flippulselength = params.RFpulselength

            proc.Autocentertool()
            
            if params.single_plot == 1:
                for attr_name in dir(self):
                    if 'canvas' in attr_name.lower():
                        canvas = getattr(self, attr_name)
                        if canvas != None:
                            plt.close(canvas.figure)
                            canvas.setParent(None)
                            canvas.deleteLater()
                            setattr(self, attr_name, None)

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax = self.fig.add_subplot(111)
            self.ax.plot(np.transpose(params.ACvalues[0, :]), np.transpose(params.ACvalues[1, :]), 'o', color='#000000')
            self.ax.set_xlabel('Frequency [MHz]')
            self.ax.set_ylabel('Signal')
            self.ax.set_title('Autocenter Signals')
            self.major_ticks = np.zeros(6)
            self.major_tickslin = np.linspace(params.ACstart, params.ACstop, num = 5)
            self.major_ticks[0:5] = self.major_tickslin
            self.major_ticks[5] = params.Reffrequency
            if params.ACstop >= params.ACstart: self.minor_ticks = np.arange(params.ACstart, params.ACstop, params.ACstepwidth/1.0e6)
            else: self.minor_ticks = np.arange(params.ACstop, params.ACstart, params.ACstepwidth/1.0e6)
            self.ax.set_xticks(self.major_ticks)
            self.ax.set_xticks(self.minor_ticks, minor=True)
            self.ax.grid(which='major', color='#888888', linestyle='-')
            self.ax.grid(which='minor', color='#888888', linestyle=':')
            self.ax.grid(which='both', visible=True)
            self.ax.set_xlim((params.ACstart, params.ACstop))
            self.ax.set_ylim((0, 1.1 * np.max(np.transpose(params.ACvalues[1, :]))))
            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(420, 40, 1160, 950)
            self.fig_canvas.show()
            
            self.font = self.AC_Reffrequency_lineEdit.font()
            self.font.setPointSize(12)
            self.AC_Reffrequency_lineEdit.setFont(self.font)
            self.AC_Reffrequency_lineEdit.setText(str(params.Reffrequency))

            params.flippulselength = self.flippulselength_temp

            self.Autocenter_pushButton.setEnabled(True)
            self.repaint()
            
        else:
            self.font = self.AC_Reffrequency_lineEdit.font()
            self.font.setPointSize(10)
            self.AC_Reffrequency_lineEdit.setFont(self.font)
            self.AC_Reffrequency_lineEdit.setText('Select spectroscopy!')
            
            self.Autocenter_pushButton.setEnabled(True)
            self.repaint()

    def Flipangletool(self):
        self.Flipangle_pushButton.setEnabled(False)
        self.FA_RefRFattenuation_lineEdit.setText('')
        self.repaint()
        
        if params.toolautosequence == 1 or params.GUImode == 0:
            self.flippulselength_temp = 0
            self.flippulselength_temp = params.flippulselength
            params.flippulselength = params.RFpulselength

            proc.Flipangletool()
            
            if params.single_plot == 1:
                for attr_name in dir(self):
                    if 'canvas' in attr_name.lower():
                        canvas = getattr(self, attr_name)
                        if canvas != None:
                            plt.close(canvas.figure)
                            canvas.setParent(None)
                            canvas.deleteLater()
                            setattr(self, attr_name, None)

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax = self.fig.add_subplot(111)
            self.ax.plot(np.transpose(params.FAvalues[0, :]), np.transpose(params.FAvalues[1, :]), 'o-', color='#000000')
            self.ax.set_xlabel('Attenuation [dB]')
            self.ax.set_ylabel('Signal')
            self.ax.set_title('Flipangle Signals')
            if params.FAstop >= params.FAstart:
                self.major_ticks = np.arange(math.floor(params.FAstart), math.ceil(params.FAstop) + 1, 1)
                self.minor_ticks = np.arange(math.floor(params.FAstart), math.ceil(params.FAstop), 0.25)
                self.ax.set_xlim((math.floor(params.FAstart), math.ceil(params.FAstop)))
            else:
                self.major_ticks = np.arange(math.floor(params.FAstop), math.ceil(params.FAstart) + 1, 1)
                self.minor_ticks = np.arange(math.floor(params.FAstop), math.ceil(params.FAstart), 0.25)
                self.ax.set_xlim((math.floor(params.FAstop), math.ceil(params.FAstart)))
            self.ax.set_xticks(self.major_ticks)
            self.ax.set_xticks(self.minor_ticks, minor=True)
            self.ax.grid(which='major', color='#888888', linestyle='-')
            self.ax.grid(which='minor', color='#888888', linestyle=':')
            self.ax.grid(which='both', visible=True)
            self.ax.set_ylim((0, 1.1 * np.max(np.transpose(params.FAvalues[1, :]))))
            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(420, 40, 1160, 950)
            self.fig_canvas.show()
            
            self.font = self.FA_RefRFattenuation_lineEdit.font()
            self.font.setPointSize(12)
            self.FA_RefRFattenuation_lineEdit.setFont(self.font)
            self.FA_RefRFattenuation_lineEdit.setText(str(params.RefRFattenuation))

            params.flippulselength = self.flippulselength_temp

            self.Flipangle_pushButton.setEnabled(True)
            self.repaint()
            
        else:
            self.font = self.FA_RefRFattenuation_lineEdit.font()
            self.font.setPointSize(10)
            self.FA_RefRFattenuation_lineEdit.setFont(self.font)
            self.FA_RefRFattenuation_lineEdit.setText('Select spectroscopy!')
            
            self.Flipangle_pushButton.setEnabled(True)
            self.repaint()
            
    def FAchecktool(self):
        self.Flip_Angle_Check_pushButton.setEnabled(False)
        self.repaint()
        
        if params.toolautosequence == 1 or params.GUImode == 0:
            self.flippulselength_temp = 0
            self.flippulselength_temp = params.flippulselength
            params.flippulselength = params.RFpulselength

            proc.FAchecktool()
            
            if params.single_plot == 1:
                for attr_name in dir(self):
                    if 'canvas' in attr_name.lower():
                        canvas = getattr(self, attr_name)
                        if canvas != None:
                            plt.close(canvas.figure)
                            canvas.setParent(None)
                            canvas.deleteLater()
                            setattr(self, attr_name, None)

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax = self.fig.add_subplot(111)
            self.FAvalues = np.linspace(0, 180, 19)            
            self.ax.plot(self.FAvalues, np.transpose(params.FAvalues[1, :]), 'o-', color='#000000')
            self.ax.plot([90 , 90], [0, 1.1 * np.max(np.transpose(params.FAvalues[1, :]))], '-', color='#000000')
            self.ax.set_xlabel('Flip angle [°]')
            self.ax.set_ylabel('Signal')
            self.ax.set_title('Flipangle Signals')

            self.ax.set_xticks(self.FAvalues)
            self.ax.grid(which='major', color='#888888', linestyle='-')
            self.ax.grid(which='both', visible=True)
            self.ax.set_xlim((0, 180))
            self.ax.set_ylim((0, 1.1 * np.max(np.transpose(params.FAvalues[1, :]))))

            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(420, 40, 1160, 950)
            self.fig_canvas.show()
            
            params.flippulselength = self.flippulselength_temp

            self.Flip_Angle_Check_pushButton.setEnabled(True)
            self.repaint()
            
        else:
            self.Flip_Angle_Check_pushButton.setEnabled(True)
            self.repaint()

    def Shimtool(self):
        self.Tool_Shim_pushButton.setEnabled(False)
        self.Tool_Shim_X_Ref_lineEdit.setText('')
        self.Tool_Shim_Y_Ref_lineEdit.setText('')
        self.Tool_Shim_Z_Ref_lineEdit.setText('')
        self.Tool_Shim_Z2_Ref_lineEdit.setText('')
        self.repaint()
        
        if params.ToolShimChannel != [0, 0, 0, 0]:
            if params.toolautosequence == 1 or params.GUImode == 0:
                self.frequency_temp = 0
                self.frequency_temp = params.frequency
                params.STgrad[0] = 0

                proc.Shimtool()
                
                params.frequency = self.frequency_temp
                
                if params.single_plot == 1:
                    for attr_name in dir(self):
                        if 'canvas' in attr_name.lower():
                            canvas = getattr(self, attr_name)
                            if canvas != None:
                                plt.close(canvas.figure)
                                canvas.setParent(None)
                                canvas.deleteLater()
                                setattr(self, attr_name, None)

                self.fig = Figure()
                self.fig.set_facecolor('None')
                self.fig_canvas = FigureCanvas(self.fig)

                self.ax = self.fig.add_subplot(111)
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[1, :]), 'o-', color='#0072BD')
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[2, :]), 'o-', color='#D95319')
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[3, :]), 'o-', color='#EDB120')
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[4, :]), 'o-', color='#7E2F8E')
                self.ax.set_xlabel('Shim [mA]')
                self.ax.set_ylabel('Signal')
                self.ax.legend(['X', 'Y', 'Z', 'Z²'])
                self.ax.set_title('Shim Signals')
                
                if params.ToolShimStop >= params.ToolShimStart:
                    if params.ToolShimStop - params.ToolShimStart <= 10:
                        self.major_ticks = np.arange(math.floor(params.ToolShimStart), math.ceil(params.ToolShimStop) + 1, 1)
                        self.ax.set_xlim((math.floor(params.ToolShimStart), math.ceil(params.ToolShimStop)))
                    elif params.ToolShimStop - params.ToolShimStart > 10 and params.ToolShimStop - params.ToolShimStart <= 200:
                        self.major_ticks = np.arange(math.floor(params.ToolShimStart / 10) * 10, math.ceil(params.ToolShimStop / 10) * 10 + 10, 10)
                        self.minor_ticks = np.arange(math.floor(params.ToolShimStart / 10) * 10, math.ceil(params.ToolShimStop / 10) * 10 + 2, 2)
                        self.ax.set_xlim((math.floor(params.ToolShimStart / 10) * 10, math.ceil(params.ToolShimStop / 10) * 10))
                    else:
                        self.major_ticks = np.arange(math.floor(params.ToolShimStart / 50) * 50, math.ceil(params.ToolShimStop / 50) * 50 + 50, 50)
                        self.minor_ticks = np.arange(math.floor(params.ToolShimStart / 50) * 50, math.ceil(params.ToolShimStop / 50) * 50 + 10, 10)
                        self.ax.set_xlim((math.floor(params.ToolShimStart / 50) * 50, math.ceil(params.ToolShimStop / 50) * 50))
                else:
                    if params.ToolShimStart - params.ToolShimStop <= 10:
                        self.major_ticks = np.arange(math.floor(params.ToolShimStop), math.ceil(params.ToolShimStart) + 1, 1)
                        self.ax.set_xlim((math.floor(params.ToolShimStop), math.ceil(params.ToolShimStart)))
                    elif params.ToolShimStart - params.ToolShimStop > 10 and params.ToolShimStart - params.ToolShimStop <= 200:
                        self.major_ticks = np.arange(math.floor(params.ToolShimStop / 10) * 10, math.ceil(params.ToolShimStart / 10) * 10 + 10, 10)
                        self.minor_ticks = np.arange(math.floor(params.ToolShimStop / 10) * 10, math.ceil(params.ToolShimStart / 10) * 10 + 2, 2)
                        self.ax.set_xlim((math.floor(params.ToolShimStop / 10) * 10, math.ceil(params.ToolShimStart / 10) * 10))
                    else:
                        self.major_ticks = np.arange(math.floor(params.ToolShimStop / 50) * 50, math.ceil(params.ToolShimStart / 50) * 50 + 50, 50)
                        self.minor_ticks = np.arange(math.floor(params.ToolShimStorp / 50) * 50, math.ceil(params.ToolShimStart / 50) * 50 + 10, 10)
                        self.ax.set_xlim((math.floor(params.ToolShimStop / 50) * 50, math.ceil(params.ToolShimStart / 50) * 50))

                self.ax.set_xticks(self.major_ticks)
                self.ax.set_xticks(self.minor_ticks, minor=True)
                self.ax.grid(which='major', color='#888888', linestyle='-')
                self.ax.grid(which='minor', color='#888888', linestyle=':')
                self.ax.grid(which='both', visible=True)
                self.ax.set_ylim((0, 1.1 * np.max(np.transpose(params.STvalues[1:, :]))))
                self.fig_canvas.draw()
                self.fig_canvas.setWindowTitle('Tool Plot')
                self.fig_canvas.setGeometry(420, 40, 1160, 950)
                self.fig_canvas.show()
                
                self.font = self.Tool_Shim_X_Ref_lineEdit.font()
                self.font.setPointSize(12)
                self.Tool_Shim_X_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Y_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z2_Ref_lineEdit.setFont(self.font)
                
                if params.ToolShimChannel[0] == 1:
                    params.STgrad[1] = params.STvalues[0, np.argmax(params.STvalues[1, :])]
                    self.Tool_Shim_X_Ref_lineEdit.setText(str(params.STgrad[1]))
                else: self.Tool_Shim_X_Ref_lineEdit.setText('')
                if params.ToolShimChannel[1] == 1:
                    params.STgrad[2] = params.STvalues[0, np.argmax(params.STvalues[2, :])]
                    self.Tool_Shim_Y_Ref_lineEdit.setText(str(params.STgrad[2]))
                else: self.Tool_Shim_Y_Ref_lineEdit.setText('')
                if params.ToolShimChannel[2] == 1:
                    params.STgrad[3] = params.STvalues[0, np.argmax(params.STvalues[3, :])]
                    self.Tool_Shim_Z_Ref_lineEdit.setText(str(params.STgrad[3]))
                else: self.Tool_Shim_Z_Ref_lineEdit.setText('')
                if params.ToolShimChannel[3] == 1:
                    params.STgrad[4] = params.STvalues[0, np.argmax(params.STvalues[4, :])]
                    self.Tool_Shim_Z2_Ref_lineEdit.setText(str(params.STgrad[4]))
                else: self.Tool_Shim_Z2_Ref_lineEdit.setText('')
                
                params.STgrad[0] = 1
                
                np.savetxt('data/Tool_data/Shim_data.txt', params.STvalues)

            else:
                self.font = self.Tool_Shim_X_Ref_lineEdit.font()
                self.font.setPointSize(10)
                self.Tool_Shim_X_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Y_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z2_Ref_lineEdit.setFont(self.font)
                if params.ToolShimChannel[0] == 1: self.Tool_Shim_X_Ref_lineEdit.setText('Select spectroscopy!')
                if params.ToolShimChannel[1] == 1: self.Tool_Shim_Y_Ref_lineEdit.setText('Select spectroscopy!')
                if params.ToolShimChannel[2] == 1: self.Tool_Shim_Z_Ref_lineEdit.setText('Select spectroscopy!')
                if params.ToolShimChannel[3] == 1: self.Tool_Shim_Z2_Ref_lineEdit.setText('Select spectroscopy!')
            
        else:
            self.font = self.Tool_Shim_X_Ref_lineEdit.font()
            self.font.setPointSize(10)
            self.Tool_Shim_X_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_Y_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_Z_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_Z2_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_X_Ref_lineEdit.setText('Select shim channel!')
            self.Tool_Shim_Y_Ref_lineEdit.setText('Select shim channel!')
            self.Tool_Shim_Z_Ref_lineEdit.setText('Select shim channel!')
            self.Tool_Shim_Z2_Ref_lineEdit.setText('Select shim channel!')

        self.Tool_Shim_pushButton.setEnabled(True)
        self.repaint()
        
    def Auto_Shimtool(self):
        self.Tool_Auto_Shim_pushButton.setEnabled(False)
        self.Tool_Shim_X_Ref_lineEdit.setText('')
        self.Tool_Shim_Y_Ref_lineEdit.setText('')
        self.Tool_Shim_Z_Ref_lineEdit.setText('')
        self.Tool_Shim_Z2_Ref_lineEdit.setText('')
        self.repaint()
        
        if params.toolautosequence == 1 or params.GUImode == 0:
            self.frequency_temp = 0
            self.frequency_temp = params.frequency
            self.grad_temp = [0, 0, 0, 0]
            self.grad_temp[:] = params.grad[:]
            self.ToolShimStart_temp = 0
            self.ToolShimStart_temp = params.ToolShimStart
            self.ToolShimStop_temp = 0
            self.ToolShimStop_temp = params.ToolShimStop
            self.ToolShimSteps_temp = 0
            self.ToolShimSteps_temp = params.ToolShimSteps
            
            params.STgrad[0] = 0
            
            if params.ToolAutoShimMode == 1:
                print('Auto shim fine...')
            
                params.ToolShimSteps = 40
                params.AutoSTvalues = np.matrix(np.zeros((8, params.ToolShimSteps)))
        
                params.ToolShimChannel = [1, 0, 0, 0]
                params.ToolShimStart = int(self.grad_temp[0] - 60)
                params.ToolShimStop = int(self.grad_temp[0] + 60)
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[0, :] = params.STvalues[0, :]
                params.AutoSTvalues[1, :] = params.STvalues[1, :]
                params.STgrad[1] = int(params.STvalues[0, np.argmax(params.STvalues[1, :])])
                params.grad[0] = params.STgrad[1]
                
                params.frequency = self.frequency_temp
                params.ToolShimStart = int(self.grad_temp[1] - 60)
                params.ToolShimStop = int(self.grad_temp[1] + 60)
                params.ToolShimChannel = [0, 1, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[2, :] = params.STvalues[0, :]
                params.AutoSTvalues[3, :] = params.STvalues[2, :]
                params.STgrad[2] = int(params.STvalues[0, np.argmax(params.STvalues[2, :])])
                params.grad[1] = params.STgrad[2]
                
                params.frequency = self.frequency_temp
                params.ToolShimStart = int(self.grad_temp[2] - 60)
                params.ToolShimStop = int(self.grad_temp[2] + 60)
                params.ToolShimChannel = [0, 0, 1, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[4, :] = params.STvalues[0, :]
                params.AutoSTvalues[5, :] = params.STvalues[3, :]
                params.STgrad[3] = int(params.STvalues[0, np.argmax(params.STvalues[3, :])])
                params.grad[2] = params.STgrad[3]
                
                params.frequency = self.frequency_temp
                params.ToolShimStart = int(self.grad_temp[3] - 60)
                params.ToolShimStop = int(self.grad_temp[3] + 60)
                params.ToolShimChannel = [0, 0, 0, 1]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[6, :] = params.STvalues[0, :]
                params.AutoSTvalues[7, :] = params.STvalues[4, :]
                params.STgrad[4] = int(params.STvalues[0, np.argmax(params.STvalues[4, :])])
                params.grad[3] = params.STgrad[4]
                
                params.frequency = self.frequency_temp
                params.saveFileParameter()
                
                self.font = self.Tool_Shim_X_Ref_lineEdit.font()
                self.font.setPointSize(12)
                self.Tool_Shim_X_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Y_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z2_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_X_Ref_lineEdit.setText(str(params.STgrad[1]))
                self.Tool_Shim_Y_Ref_lineEdit.setText(str(params.STgrad[2]))
                self.Tool_Shim_Z_Ref_lineEdit.setText(str(params.STgrad[3]))
                self.Tool_Shim_Z2_Ref_lineEdit.setText(str(params.STgrad[4]))
                
                params.STgrad[0] = 2
                
            else:
                print('Auto shim rough...')
                
                params.grad = [0, 0, 0, 0]
                params.ToolShimStart = -400
                params.ToolShimStop = 400
                params.ToolShimSteps = 20
                params.AutoSTvalues = np.matrix(np.zeros((8, params.ToolShimSteps)))
        
                params.ToolShimChannel = [1, 0, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[0, :] = params.STvalues[0, :]
                params.AutoSTvalues[1, :] = params.STvalues[1, :]
                params.STgrad[1] = int(params.STvalues[0, np.argmax(params.STvalues[1, :])])
                params.grad[0] = params.STgrad[1]
                
                params.frequency = params.STvalues[5, np.argmax(params.STvalues[1, :])]
                params.ToolShimChannel = [0, 1, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[2, :] = params.STvalues[0, :]
                params.AutoSTvalues[3, :] = params.STvalues[2, :]
                params.STgrad[2] = int(params.STvalues[0, np.argmax(params.STvalues[2, :])])
                params.grad[1] = params.STgrad[2]
                
                params.frequency = params.STvalues[6, np.argmax(params.STvalues[2, :])]
                params.ToolShimChannel = [0, 0, 1, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[4, :] = params.STvalues[0, :]
                params.AutoSTvalues[5, :] = params.STvalues[3, :]
                params.STgrad[3] = int(params.STvalues[0, np.argmax(params.STvalues[3, :])])
                params.grad[2] = params.STgrad[3]
                
                params.frequency = params.STvalues[7, np.argmax(params.STvalues[3, :])]
                params.ToolShimChannel = [0, 0, 0, 1]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[6, :] = params.STvalues[0, :]
                params.AutoSTvalues[7, :] = params.STvalues[4, :]
                params.STgrad[4] = int(params.STvalues[0, np.argmax(params.STvalues[4, :])])
                params.grad[3] = params.STgrad[4]
                
                params.frequency = params.STvalues[8, np.argmax(params.STvalues[4, :])]
                params.ToolShimChannel = [1, 0, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[0, :] = params.STvalues[0, :]
                params.AutoSTvalues[1, :] = params.STvalues[1, :]
                params.STgrad[1] = int(params.STvalues[0, np.argmax(params.STvalues[1, :])])
                params.grad[0] = params.STgrad[1]
                
                params.frequency = params.STvalues[5, np.argmax(params.STvalues[1, :])]
                params.ToolShimChannel = [0, 1, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[2, :] = params.STvalues[0, :]
                params.AutoSTvalues[3, :] = params.STvalues[2, :]
                params.STgrad[2] = int(params.STvalues[0, np.argmax(params.STvalues[2, :])])
                print(params.STgrad[2])
                params.grad[1] = params.STgrad[2]
                
                params.frequency = params.STvalues[6, np.argmax(params.STvalues[2, :])]
                params.ToolShimChannel = [0, 0, 1, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[4, :] = params.STvalues[0, :]
                params.AutoSTvalues[5, :] = params.STvalues[3, :]
                params.STgrad[3] = int(params.STvalues[0, np.argmax(params.STvalues[3, :])])
                params.grad[2] = params.STgrad[3]
                
                params.frequency = params.STvalues[7, np.argmax(params.STvalues[3, :])]
                params.ToolShimChannel = [0, 0, 0, 1]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[6, :] = params.STvalues[0, :]
                params.AutoSTvalues[7, :] = params.STvalues[4, :]
                params.STgrad[4] = int(params.STvalues[0, np.argmax(params.STvalues[4, :])])
                print(params.STgrad[4])
                params.grad[3] = params.STgrad[4]
                
                params.frequency = self.frequency_temp
                params.saveFileParameter()
                
                self.font = self.Tool_Shim_X_Ref_lineEdit.font()
                self.font.setPointSize(12)
                self.Tool_Shim_X_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Y_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_Z2_Ref_lineEdit.setFont(self.font)
                self.Tool_Shim_X_Ref_lineEdit.setText(str(params.STgrad[1]))
                self.Tool_Shim_Y_Ref_lineEdit.setText(str(params.STgrad[2]))
                self.Tool_Shim_Z_Ref_lineEdit.setText(str(params.STgrad[3]))
                self.Tool_Shim_Z2_Ref_lineEdit.setText(str(params.STgrad[4]))
                
                params.STgrad[0] = 2
                
            params.grad = self.grad_temp
            params.ToolShimStart = self.ToolShimStart_temp
            params.ToolShimStop = self.ToolShimStop_temp
            params.ToolShimSteps = self.ToolShimSteps_temp
            
            params.saveFileParameter()
                        
            np.savetxt('data/Tool_data/Auto_Shim_data.txt', np.transpose(params.AutoSTvalues))
            
            if params.single_plot == 1:
                for attr_name in dir(self):
                    if 'canvas' in attr_name.lower():
                        canvas = getattr(self, attr_name)
                        if canvas != None:
                            plt.close(canvas.figure)
                            canvas.setParent(None)
                            canvas.deleteLater()
                            setattr(self, attr_name, None)

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax = self.fig.add_subplot(111)
            self.ax.plot(np.transpose(params.AutoSTvalues[0, :]), np.transpose(params.AutoSTvalues[1, :]), 'o-', color='#0072BD')
            self.ax.plot(np.transpose(params.AutoSTvalues[2, :]), np.transpose(params.AutoSTvalues[3, :]), 'o-', color='#D95319')
            self.ax.plot(np.transpose(params.AutoSTvalues[4, :]), np.transpose(params.AutoSTvalues[5, :]), 'o-', color='#EDB120')
            self.ax.plot(np.transpose(params.AutoSTvalues[6, :]), np.transpose(params.AutoSTvalues[7, :]), 'o-', color='#7E2F8E')
            self.ax.set_xlabel('Shim [mA]')
            self.ax.set_ylabel('Signal')
            self.ax.legend(['X', 'Y', 'Z', 'Z²'])
            self.ax.set_title('Shim Signals')
            
            if params.ToolAutoShimMode == 1: 
                if (np.max(params.grad)+60) - (np.min(params.grad)-60) <= 10:
                    self.major_ticks = np.arange(math.floor((np.min(params.grad)-60)), math.ceil((np.max(params.grad)+60)) + 1, 1)
                    self.ax.set_xlim((math.floor((np.min(params.grad)-60)), math.ceil((np.max(params.grad)+60))))
                elif (np.max(params.grad)+60) - (np.min(params.grad)-60) > 10 and (np.max(params.grad)+60) - (np.min(params.grad)-60) <= 200:
                    self.major_ticks = np.arange(math.floor((np.min(params.grad)-60) / 10) * 10, math.ceil((np.max(params.grad)+60) / 10) * 10 + 10, 10)
                    self.minor_ticks = np.arange(math.floor((np.min(params.grad)-60) / 10) * 10, math.ceil((np.max(params.grad)+60) / 10) * 10 + 2, 2)
                    self.ax.set_xlim((math.floor((np.min(params.grad)-60) / 10) * 10, math.ceil((np.max(params.grad)+60) / 10) * 10))
                else:
                    self.major_ticks = np.arange(math.floor((np.min(params.grad)-60) / 50) * 50, math.ceil((np.max(params.grad)+60) / 50) * 50 + 50, 50)
                    self.minor_ticks = np.arange(math.floor((np.min(params.grad)-60) / 50) * 50, math.ceil((np.max(params.grad)+60) / 50) * 50 + 10, 10)
                    self.ax.set_xlim((math.floor((np.min(params.grad)-60) / 50) * 50, math.ceil((np.max(params.grad)+60) / 50) * 50))
            else:
                self.major_ticks = np.arange(-400, 450, 50)
                self.minor_ticks = np.arange(-400, 410, 10)
                self.ax.set_xlim((-400, 400))
            
            self.ax.set_xticks(self.major_ticks)
            self.ax.set_xticks(self.minor_ticks, minor=True)
            self.ax.grid(which='major', color='#888888', linestyle='-')
            self.ax.grid(which='minor', color='#888888', linestyle=':')
            self.ax.grid(which='both', visible=True)
            self.AutoSTvaluesmax = np.zeros((4))
            self.AutoSTvaluesmax[0] = np.max(np.transpose(params.AutoSTvalues[1, :]))
            self.AutoSTvaluesmax[1] = np.max(np.transpose(params.AutoSTvalues[3, :]))
            self.AutoSTvaluesmax[2] = np.max(np.transpose(params.AutoSTvalues[5, :]))
            self.AutoSTvaluesmax[3] = np.max(np.transpose(params.AutoSTvalues[7, :]))
            self.ax.set_ylim((0, 1.1 * np.max(self.AutoSTvaluesmax)))
            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(420, 40, 1160, 950)
            self.fig_canvas.show()
            
        else:
            self.font = self.Tool_Shim_X_Ref_lineEdit.font()
            self.font.setPointSize(10)
            self.Tool_Shim_X_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_Y_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_Z_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_Z2_Ref_lineEdit.setFont(self.font)
            self.Tool_Shim_X_Ref_lineEdit.setText('Select spectroscopy!')
            self.Tool_Shim_Y_Ref_lineEdit.setText('Select spectroscopy!')
            self.Tool_Shim_Z_Ref_lineEdit.setText('Select spectroscopy!')
            self.Tool_Shim_Z2_Ref_lineEdit.setText('Select spectroscopy!')
            
        self.Tool_Auto_Shim_pushButton.setEnabled(True)
        self.repaint()
        
        params.ToolShimChannel = [1, 1, 1, 1]
        params.saveFileParameter()
        
        self.Tool_Shim_X_radioButton.setChecked(True)
        self.Tool_Shim_Y_radioButton.setChecked(True)
        self.Tool_Shim_Z_radioButton.setChecked(True)
        self.Tool_Shim_Z2_radioButton.setChecked(True)

    def Field_Map_B0(self):
        self.Field_Map_B0_pushButton.setEnabled(False)
        self.repaint()

        print('\033[1m' + 'WIP Field_Map_B0' + '\033[0m')

        proc.FieldMapB0()
        
        if params.single_plot == 1:
            for attr_name in dir(self):
                if 'canvas' in attr_name.lower():
                    canvas = getattr(self, attr_name)
                    if canvas != None:
                        plt.close(canvas.figure)
                        canvas.setParent(None)
                        canvas.deleteLater()
                        setattr(self, attr_name, None)

        self.IPha_fig = Figure()
        self.IPha_canvas = FigureCanvas(self.IPha_fig)
        self.IPha_fig.set_facecolor('None')
        self.IPha_ax = self.IPha_fig.add_subplot(111)
        self.IPha_ax.grid(False)
        self.IPha_ax.imshow(params.img_pha, cmap='gray')
        self.IPha_ax.axis('off')
        self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
        self.IPha_ax.set_title('Phase Image')
        self.IPha_canvas.draw()
        self.IPha_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IPha_canvas.setGeometry(420, 40, 575, 455)
        self.IPha_canvas.show()

        self.FMB0_fig = Figure()
        self.FMB0_canvas = FigureCanvas(self.FMB0_fig)
        self.FMB0_fig.set_facecolor('None')
        self.FMB0_ax = self.FMB0_fig.add_subplot(111)
        self.FMB0_ax.grid(False)
        self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet')
        self.FMB0_ax.axis('off')
        self.FMB0_ax.set_aspect(1.0 / self.FMB0_ax.get_data_ratio())
        self.FMB0_ax.set_title('\u0394 B0 Map')
        self.FMB0_fig_cbar = self.FMB0_fig.colorbar(self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet'))
        self.FMB0_fig_cbar.set_label('\u0394 B0 in µT', rotation=90)
        self.FMB0_canvas.draw()
        self.FMB0_canvas.setWindowTitle('Tool Plot')
        self.FMB0_canvas.setGeometry(1005, 40, 575, 455)
        self.FMB0_canvas.show()

        self.Field_Map_B0_pushButton.setEnabled(True)
        self.repaint()

    def Field_Map_B0_Slice(self):
        self.Field_Map_B0_Slice_pushButton.setEnabled(False)
        self.repaint()

        print('\033[1m' + 'WIP Field_Map_B0_Slice' + '\033[0m')

        proc.FieldMapB0Slice()
        
        if params.single_plot == 1:
            for attr_name in dir(self):
                if 'canvas' in attr_name.lower():
                    canvas = getattr(self, attr_name)
                    if canvas != None:
                        plt.close(canvas.figure)
                        canvas.setParent(None)
                        canvas.deleteLater()
                        setattr(self, attr_name, None)

        self.IPha_fig = Figure()
        self.IPha_canvas = FigureCanvas(self.IPha_fig)
        self.IPha_fig.set_facecolor('None')
        self.IPha_ax = self.IPha_fig.add_subplot(111)
        self.IPha_ax.grid(False)
        self.IPha_ax.imshow(params.img_pha, cmap='gray')
        self.IPha_ax.axis('off')
        self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
        self.IPha_ax.set_title('Phase Image')
        self.IPha_canvas.draw()
        self.IPha_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IPha_canvas.setGeometry(420, 40, 575, 455)
        self.IPha_canvas.show()

        self.FMB0_fig = Figure()
        self.FMB0_canvas = FigureCanvas(self.FMB0_fig)
        self.FMB0_fig.set_facecolor('None')
        self.FMB0_ax = self.FMB0_fig.add_subplot(111)
        self.FMB0_ax.grid(False)
        self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet')
        self.FMB0_ax.axis('off')
        self.FMB0_ax.set_aspect(1.0 / self.FMB0_ax.get_data_ratio())
        self.FMB0_ax.set_title('\u0394 B0 Map')
        self.FMB0_fig_cbar = self.FMB0_fig.colorbar(self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet'))
        self.FMB0_fig_cbar.set_label('\u0394 B0 in uT', rotation=90)
        self.FMB0_canvas.draw()
        self.FMB0_canvas.setWindowTitle('Tool Plot')
        self.FMB0_canvas.setGeometry(1005, 40, 575, 455)
        self.FMB0_canvas.show()

        self.Field_Map_B0_Slice_pushButton.setEnabled(True)
        self.repaint()

    def Field_Map_B1(self):
        self.Field_Map_B1_pushButton.setEnabled(False)
        self.repaint()

        print('\033[1m' + 'WIP Field_Map_B1' + '\033[0m')

        proc.FieldMapB1()
        
        if params.single_plot == 1:
            for attr_name in dir(self):
                if 'canvas' in attr_name.lower():
                    canvas = getattr(self, attr_name)
                    if canvas != None:
                        plt.close(canvas.figure)
                        canvas.setParent(None)
                        canvas.deleteLater()
                        setattr(self, attr_name, None)

        self.IMag_fig = Figure()
        self.IMag_canvas = FigureCanvas(self.IMag_fig)
        self.IMag_fig.set_facecolor('None')
        self.IMag_ax = self.IMag_fig.add_subplot(111)
        self.IMag_ax.grid(False)
        if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap)
        else: self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap)
        self.IMag_ax.axis('off')
        self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
        self.IMag_ax.set_title('Magnitude Image')
        self.IMag_canvas.draw()
        self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IMag_canvas.setGeometry(420, 40, 575, 455)
        self.IMag_canvas.show()

        self.FMB1_fig = Figure()
        self.FMB1_canvas = FigureCanvas(self.FMB1_fig)
        self.FMB1_fig.set_facecolor('None');
        self.FMB1_ax = self.FMB1_fig.add_subplot(111)
        self.FMB1_ax.grid(False)
        self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet')
        self.FMB1_ax.axis('off')
        self.FMB1_ax.set_aspect(1.0 / self.FMB1_ax.get_data_ratio())
        self.FMB1_ax.set_title('Flip Angle Map')
        self.FMB1_fig_cbar = self.FMB1_fig.colorbar(self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet'))
        self.FMB1_fig_cbar.set_label('\u03B1 in deg', rotation=90)
        self.FMB1_canvas.draw()
        self.FMB1_canvas.setWindowTitle('Tool Plot')
        self.FMB1_canvas.setGeometry(1005, 40, 575, 455)
        self.FMB1_canvas.show()

        self.Field_Map_B1_pushButton.setEnabled(True)
        self.repaint()

    def Field_Map_B1_Slice(self):
        self.Field_Map_B1_Slice_pushButton.setEnabled(False)
        self.repaint()

        print('\033[1m' + 'WIP Field_Map_B1_Slice' + '\033[0m')

        proc.FieldMapB1Slice()
        
        if params.single_plot == 1:
            for attr_name in dir(self):
                if 'canvas' in attr_name.lower():
                    canvas = getattr(self, attr_name)
                    if canvas != None:
                        plt.close(canvas.figure)
                        canvas.setParent(None)
                        canvas.deleteLater()
                        setattr(self, attr_name, None)

        self.IMag_fig = Figure()
        self.IMag_canvas = FigureCanvas(self.IMag_fig)
        self.IMag_fig.set_facecolor('None')
        self.IMag_ax = self.IMag_fig.add_subplot(111)
        self.IMag_ax.grid(False)
        if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap)
        else: self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap)
        self.IMag_ax.axis('off')
        self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
        self.IMag_ax.set_title('Magnitude Image')
        self.IMag_canvas.draw()
        self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IMag_canvas.setGeometry(420, 40, 575, 455)
        self.IMag_canvas.show()

        self.FMB1_fig = Figure()
        self.FMB1_canvas = FigureCanvas(self.FMB1_fig)
        self.FMB1_fig.set_facecolor('None')
        self.FMB1_ax = self.FMB1_fig.add_subplot(111)
        self.FMB1_ax.grid(False)
        self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet')
        self.FMB1_ax.axis('off')
        self.FMB1_ax.set_aspect(1.0 / self.FMB1_ax.get_data_ratio())
        self.FMB1_ax.set_title('Flip Angle Map')
        self.FMB1_fig_cbar = self.FMB1_fig.colorbar(self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet'))
        self.FMB1_fig_cbar.set_label('\u03B1 in deg', rotation=90)
        self.FMB1_canvas.draw()
        self.FMB1_canvas.setWindowTitle('Tool Plot')
        self.FMB1_canvas.setGeometry(1005, 40, 575, 455)
        self.FMB1_canvas.show()

        self.Field_Map_B1_Slice_pushButton.setEnabled(True)
        self.repaint()

    def Field_Map_Gradient(self):
        self.Field_Map_Gradient_pushButton.setEnabled(False)
        self.repaint()

        proc.FieldMapGradient()
        
        if params.toolautosequence == 1:
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
        
        if params.single_plot == 1:
            for attr_name in dir(self):
                if 'canvas' in attr_name.lower():
                    canvas = getattr(self, attr_name)
                    if canvas != None:
                        plt.close(canvas.figure)
                        canvas.setParent(None)
                        canvas.deleteLater()
                        setattr(self, attr_name, None)

        self.IMag_fig = Figure()
        self.IMag_canvas = FigureCanvas(self.IMag_fig)
        self.IMag_fig.set_facecolor('None')
        self.IMag_ax = self.IMag_fig.add_subplot(111)
        if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
        else: self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
        self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
        self.IMag_ax.set_title('Magnitude Image')
        self.major_ticks = np.linspace(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)), math.floor((params.FOV / 2)) - math.ceil((-params.FOV / 2)) + 1)
        self.minor_ticks = np.linspace((math.ceil((-params.FOV / 2) * 5)) / 5, (math.floor((params.FOV / 2) * 5)) / 5, math.floor((params.FOV / 2) * 5) - math.ceil((-params.FOV / 2) * 5) + 1)
        self.IMag_ax.set_xticks(self.major_ticks)
        self.IMag_ax.set_xticks(self.minor_ticks, minor=True)
        self.IMag_ax.set_yticks(self.major_ticks)
        self.IMag_ax.set_yticks(self.minor_ticks, minor=True)
        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
        self.IMag_ax.grid(which='minor', color='#CCCCCC', linestyle=':')
        self.IMag_ax.grid(which='both', visible=True)

        if params.imageorientation == 0:
            self.IMag_ax.set_xlabel('X in mm')
            self.IMag_ax.set_ylabel('Y in mm')
        elif params.imageorientation == 1:
            self.IMag_ax.set_xlabel('Y in mm')
            self.IMag_ax.set_ylabel('Z in mm')
        elif params.imageorientation == 2:
            self.IMag_ax.set_xlabel('Z in mm')
            self.IMag_ax.set_ylabel('X in mm')
        elif params.imageorientation == 3:
            self.IMag_ax.set_xlabel('Y in mm')
            self.IMag_ax.set_ylabel('Z in mm')
        elif params.imageorientation == 4:
            self.IMag_ax.set_xlabel('Z in mm')
            self.IMag_ax.set_ylabel('Y in mm')
        elif params.imageorientation == 5:
            self.IMag_ax.set_xlabel('X in mm')
            self.IMag_ax.set_ylabel('Z in mm')

        self.IMag_canvas.draw()
        self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IMag_canvas.setGeometry(420, 40, 1160, 950)
        self.IMag_canvas.show()
        
        if params.toolautosequence == 1:
            params.FOV = self.FOV_temp

        self.Field_Map_Gradient_pushButton.setEnabled(True)
        self.repaint()

    def Field_Map_Gradient_Slice(self):
        self.Field_Map_Gradient_Slice_pushButton.setEnabled(False)
        self.repaint()

        proc.FieldMapGradientSlice()
        
        if params.toolautosequence == 1:
            self.FOV_temp = 0
            self.FOV_temp = params.FOV
            
            if params.imageorientation == 2 or params.imageorientation == 5:
                if params.motor_enable == 0: params.FOV = 12
                else: params.FOV = 16
            else:
                if params.motor_enable == 0: params.FOV = 16
                else: params.FOV = 18
        
        if params.single_plot == 1:
            for attr_name in dir(self):
                if 'canvas' in attr_name.lower():
                    canvas = getattr(self, attr_name)
                    if canvas != None:
                        plt.close(canvas.figure)
                        canvas.setParent(None)
                        canvas.deleteLater()
                        setattr(self, attr_name, None)
                        
        self.IMag_fig = Figure()
        self.IMag_canvas = FigureCanvas(self.IMag_fig)
        self.IMag_fig.set_facecolor('None')
        self.IMag_ax = self.IMag_fig.add_subplot(111)
        if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
        else: self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
        self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
        self.IMag_ax.set_title('Magnitude Image')
        self.major_ticks = np.linspace(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)), math.floor((params.FOV / 2)) - math.ceil((-params.FOV / 2)) + 1)
        self.minor_ticks = np.linspace((math.ceil((-params.FOV / 2) * 5)) / 5, (math.floor((params.FOV / 2) * 5)) / 5, math.floor((params.FOV / 2) * 5) - math.ceil((-params.FOV / 2) * 5) + 1)
        self.IMag_ax.set_xticks(self.major_ticks)
        self.IMag_ax.set_xticks(self.minor_ticks, minor=True)
        self.IMag_ax.set_yticks(self.major_ticks)
        self.IMag_ax.set_yticks(self.minor_ticks, minor=True)
        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
        self.IMag_ax.grid(which='minor', color='#CCCCCC', linestyle=':')
        self.IMag_ax.grid(which='both', visible=True)

        if params.imageorientation == 0:
            self.IMag_ax.set_xlabel('X in mm')
            self.IMag_ax.set_ylabel('Y in mm')
        elif params.imageorientation == 1:
            self.IMag_ax.set_xlabel('Y in mm')
            self.IMag_ax.set_ylabel('Z in mm')
        elif params.imageorientation == 2:
            self.IMag_ax.set_xlabel('Z in mm')
            self.IMag_ax.set_ylabel('X in mm')
        elif params.imageorientation == 3:
            self.IMag_ax.set_xlabel('Y in mm')
            self.IMag_ax.set_ylabel('X in mm')
        elif params.imageorientation == 4:
            self.IMag_ax.set_xlabel('Z in mm')
            self.IMag_ax.set_ylabel('Y in mm')
        elif params.imageorientation == 5:
            self.IMag_ax.set_xlabel('X in mm')
            self.IMag_ax.set_ylabel('Z in mm')

        self.IMag_canvas.draw()
        self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IMag_canvas.setGeometry(420, 40, 1160, 950)
        self.IMag_canvas.show()
        
        if params.toolautosequence == 1:
            params.FOV = self.FOV_temp

        self.Field_Map_Gradient_Slice_pushButton.setEnabled(True)
        self.repaint()
        
    def PB_Marker_Calibration(self):
        self.PB_Marker_Cal_pushButton.setEnabled(False)
        self.repaint()
        
        if params.toolautosequence == 1 or params.GUImode == 4:
        
            proc.PBMarkerCalProjection()
            
            if params.toolautosequence == 1:
                self.nPE_temp = 0
                self.nPE_temp = params.nPE
                self.FOV_temp = 0
                self.FOV_temp = params.FOV

                params.nPE = 128
                params.FOV = 22
                
            self.freqencyaxis = np.linspace(-params.FOV/2,params.FOV/2,num=params.nPE)
                
            self.spectrumfft_center = int(params.spectrumfft.shape[0] / 2)
            
            self.spectrumfft = []
            self.spectrumfft = params.spectrumfft[self.spectrumfft_center - int(params.nPE / 2 * params.ROBWscaler):self.spectrumfft_center + int(params.nPE / 2 * params.ROBWscaler)]

            if params.single_plot == 1:
                for attr_name in dir(self):
                    if 'canvas' in attr_name.lower():
                        canvas = getattr(self, attr_name)
                        if canvas != None:
                            plt.close(canvas.figure)
                            canvas.setParent(None)
                            canvas.deleteLater()
                            setattr(self, attr_name, None)

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax1 = self.fig.add_subplot(1, 1, 1)

            self.ax1.plot(self.freqencyaxis, self.spectrumfft)
            self.ax1.plot([0, 0], [0, 1.1 * np.max(self.spectrumfft)], color='#000000',linewidth=2)
            self.ax1.plot(self.freqencyaxis, self.spectrumfft, color='#000000')
            self.ax1.set_xlim([-params.FOV / 2, params.FOV / 2])
            self.ax1.set_ylim([0, 1.1 * np.max(self.spectrumfft)])
            self.ax1.set_title('Y - Projection')
            self.ax1.set_ylabel('RX Signal [arb.]')
            self.ax1.set_xlabel('Y in mm')
            self.major_ticks = np.arange(-params.FOV / 2, params.FOV / 2 + 1, 1)
            self.minor_ticks = np.arange(-params.FOV / 2, params.FOV / 2 + 0.2, 0.2)
            self.ax1.set_xticks(self.major_ticks)
            self.ax1.set_xticks(self.minor_ticks, minor=True)
            self.ax1.grid(which='major', color='#888888', linestyle='-')
            self.ax1.grid(which='minor', color='#888888', linestyle=':')
            self.ax1.grid(which='both', visible=True)
            self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.fig_canvas.setGeometry(420, 40, 1160, 950)
            self.fig_canvas.show()
            
            params.Ref_PB_marker_isocenter_distance = np.round(params.PB_marker_isocenter_distance - self.freqencyaxis[np.argmax(self.spectrumfft)],1)
            
            self.font = self.PB_Marker_Cal_MIC_Dist_lineEdit.font()
            self.font.setPointSize(12)
            self.PB_Marker_Cal_MIC_Dist_lineEdit.setFont(self.font)
            self.PB_Marker_Cal_MIC_Dist_lineEdit.setText(str(params.Ref_PB_marker_isocenter_distance))
            
            if params.toolautosequence == 1:
                params.nPE = self.nPE_temp
                params.FOV = self.FOV_temp
                
        else:
            self.font = self.PB_Marker_Cal_MIC_Dist_lineEdit.font()
            self.font.setPointSize(10)
            self.PB_Marker_Cal_MIC_Dist_lineEdit.setFont(self.font)
            self.PB_Marker_Cal_MIC_Dist_lineEdit.setText('Select projections!')

        self.PB_Marker_Cal_pushButton.setEnabled(True)
        self.repaint()


class ProtocolWindow(Protocol_Window_Form, Protocol_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None, motor=None, motor_reader=None):
        super(ProtocolWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.motor = motor
        self.motor_reader = motor_reader
        # self.load_params()
        self.prot_datapath = 'protocol/Protocol_01'

        self.ui = loadUi('ui/protocol.ui')
        self.setWindowTitle('Protocol')
        self.setGeometry(420, 40, 800, 850)

        self.Protocol_Execute_Protocol_pushButton.setEnabled(params.connectionmode)

        self.Protocol_Datapath_lineEdit.setText(self.prot_datapath)
        self.Protocol_Datapath_lineEdit.editingFinished.connect(lambda: self.set_protocol_datapath())
        
        self.Protocol_window_init_flag = 0
        self.protocol_new_protocol()
        self.protocol_load_protocol()
        self.Protocol_window_init_flag = 1
        
        self.Protocol_Message_comboBox.clear()
        self.Protocol_Message_comboBox.addItems(['Change Sample!', 'Move Sample!', 'Rotate Sample!'])
        
        self.Protocol_MoveTo_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.Protocol_MoveTo_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)

        self.Protocol_Add_pushButton.clicked.connect(lambda: self.protocol_add())
        self.Protocol_Overwrite_pushButton.clicked.connect(lambda: self.protocol_overwrite())
        self.Protocol_Insert_pushButton.clicked.connect(lambda: self.protocol_insert())
        self.Protocol_Delete_Last_pushButton.clicked.connect(lambda: self.protocol_delete_last())
        self.Protocol_Delete_pushButton.clicked.connect(lambda: self.protocol_delete())
        self.Protocol_New_Protocol_pushButton.clicked.connect(lambda: self.protocol_new_protocol())
        self.Protocol_Execute_Protocol_pushButton.clicked.connect(lambda: self.protocol_execute_protocol())
        
        self.Protocol_Add_Pause_pushButton.clicked.connect(lambda: self.protocol_add_pause())
        self.Protocol_Insert_Pause_pushButton.clicked.connect(lambda: self.protocol_insert_pause())
        self.Protocol_Add_Message_pushButton.clicked.connect(lambda: self.protocol_add_message())
        self.Protocol_Insert_Message_pushButton.clicked.connect(lambda: self.protocol_insert_message())
        self.Protocol_Add_MoveTo_pushButton.clicked.connect(lambda: self.protocol_add_moveto())
        self.Protocol_Insert_MoveTo_pushButton.clicked.connect(lambda: self.protocol_insert_moveto())

    def set_protocol_datapath(self):
        self.prot_datapath = self.Protocol_Datapath_lineEdit.text()
        if os.path.isdir(self.prot_datapath) == True: self.protocol_load_protocol()
        else: self.protocol_new_protocol()

    def protocol_add(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0], :] = self.protocol[:, :]
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 0] = params.GUImode
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 1] = params.sequence
        self.protocol = self.protocoltemp
        
        if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
        if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')
        
        try:
            shutil.copyfile('parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(self.protocol.shape[0] - 1) + '_parameters.pkl')
            time.sleep(0.01)
        except: print('No parameter file.')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')

    def protocol_delete_last(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] - 1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0] - 1, :] = self.protocol[0:self.protocol.shape[0] - 1, :]
        self.protocol = self.protocoltemp
        
        if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
        if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')
        
        try:
            os.remove(self.prot_datapath + '/Parameters/Task_' + str(self.protocol.shape[0]) + '_parameters.pkl')
            time.sleep(0.01)
        except: print('No parameter file.')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')

    def protocol_insert(self):
        if self.Protocol_Number_spinBox.value() - 1 <= self.protocoltemp.shape[0] - 1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value() - 1, :] = self.protocol[0:self.Protocol_Number_spinBox.value() - 1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 0] = params.GUImode
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 1] = params.sequence
            self.protocoltemp[self.Protocol_Number_spinBox.value():self.protocoltemp.shape[0] - 1, :] = self.protocol[self.Protocol_Number_spinBox.value() - 1:self.protocol.shape[0] - 1, :]
            self.protocol = self.protocoltemp
            
            if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
            if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

            for n in range(self.Protocol_Number_spinBox.value(), self.protocol.shape[0] - 1):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')
                    
            shutil.copyfile('parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(self.Protocol_Number_spinBox.value()) + '_parameters.pkl')
            time.sleep(0.01)
            
            for n in range(self.Protocol_Number_spinBox.value() + 1, self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                    os.remove(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')

        else: print('Index to high!')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')

    def protocol_delete(self):
        if self.Protocol_Number_spinBox.value() <= self.protocoltemp.shape[0] - 1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0], self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value() - 1, :] = self.protocol[0:self.Protocol_Number_spinBox.value() - 1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1:self.protocoltemp.shape[0] - 2,
            :] = self.protocol[self.Protocol_Number_spinBox.value():self.protocol.shape[0] - 1, :]
            self.protocol = np.matrix(np.zeros((self.protocoltemp.shape[0] - 1, self.protocoltemp.shape[1])))
            self.protocol = self.protocoltemp[0:self.protocoltemp.shape[0] - 1, :]
            
            if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
            if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

            for n in range(self.Protocol_Number_spinBox.value(), self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n + 1) + '_parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')
                
            try:
                os.remove(self.prot_datapath + '/Parameters/Task_' + str(self.protocol.shape[0]) + '_parameters.pkl')
                time.sleep(0.01)
            except: print('No parameter file.')

        else: print('Index to high!')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')

    def protocol_overwrite(self):
        if self.Protocol_Number_spinBox.value() - 1 <= self.protocoltemp.shape[0] - 2:
            self.protocol[self.Protocol_Number_spinBox.value() - 1, 0] = params.GUImode
            self.protocol[self.Protocol_Number_spinBox.value() - 1, 1] = params.sequence
            
            if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
            if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

            try:
                shutil.copyfile('parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(self.Protocol_Number_spinBox.value()) + '_parameters.pkl')
                time.sleep(0.01)
            except: print('No parameter file.')

        else: print('Index to high!')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')
        
    def protocol_add_pause(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0], :] = self.protocol[:, :]
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 0] = 6
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 1] = self.Protocol_Pause_doubleSpinBox.value()
        self.protocol = self.protocoltemp
        
        if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
        if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')
        
    def protocol_insert_pause(self):
        if self.Protocol_Number_spinBox.value() - 1 <= self.protocoltemp.shape[0] - 1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value() - 1, :] = self.protocol[0:self.Protocol_Number_spinBox.value() - 1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 0] = 6
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 1] = self.Protocol_Pause_doubleSpinBox.value()
            self.protocoltemp[self.Protocol_Number_spinBox.value():self.protocoltemp.shape[0] - 1, :] = self.protocol[self.Protocol_Number_spinBox.value() - 1:self.protocol.shape[0] - 1, :]
            self.protocol = self.protocoltemp
            
            if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
            if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

            for n in range(self.Protocol_Number_spinBox.value(), self.protocol.shape[0] - 1):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                    os.remove(self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')
            
            for n in range(self.Protocol_Number_spinBox.value() + 1, self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                    os.remove(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')

        else: print('Index to high!')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')
        
    def protocol_add_message(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0], :] = self.protocol[:, :]
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 0] = 7
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 1] = self.Protocol_Message_comboBox.currentIndex()
        self.protocol = self.protocoltemp
        
        if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
        if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')
        
    def protocol_insert_message(self):
        if self.Protocol_Number_spinBox.value() - 1 <= self.protocoltemp.shape[0] - 1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value() - 1, :] = self.protocol[0:self.Protocol_Number_spinBox.value() - 1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 0] = 7
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 1] = self.Protocol_Message_comboBox.currentIndex()
            self.protocoltemp[self.Protocol_Number_spinBox.value():self.protocoltemp.shape[0] - 1, :] = self.protocol[self.Protocol_Number_spinBox.value() - 1:self.protocol.shape[0] - 1, :]
            self.protocol = self.protocoltemp
            
            if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
            if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

            for n in range(self.Protocol_Number_spinBox.value(), self.protocol.shape[0] - 1):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                    os.remove(self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')
            
            for n in range(self.Protocol_Number_spinBox.value() + 1, self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                    os.remove(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')

        else: print('Index to high!')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')
        
    def protocol_add_moveto(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0], :] = self.protocol[:, :]
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 0] = 8
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 1] = self.Protocol_MoveTo_doubleSpinBox.value()
        self.protocol = self.protocoltemp

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')
        
    def protocol_insert_moveto(self):
        if self.Protocol_Number_spinBox.value() - 1 <= self.protocoltemp.shape[0] - 1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value() - 1, :] = self.protocol[0:self.Protocol_Number_spinBox.value() - 1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 0] = 8
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 1] = self.Protocol_MoveTo_doubleSpinBox.value()
            self.protocoltemp[self.Protocol_Number_spinBox.value():self.protocoltemp.shape[0] - 1, :] = self.protocol[self.Protocol_Number_spinBox.value() - 1:self.protocol.shape[0] - 1, :]
            self.protocol = self.protocoltemp
            
            if os.path.isdir(self.prot_datapath) != True: os.mkdir(self.prot_datapath)
            if os.path.isdir(self.prot_datapath + '/Parameters') != True: os.mkdir(self.prot_datapath + '/Parameters')

            for n in range(self.Protocol_Number_spinBox.value(), self.protocol.shape[0] - 1):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                    os.remove(self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')
            
            for n in range(self.Protocol_Number_spinBox.value() + 1, self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl', self.prot_datapath + '/Parameters/Task_' + str(n) + '_parameters.pkl')
                    time.sleep(0.01)
                    os.remove(self.prot_datapath + '/Parameters/Task_' + str(n - 1) + '_parameters_temp.pkl')
                    time.sleep(0.01)
                except: print('No parameter file.')

        else: print('Index to high!')

        self.protocol_plot_table()
        
        np.savetxt(self.prot_datapath + '/Protocol.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')

    def protocol_plot_table(self):
        self.Protocol_Table_tableWidget.setRowCount(self.protocol.shape[0] - 1)
        self.Protocol_Table_tableWidget.setColumnCount(self.protocol.shape[1])
        self.Protocol_Table_tableWidget.setHorizontalHeaderLabels(('Mode', 'Sequence'))
        for n in range(self.protocol.shape[0] - 1):

            if self.protocol[n, 0] == 0:
                self.Prot_Table_GUImode = 'Spectroscopy'
                self.Prot_Table_sequence = ('Free Induction Decay', 'Spin Echo', 'Inversion Recovery (FID)' \
                                            , 'Inversion Recovery (SE)', 'Saturation Inversion Recovery (FID)', 'Saturation Inversion Recovery (SE)' \
                                            , 'Echo Planar Spectrum (FID, 4 Echos)', 'Echo Planar Spectrum (SE, 4 Echos)', 'Turbo Spin Echo (4 Echos)' \
                                            , 'Free Induction Decay (Slice)', 'Spin Echo (Slice)', 'Inversion Recovery (FID, Slice)' \
                                            , 'Inversion Recovery (SE, Slice)', 'Saturation Inversion Recovery (FID, Slice)', 'Saturation Inversion Recovery (SE, Slice)' \
                                            , 'Echo Planar Spectrum (FID, 4 Echos, Slice)', 'Echo Planar Spectrum (SE, 4 Echos, Slice)', 'Turbo Spin Echo (4 Echos, Slice)' \
                                            , 'RF Loopback Test Sequence (Rect, Flip)', 'RF Loopback Test Sequence (Rect, 180°)', 'RF Loopback Test Sequence (Sinc, Flip)' \
                                            , 'RF Loopback Test Sequence (Sinc, 180°)', 'RF Loopback Test Sequence (Rect, inverse Flip)', 'RF Loopback Test Sequence (Rect, inverse 180°)' \
                                            , 'RF Loopback Test Sequence (Sinc, inverse Flip)', 'RF Loopback Test Sequence (Sinc, inverse 180°)', 'Gradient Test Sequence' \
                                            , 'RF SAR Calibration Test Sequence')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 1:
                self.Prot_Table_GUImode = 'Imaging'
                self.Prot_Table_sequence = ('2D Radial (GRE, Full)', '2D Radial (SE, Full)', '2D Radial (GRE, Half)' \
                                            , '2D Radial (SE, Half)', '2D Gradient Echo', '2D Spin Echo' \
                                            , '2D Spin Echo (InOut)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                            , '2D Saturation Inversion Recovery (GRE)', 'WIP 2D Saturation Inversion Recovery (SE)' \
                                            , '2D Turbo Spin Echo (4 Echos)', '2D Echo Planar Imaging (GRE, 4 Echos)', '2D Echo Planar Imaging (SE, 4 Echos)' \
                                            , '2D Diffusion (SE)', '2D Flow Compensation (GRE)', '2D Flow Compensation (SE)' \
                                            , '2D Radial (Slice, GRE, Full)', '2D Radial (Slice, SE, Full)', '2D Radial (Slice, GRE, Half)' \
                                            , '2D Radial (Slice, SE, Half)', '2D Gradient Echo (Slice)', '2D Spin Echo (Slice)' \
                                            , '2D Spin Echo (Slice, InOut)', '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)' \
                                            , 'WIP 2D Saturation Inversion Recovery (Slice, GRE)', 'WIP 2D Saturation Inversion Recovery (Slice, SE)', '2D Turbo Spin Echo (Slice, 4 Echos)' \
                                            , 'WIP 2D Echo Planar Imaging (Slice, GRE, 4 Echos)', 'WIP 2D Echo Planar Imaging (Slice, SE, 4 Echos)', '2D Diffusion (Slice, SE)' \
                                            , 'WIP 2D Flow Compensation (Slice, GRE)', 'WIP 2D Flow Compensation (Slice, SE)', 'WIP 3D FFT Gradient Echo (Slab)' \
                                            , '3D FFT Spin Echo (Slab)', '3D FFT Turbo Spin Echo (Slab)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 2:
                self.Prot_Table_GUImode = 'T1 Measurement'
                self.Prot_Table_sequence = ('Inversion Recovery (FID)', 'Inversion Recovery (SE)', 'Inversion Recovery (Slice, FID)' \
                                            , 'Inversion Recovery (Slice, SE)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 3:
                self.Prot_Table_GUImode = 'T2 Measurement'
                self.Prot_Table_sequence = ('Spin Echo', 'Saturation Inversion Recovery (FID)', 'Spin Echo (Slice)' \
                                            , 'Saturation Inversion Recovery (Slice, FID)', '2D Spin Echo', '2D Saturation Inversion Recovery (GRE)' \
                                            , '2D Spin Echo (Slice)', '2D Saturation Inversion Recovery (Slice, GRE)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 4:
                self.Prot_Table_GUImode = 'Projections'
                self.Prot_Table_sequence = ('2D Gradient Echo', '2D Inversion Recovery (GRE)', '2D Spin Echo' \
                                            , '2D Inversion Recovery (SE)', '2D Turbo Spin Echo (4 Echos)', '2D Gradient Echo (Slice)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Spin Echo (Slice)', '2D Inversion Recovery (Slice, SE)' \
                                            , '2D Turbo Spin Echo (Slice, 4 Echos)', '3D FFT Spin Echo (Slab)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 5:
                self.Prot_Table_GUImode = 'Image Stitching'
                self.Prot_Table_sequence = ('2D Gradient Echo', '2D Inversion Recovery (GRE)', '2D Spin Echo' \
                                            , '2D Inversion Recovery (SE)', '2D Turbo Spin Echo (4 Echos)', '2D Gradient Echo (Slice)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Spin Echo (Slice)', '2D Inversion Recovery (Slice, SE)' \
                                            , '2D Turbo Spin Echo (Slice, 4 Echos)', '3D FFT Spin Echo (Slab)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 6:
                self.Prot_Table_GUImode = 'Pause [s]'
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(str(self.protocol[n, 1])))
            elif self.protocol[n, 0] == 7:
                self.Prot_Table_GUImode = 'Message'
                self.Prot_Table_sequence = ('Change Sample!', 'Move Sample!', 'Rotate Sample!')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 8:
                self.Prot_Table_GUImode = 'Move to [mm]'
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(str(self.protocol[n, 1])))

        self.Protocol_Table_tableWidget.resizeColumnToContents(0)
        self.Protocol_Table_tableWidget.resizeColumnToContents(1)

        self.Protocol_Table_tableWidget.show()

    def protocol_new_protocol(self):
        if self.Protocol_window_init_flag != 0:
            if os.path.isdir(self.prot_datapath) == True:
                shutil.rmtree(self.prot_datapath)
                print('Protocol directory overwritten!')
        
        self.protocol = np.matrix([0, 0])
        self.protocol_plot_table()

    def protocol_load_protocol(self):
        if os.path.isdir(self.prot_datapath) == True:
            if os.path.isfile(self.prot_datapath + '/Protocol.txt') == True:
                self.protocoltemp = np.genfromtxt(self.prot_datapath + '/Protocol.txt', ndmin=2)
                self.protocol = np.matrix(np.zeros((self.protocoltemp.shape[0] + 1, self.protocoltemp.shape[1])))
                self.protocol[0:self.protocoltemp.shape[0], :] = self.protocoltemp[:, :]
                self.protocol_plot_table()
            else: print('No protocol file!!')
        else:
            if self.Protocol_window_init_flag != 0:
                print('No protocol directory!!')

    def protocol_execute_protocol(self):
        print('WIP')

        self.Protocol_Execute_Protocol_pushButton.setEnabled(False)
        self.repaint()
        
        if os.path.isdir(self.prot_datapath) == True:
            if os.path.isdir(self.prot_datapath + '/Parameters') == True:

                try:
                    shutil.copyfile('parameters.pkl', self.prot_datapath + '/Parameters/Parameters_temp.pkl')
                    time.sleep(0.01)
                except:
                    print('No parameter file.')

                self.datapathtemp = ''
                self.datapathtemp = params.datapath
                self.prot_motor_actual_position_temp = 0
                self.prot_motor_actual_position_temp = params.motor_actual_position
                self.prot_motor_actual_position = 0

                for n in range(self.protocol.shape[0] - 1):
                    self.prot_motor_actual_position = params.motor_actual_position
                    
                    print('Protocol task: ' + str(n + 1))
                    if self.protocol[n, 0] < 6:
                        try:
                            shutil.copyfile(self.prot_datapath + '/Parameters/Task_' + str(n + 1) + '_parameters.pkl', 'parameters.pkl')
                            time.sleep(0.01)
                            params.loadParam()
                            params.motor_actual_position = self.prot_motor_actual_position
                        except:
                            print('No parameter file!!')
                        
                    if self.protocol[n, 0] == 6:
                        print('Pause')
                        params.GUImode = 6
                        params.TR = self.protocol[n, 1]
                    if self.protocol[n, 0] == 7:
                        print('Message')
                        params.GUImode = 7
                        params.sequence = self.protocol[n, 1]
                    if self.protocol[n, 0] == 8:
                        params.GUImode = 8
                        params.motor_goto_position = self.protocol[n, 1]
                    
                    if params.GUImode == 0: self.datapath_mode = 'Spectroscopy'
                    if params.GUImode == 1: self.datapath_mode = 'Imaging'
                    if params.GUImode == 2: self.datapath_mode = 'T1 Measurement'
                    if params.GUImode == 3: self.datapath_mode = 'T2 Measurement'
                    if params.GUImode == 4: self.datapath_mode = 'Projections'
                    if params.GUImode == 5: self.datapath_mode = 'Image Stitching'
                    
                    if params.GUImode < 6:
                        if os.path.isdir(self.prot_datapath + '/Task_' + str(n + 1) + '_rawdata') != True: os.mkdir(self.prot_datapath + '/Task_' + str(n + 1) + '_rawdata')
                        params.datapath = self.prot_datapath + '/Task_' + str(n + 1) + '_rawdata/' + self.datapath_mode + '_rawdata'
                    else: params.datapath = ''
                    
                    self.protocol_acquire()
                    
                    if params.GUImode < 6:
                        time.sleep(params.TR/1000)
                    if params.GUImode == 8:
                        time.sleep(1)
                    
                params.motor_goto_position = self.prot_motor_actual_position_temp
                proc.motor_move(motor=self.motor)
                time.sleep(1)

                params.datapath = self.datapathtemp

                try:
                    shutil.copyfile(self.prot_datapath + '/Parameters/Parameters_temp.pkl', 'parameters.pkl')
                    time.sleep(0.01)
                    
                    params.loadParam()
                    
                    os.remove(self.prot_datapath + '/Parameters/Parameters_temp.pkl')
                    
                    
                except:
                    print('No parameter file.')
            
            else: print('No protocol parameter directory!!')
        else: print('No protocol directory!!')
            
        self.Protocol_Execute_Protocol_pushButton.setEnabled(True)
        self.repaint()

    def protocol_acquire(self):
        if params.agriMRI_mode == 1:
            self.datapath_temp = ''
            self.datapath_temp = params.datapath
            self.agriMRI_folder_structure_temp = ''
            self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
            
            if params.agriMRI_folder_structure != 'rawdata/': params.save_AgriMRI_Metadata_file_json()
            else: print('\033[1m' + 'No experiment ID set!! Save data to rawdata folder.' + '\033[0m')
            
            params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_rawdata'
            if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
            params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/'
            params.datapath = params.agriMRI_folder_structure + params.datapath
        
        if params.GUImode == 2:
            if params.sequence == 0:
                proc.T1measurement_IR_FID()
            elif params.sequence == 1:
                proc.T1measurement_IR_SE()
            elif params.sequence == 2:
                proc.T1measurement_IR_FID_Gs()
            elif params.sequence == 3:
                proc.T1measurement_IR_SE_Gs()
            elif params.sequence == 4:
                proc.T1measurement_Image_IR_GRE()
            elif params.sequence == 5:
                proc.T1measurement_Image_IR_SE()
            elif params.sequence == 6:
                proc.T1measurement_Image_IR_GRE_Gs()
            elif params.sequence == 7:
                proc.T1measurement_Image_IR_SE_Gs()
        elif params.GUImode == 3:
            if params.sequence == 0:
                proc.T2measurement_SE()
            elif params.sequence == 1:
                proc.T2measurement_SIR_FID()
            elif params.sequence == 2:
                proc.T2measurement_SE_Gs()
            elif params.sequence == 3:
                proc.T2measurement_SIR_FID_Gs()
            elif params.sequence == 4:
                proc.T2measurement_Image_SE()
            elif params.sequence == 5:
                proc.T2measurement_Image_SIR_GRE()
            elif params.sequence == 6:
                proc.T2measurement_Image_SE_Gs()
            elif params.sequence == 7:
                proc.T2measurement_Image_SIR_GRE_Gs()
        elif params.GUImode == 5:
            if params.motor_enable == 1:
                if params.motor_available:
                    self.motor_reader.blockSignals(True)
                    if params.sequence == 0:
                        proc.image_stitching_2D_GRE(motor=self.motor)
                    if params.sequence == 1:
                        proc.image_stitching_2D_GRE(motor=self.motor)
                    if params.sequence == 2:
                        proc.image_stitching_2D_SE(motor=self.motor)
                    if params.sequence == 3:
                        proc.image_stitching_2D_SE(motor=self.motor)
                    if params.sequence == 4:
                        proc.image_stitching_2D_SE(motor=self.motor)
                    if params.sequence == 5:
                        proc.image_stitching_2D_GRE_slice(motor=self.motor)
                    if params.sequence == 6:
                        proc.image_stitching_2D_GRE_slice(motor=self.motor)
                    if params.sequence == 7:
                        proc.image_stitching_2D_SE_slice(motor=self.motor)
                    if params.sequence == 8:
                        proc.image_stitching_2D_SE_slice(motor=self.motor)
                    if params.sequence == 9:
                        proc.image_stitching_2D_SE_slice(motor=self.motor)
                    if params.sequence == 10:
                        proc.image_stitching_3D_slab(motor=self.motor)
                    if params.sequence == 11:
                        proc.image_stitching_3D_TSE_slab(motor=self.motor)
                    self.motor_reader.blockSignals(False)                
                else:
                    print('Motor Control: Motor not available, maybe it is still homing?')
            else:
                if params.sequence == 0:
                    proc.image_stitching_2D_GRE()
                if params.sequence == 1:
                    proc.image_stitching_2D_GRE()
                if params.sequence == 2:
                    proc.image_stitching_2D_SE()
                if params.sequence == 3:
                    proc.image_stitching_2D_SE()
                if params.sequence == 4:
                    proc.image_stitching_2D_SE()
                if params.sequence == 5:
                    proc.image_stitching_2D_GRE_slice()
                if params.sequence == 6:
                    proc.image_stitching_2D_GRE_slice()
                if params.sequence == 7:
                    proc.image_stitching_2D_SE_slice()
                if params.sequence == 8:
                    proc.image_stitching_2D_SE_slice()
                if params.sequence == 9:
                    proc.image_stitching_2D_SE_slice()
                if params.sequence == 10:
                    proc.image_stitching_3D_slab()
                if params.sequence == 11:
                    proc.image_stitching_3D_TSE_slab()
            
        elif params.GUImode == 1:
            if params.autorecenter == 1:
                self.frequencyoffsettemp = 0
                self.frequencyoffsettemp = params.frequencyoffset
                params.frequencyoffset = 0
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
                    seq.sequence_upload()
                elif params.sequence == 17 or params.sequence == 19 or params.sequence == 21 \
                        or params.sequence == 24 or params.sequence == 26 or params.sequence == 29 \
                        or params.sequence == 32 or params.sequence == 34:
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
                    seq.sequence_upload()
                elif params.sequence == 18 or params.sequence == 20 or params.sequence == 22 \
                        or params.sequence == 23 or params.sequence == 25 or params.sequence == 27 \
                        or params.sequence == 28 or params.sequence == 30 or params.sequence == 31 \
                        or params.sequence == 33 or params.sequence == 35 or params.sequence == 36:
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
                    print('Autorecenter to: ' + str(params.frequency) + 'MHz')
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-10)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-10)/1000)
                    time.sleep(0.01)
                    seq.sequence_upload()
            else:
                seq.sequence_upload()
        elif params.GUImode == 6:
            print('Pause: ' + str(params.TR) + 's')
            msg_box = QMessageBox()
            msg_box.setText('Pause: ' + str(params.TR) + 's')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(int(params.TR*1000))
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        elif params.GUImode == 7:
            self.protocol_messagebox_string = ('Change Sample!', 'Move Sample!', 'Rotate Sample!')
            print(self.protocol_messagebox_string[int(params.sequence)])
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(self.protocol_messagebox_string[int(params.sequence)])
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
        elif params.GUImode == 8:
            proc.motor_move(motor=self.motor)
        else:
            seq.sequence_upload()
            
        if params.headerfileformat == 0:
            params.save_header_file_txt()
        else:
            params.save_header_file_json()
            
        if params.agriMRI_mode == 1:
            params.datapath = self.datapath_temp
            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp


class PlotWindow(Plot_Window_Form, Plot_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(PlotWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.dialog_3D_layers = None
        
        self.fig_canvas = None
        self.IMag_canvas = None
        self.IPha_canvas = None
        self.kMag_canvas = None
        self.kPha_canvas = None
        self.all_canvas = None
        self.fig_canvas1 = None
        self.fig_canvas2 = None
        self.IComb_canvas = None
        self.IDiff_canvas = None
        self.hist_canvas = None

        self.datapath_plot = ''
        self.datapath_plot = params.datapath
        
        self.load_params()
        
        self.ui = loadUi('ui/plotview.ui')
        self.setWindowTitle('Plotvalues - ' + params.datapath + '.txt')
        self.setGeometry(10, 490, 400, 500)

        self.Animate_pushButton.setEnabled(False)
        self.View_3D_Data_pushButton.setEnabled(False)
        self.Save_Spectrum_Data_pushButton.setEnabled(False)
        self.Save_Image_Data_pushButton.setEnabled(False)
        self.Save_Mag_Image_Data_pushButton.setEnabled(False)
        self.Save_Pha_Image_Data_pushButton.setEnabled(False)
        self.Hist_pushButton.setEnabled(False)
        
        if params.GUImode == 0:
            if params.sequence == 18 or params.sequence == 19 or params.sequence == 20 or params.sequence == 21 \
               or params.sequence == 22 or params.sequence == 23 or params.sequence == 24 or params.sequence == 25:
                self.rf_loopback_test_spectrum_plot_init()
            else:
                self.spectrum_plot_init()
            self.Save_Spectrum_Data_pushButton.setEnabled(True)
            
        elif params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36:
                params.imageminimum = np.min(params.img_mag)
                self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
                params.imagemaximum = np.max(params.img_mag)
                self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
                self.imaging_3D_plot_init()
                self.Save_Image_Data_pushButton.setEnabled(True)
                self.Save_Mag_Image_Data_pushButton.setEnabled(True)
                self.Save_Pha_Image_Data_pushButton.setEnabled(True)
                self.View_3D_Data_pushButton.setEnabled(True)
                self.Hist_pushButton.setEnabled(True)
            elif params.sequence == 14 or params.sequence == 31:
                self.imaging_diff_plot_init()
            else:
                params.imageminimum = np.min(params.img_mag)
                self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
                params.imagemaximum = np.max(params.img_mag)
                self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
                self.imaging_plot_init()
                self.Save_Image_Data_pushButton.setEnabled(True)
                self.Save_Mag_Image_Data_pushButton.setEnabled(True)
                self.Save_Pha_Image_Data_pushButton.setEnabled(True)
                self.Animate_pushButton.setEnabled(True)
                self.Hist_pushButton.setEnabled(True)

        elif params.GUImode == 2:
            if params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3:
                self.T1_plot_init()
                self.Save_Spectrum_Data_pushButton.setEnabled(True)
            else:
                self.T1_imaging_plot_init()

        elif params.GUImode == 3:
            if params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3:
                self.T2_plot_init()
                self.Save_Spectrum_Data_pushButton.setEnabled(True)
            else:
                self.T2_imaging_plot_init()

        elif params.GUImode == 4:
            if params.sequence == 0 or params.sequence == 1 or params.sequence == 4 or params.sequence == 5:
                params.frequencyplotrange = 250000
                self.Frequncyaxisrange_spinBox.setValue(params.frequencyplotrange)
                self.projection_plot_init()
            elif params.sequence == 2 or params.sequence == 3 or params.sequence == 6 or params.sequence == 7:
                params.frequencyplotrange = 250000
                self.Frequncyaxisrange_spinBox.setValue(params.frequencyplotrange)
                self.spectrum_plot_init()

        elif params.GUImode == 5:
            if params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3 \
                or params.sequence == 4  or params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                or params.sequence == 8 or params.sequence == 9:
                params.imageminimum = np.min(params.img_st_mag)
                self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
                params.imagemaximum = np.max(params.img_st_mag)
                self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
                params.image_stitching_slice = 0
                if params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                    self.imaging_stitching_plot_init()
                    self.View_3D_Data_pushButton.setEnabled(True)  
                else: self.imaging_stitching_plot_init()
                self.Save_Image_Data_pushButton.setEnabled(True)
                self.Save_Mag_Image_Data_pushButton.setEnabled(True)
                self.Save_Pha_Image_Data_pushButton.setEnabled(True)
                self.Hist_pushButton.setEnabled(True)
            elif params.sequence == 10 or params.sequence == 11:
                params.imageminimum = np.min(params.img_st_mag)
                self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
                params.imagemaximum = np.max(params.img_st_mag)
                self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
                self.imaging_stitching_3D_plot_init()
                self.Save_Image_Data_pushButton.setEnabled(True)
                self.Save_Mag_Image_Data_pushButton.setEnabled(True)
                self.Save_Pha_Image_Data_pushButton.setEnabled(True)
                self.View_3D_Data_pushButton.setEnabled(True)
                self.Hist_pushButton.setEnabled(True)

        self.Frequncyaxisrange_spinBox.setKeyboardTracking(False)
        self.Frequncyaxisrange_spinBox.valueChanged.connect(self.update_params)

        self.Save_Spectrum_Data_pushButton.clicked.connect(lambda: self.save_spectrum_data())
        self.Save_Mag_Image_Data_pushButton.clicked.connect(lambda: self.save_mag_image_data())
        self.Save_Pha_Image_Data_pushButton.clicked.connect(lambda: self.save_pha_image_data())
        self.Save_Image_Data_pushButton.clicked.connect(lambda: self.save_image_data())
        
        self.View_3D_Data_pushButton.clicked.connect(lambda: self.view_3D_layers())

        self.Animation_Step_spinBox.setKeyboardTracking(False)
        self.Animation_Step_spinBox.valueChanged.connect(self.update_params)
        self.Animate_pushButton.clicked.connect(lambda: self.animate())
        
        self.Hist_pushButton.clicked.connect(lambda: self.histogram())
        
        self.Image_Minimum_doubleSpinBox.setKeyboardTracking(False)
        self.Image_Minimum_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Image_Maximum_doubleSpinBox.setKeyboardTracking(False)
        self.Image_Maximum_doubleSpinBox.valueChanged.connect(self.update_params)

    def load_params(self):
        self.label.setText('Frequency Range [Hz]')
        self.Frequncyaxisrange_spinBox.setMaximum(250000)
        self.Frequncyaxisrange_spinBox.setMinimum(1000)
        self.Frequncyaxisrange_spinBox.setSingleStep(1000)
        if params.GUImode == 0:
            self.Frequncyaxisrange_spinBox.setEnabled(True)
            self.Frequncyaxisrange_spinBox.setValue(params.frequencyplotrange)
            self.Center_Frequency_lineEdit.setEnabled(True)
            self.Center_Frequency_lineEdit.setText(str(params.centerfrequency))
            self.FWHM_lineEdit.setEnabled(True)
            self.FWHM_lineEdit.setText(str(params.FWHM))
            self.Peak_lineEdit.setEnabled(True)
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setEnabled(True)
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setEnabled(True)
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Image_Minimum_doubleSpinBox.setEnabled(False)
            self.Image_Minimum_doubleSpinBox.setValue(0.0)
            self.Image_Maximum_doubleSpinBox.setEnabled(False)
            self.Image_Maximum_doubleSpinBox.setValue(0.0)
            self.Inhomogeneity_lineEdit.setEnabled(True)
            self.Inhomogeneity_lineEdit.setText(str(params.inhomogeneity))
            self.Animation_Step_spinBox.setValue(params.animationstep)
        elif params.GUImode == 1:
            self.Frequncyaxisrange_spinBox.setEnabled(False)
            self.Frequncyaxisrange_spinBox.setValue(0)
            self.Center_Frequency_lineEdit.setEnabled(False)
            self.Center_Frequency_lineEdit.setText('')
            self.FWHM_lineEdit.setEnabled(False)
            self.FWHM_lineEdit.setText('')
            self.Peak_lineEdit.setEnabled(True)
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setEnabled(True)
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setEnabled(True)
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Image_Minimum_doubleSpinBox.setEnabled(True)
            self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
            self.Image_Maximum_doubleSpinBox.setEnabled(True)
            self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
            self.Inhomogeneity_lineEdit.setEnabled(False)
            self.Inhomogeneity_lineEdit.setText('')
            self.Animation_Step_spinBox.setValue(params.animationstep)
        elif params.GUImode == 5:
            self.Frequncyaxisrange_spinBox.setEnabled(False)
            self.Frequncyaxisrange_spinBox.setValue(0)
            if params.sequence != 10:
                if params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                    self.Frequncyaxisrange_spinBox.setEnabled(True)
                    self.label.setText('Slice (0 = all)')
                    self.Frequncyaxisrange_spinBox.setMaximum(params.motor_image_count)
                    self.Frequncyaxisrange_spinBox.setMinimum(0)
                    self.Frequncyaxisrange_spinBox.setSingleStep(1)
                    self.Frequncyaxisrange_spinBox.setValue(0)
                    
            self.Center_Frequency_lineEdit.setEnabled(False)
            self.Center_Frequency_lineEdit.setText('')
            self.FWHM_lineEdit.setEnabled(False)
            self.FWHM_lineEdit.setText('')
            self.Peak_lineEdit.setEnabled(True)
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setEnabled(True)
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setEnabled(True)
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Image_Minimum_doubleSpinBox.setEnabled(True)
            self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
            self.Image_Maximum_doubleSpinBox.setEnabled(True)
            self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
            self.Inhomogeneity_lineEdit.setEnabled(False)
            self.Inhomogeneity_lineEdit.setText('')
            self.Animation_Step_spinBox.setValue(params.animationstep)

    def update_params(self):
        params.imageminimum = self.Image_Minimum_doubleSpinBox.value()
        params.imagemaximum = self.Image_Maximum_doubleSpinBox.value()
        params.animationstep = self.Animation_Step_spinBox.value()
        
        self.datapath_plot_temp= ''
        self.datapath_plot_temp = params.datapath
        params.datapath = self.datapath_plot
        
        self.GUImode_temp = 0
        self.GUImode_temp = params.GUImode
        self.sequence_temp = 0
        self.sequence_temp = params.sequence
        self.imageorientation_temp = ''
        self.imageorientation_temp = params.imageorientation
        self.FOV_temp = 0
        self.FOV_temp = params.FOV
        self.SPEsteps_temp = 0
        self.SPEsteps_temp = params.SPEsteps
        self.nPE_temp = 0
        self.nPE_temp = params.nPE
        self.motor_image_count_temp = 0
        self.motor_image_count_temp = params.motor_image_count
        self.motor_movement_step_temp = 0
        self.motor_movement_step_temp = params.motor_movement_step
        self.slicethickness_temp = 0
        self.slicethickness_temp = params.slicethickness
        self.motor_total_image_length_temp = 0
        self.motor_total_image_length_temp = params.motor_total_image_length
        self.motor_start_position_temp = 0
        self.motor_start_position_temp = params.motor_start_position
        self.motor_end_position_temp = 0
        self.motor_end_position_temp = params.motor_end_position
        self.radialanglestep_temp = 0
        self.radialanglestep_temp = params.radialanglestep
        self.radialosfactor_temp = 0
        self.radialosfactor_temp = params.radialosfactor
        self.autofreqoffset_temp = 0
        self.autofreqoffset_temp = params.autofreqoffset
        self.sliceoffset_temp = 0
        self.sliceoffset_temp = params.sliceoffset
        
        if params.headerfileformat == 0:
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_Header.txt') == True:
                    f = open(params.datapath + '/Image_Stitching_Header.txt', 'r+')
                    headerlines = f.readlines()
                    f.close()
                else: print('No .txt header file!!')
            elif os.path.isdir(params.datapath) == False:
                if os.path.isfile(params.datapath + '_Header.txt') == True:
                    f = open(params.datapath + '_Header.txt', 'r+')
                    headerlines = f.readlines()
                    f.close()
                else: print('No .txt header file!!')
            else: print('No directory or .txt header file!!')
            
            self.headerline_string_split = headerlines[2].split(': ')
            params.GUImode = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[3].split(': ')
            params.sequence = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[30].split(': ')
            params.imageorientation = self.headerline_string_split[1]
            self.headerline_string_split = params.imageorientation.split('\n')
            params.imageorientation = self.headerline_string_split[0]
            self.headerline_string_split = headerlines[70].split(': ')
            params.FOV = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[54].split(': ')
            params.SPEsteps = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[32].split(': ')
            params.nPE = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[91].split(': ')
            params.motor_image_count = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[90].split(': ')
            params.motor_movement_step = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[71].split(': ')
            params.slicethickness = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[89].split(': ')
            params.motor_total_image_length = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[87].split(': ')
            params.motor_start_position = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[88].split(': ')
            params.motor_end_position = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[66].split(': ')
            params.radialanglestep = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[67].split(': ')
            params.radialosfactor = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[73].split(': ')
            params.autofreqoffset = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[74].split(': ')
            params.sliceoffset = float(self.headerline_string_split[1])
                     
        else:
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_Header.json') == True:
                    with open(params.datapath + '/Image_Stitching_Header.json', 'r', encoding='utf-8') as j:
                        jsonparams = json.loads(j.read())
                else: print('No .json header file!!')
            elif os.path.isdir(params.datapath) == False:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    with open(params.datapath + '_Header.json', 'r', encoding='utf-8') as j:
                        jsonparams = json.loads(j.read())
                else: print('No .json header file!!')
            else: print('No directory or .json header file!!')
                    
            params.GUImode = int(jsonparams['GUI mode'])
            params.sequence = int(jsonparams['Sequence'])
            params.imageorientation = jsonparams['Image orientation']
            params.FOV = jsonparams['FOV [mm]']
            params.SPEsteps = int(jsonparams['3D phase steps'])
            params.nPE = int(jsonparams['Image resolution [pixel]'])
            params.motor_image_count = int(jsonparams['Motor image count'])
            params.motor_movement_step = np.abs(jsonparams['Motor movement step [mm]'])
            params.slicethickness = jsonparams['Slice/Slab thickness [mm]']
            params.motor_total_image_length = jsonparams['Motor total image length [mm]']
            params.motor_start_position = jsonparams['Motor start position [mm]']
            params.motor_end_position = jsonparams['Motor end position [mm]']
            params.radialanglestep = jsonparams['Radial angle [°]']
            params.radialosfactor = jsonparams['Radial oversampling factor']
            params.autofreqoffset = jsonparams['Auto frequency offset']
            params.sliceoffset = jsonparams['Slice offset [mm]']
            
        for attr_name in dir(self):
            if 'canvas' in attr_name.lower():
                canvas = getattr(self, attr_name)
                if canvas != None:
                    plt.close(canvas.figure)
                    canvas.setParent(None)
                    canvas.deleteLater()
                    setattr(self, attr_name, None)

        if params.GUImode == 0:
            params.frequencyplotrange = self.Frequncyaxisrange_spinBox.value()
            if params.sequence == 18 or params.sequence == 19 or params.sequence == 20 or params.sequence == 21: self.rf_loopback_test_spectrum_plot_init()
            else: self.spectrum_plot_init()
            self.Save_Spectrum_Data_pushButton.setEnabled(True)
        elif params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36: self.imaging_3D_plot_init()
            elif params.sequence == 14 or params.sequence == 31: print('WIP')
            else: self.imaging_plot_init()
        elif params.GUImode == 4:
            self.projection_plot_init()
        elif params.GUImode == 5:
            params.image_stitching_slice = self.Frequncyaxisrange_spinBox.value()
            if params.sequence == 10 or params.sequence == 11: self.imaging_stitching_3D_plot_init()
            else:
                if params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                    if params.image_stitching_slice == 0: self.imaging_stitching_plot_init()
                    else: self.imaging_stitching_single_plot_init()
                else: self.imaging_stitching_plot_init()
                
        params.datapath = self.datapath_plot_temp
            
        params.GUImode = self.GUImode_temp
        params.sequence = self.sequence_temp
        params.imageorientation = self.imageorientation_temp
        params.FOV = self.FOV_temp
        params.SPEsteps = self.SPEsteps_temp
        params.nPE = self.nPE_temp
        params.motor_image_count = self.motor_image_count_temp
        params.motor_movement_step = self.motor_movement_step_temp
        params.slicethickness = self.slicethickness_temp
        params.motor_total_image_length = self.motor_total_image_length_temp
        params.motor_start_position = self.motor_start_position_temp
        params.motor_end_position = self.motor_end_position_temp
        params.radialanglestep = self.radialanglestep_temp
        params.radialosfactor = self.radialosfactor_temp
        params.autofreqoffset = self.autofreqoffset_temp
        params.sliceoffset = self.sliceoffset_temp

    def spectrum_plot_init(self):
        self.fig = Figure()
        self.fig.set_facecolor('None')
        self.fig_canvas = FigureCanvas(self.fig)

        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)

        self.ax1.plot(params.freqencyaxis, params.spectrumfft)
        self.ax1.set_xlim([-params.frequencyplotrange / 2, params.frequencyplotrange / 2])
        self.ax1.set_ylim([0, 1.1 * np.max(params.spectrumfft)])
        self.ax1.set_title('Spectrum')
        self.ax1.set_ylabel('RX Signal [arb.]')
        self.ax1.set_xlabel(r'$\Delta$ Frequency [Hz]')
        self.major_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 11)
        self.minor_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 51)
        self.ax1.set_xticks(self.major_ticks)
        self.ax1.set_xticks(self.minor_ticks, minor=True)
        self.ax1.grid(which='major', color='#888888', linestyle='-')
        self.ax1.grid(which='minor', color='#888888', linestyle=':')
        self.ax1.grid(which='both', visible=True)
        
        self.ax2.plot(params.timeaxis, params.mag, label='Magnitude')
        self.ax2.plot(params.timeaxis, params.real, label='Real')
        self.ax2.plot(params.timeaxis, params.imag, label='Imaginary')
        self.ax2.set_xlim([0, params.timeaxis[int(params.timeaxis.shape[0] - 1)]])
        self.ax2.set_title('Signal')
        self.ax2.set_ylabel('RX Signal [mV]')
        self.ax2.set_xlabel('Time [ms]')
        self.major_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) + 1)
        self.minor_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) * 5 + 1)
        self.ax2.set_xticks(self.major_ticks)
        self.ax2.set_xticks(self.minor_ticks, minor=True)
        self.ax2.grid(which='major', color='#888888', linestyle='-')
        self.ax2.grid(which='minor', color='#888888', linestyle=':')
        self.ax2.grid(which='both', visible=True)
        self.ax2.legend()
        self.ax2.plot(params.timeaxis, params.mag, label='Magnitude')
        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 1160, 950)
        self.fig_canvas.show()
        
    def rf_loopback_test_spectrum_plot_init(self):
        self.fig = Figure()
        self.fig.set_facecolor('None')
        self.fig_canvas = FigureCanvas(self.fig)

        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)

        self.ax1.plot(params.freqencyaxis, params.spectrumfft)
        self.ax1.set_xlim([-params.frequencyplotrange / 2, params.frequencyplotrange / 2])
        self.ax1.set_ylim([0, 1.1 * np.max(params.spectrumfft)])
        self.ax1.set_title('Spectrum')
        self.ax1.set_ylabel('RX Signal [arb.]')
        self.ax1.set_xlabel(r'$\Delta$ Frequency [Hz]')
        self.major_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 11)
        self.minor_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 51)
        self.ax1.set_xticks(self.major_ticks)
        self.ax1.set_xticks(self.minor_ticks, minor=True)
        self.ax1.grid(which='major', color='#888888', linestyle='-')
        self.ax1.grid(which='minor', color='#888888', linestyle=':')
        self.ax1.grid(which='both', visible=True)
        
        self.ax2.plot(params.timeaxis, params.mag, label='Magnitude')
        self.ax2.plot(params.timeaxis, params.real, label='Real')
        self.ax2.plot(params.timeaxis, params.imag, label='Imaginary')
        self.ax2.set_xlim([params.timeaxis[0], params.timeaxis[int(params.timeaxis.shape[0] - 1)]])
        self.ax2.set_title('Signal')
        self.ax2.set_ylabel('RX Signal [mV]')
        self.ax2.set_xlabel('time [µs]')
        self.major_ticks = np.arange(math.floor(params.timeaxis[0]), math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)]), 10)
        self.minor_ticks = np.arange(math.floor(params.timeaxis[0]), math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)]), 2)
        self.ax2.set_xticks(self.major_ticks)
        self.ax2.set_xticks(self.minor_ticks, minor=True)
        self.ax2.grid(which='major', color='#888888', linestyle='-')
        self.ax2.grid(which='minor', color='#888888', linestyle=':')
        self.ax2.grid(which='both', visible=True)
        self.ax2.legend()
        self.ax2.plot(params.timeaxis, params.mag, label='Magnitude')
        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 1160, 950)
        self.fig_canvas.show()

    def projection_plot_init(self):
        self.fig = Figure()
        self.fig.set_facecolor('None')
        self.fig_canvas = FigureCanvas(self.fig)

        if params.projx.shape[0] == params.freqencyaxis.shape[0]:
            self.ax1 = self.fig.add_subplot(6, 1, 1)
            self.ax2 = self.fig.add_subplot(6, 1, 2)
            self.ax1.plot(params.freqencyaxis, params.projx[:, 3])
            self.ax1.set_xlim([-params.frequencyplotrange / 2, params.frequencyplotrange / 2])
            self.ax1.set_ylim([0, 1.1 * np.max(params.projx[:, 3])])
            self.ax1.set_title('X - Spectrum')
            self.ax1.set_ylabel('RX Signal [arb.]')
            self.ax1.set_xlabel(r'$\Delta$ Frequency [Hz]')
            self.major_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 11)
            self.minor_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 51)
            self.ax1.set_xticks(self.major_ticks)
            self.ax1.set_xticks(self.minor_ticks, minor=True)
            self.ax1.grid(which='major', color='#888888', linestyle='-')
            self.ax1.grid(which='minor', color='#888888', linestyle=':')
            self.ax1.grid(which='both', visible=True)
            self.ax2.plot(params.timeaxis, params.projx[:, 0], label='Magnitude')
            self.ax2.plot(params.timeaxis, params.projx[:, 1], label='Real')
            self.ax2.plot(params.timeaxis, params.projx[:, 2], label='Imaginary')
            self.ax2.set_xlim([0, params.timeaxis[int(params.timeaxis.shape[0] - 1)]])
            self.ax2.set_title('X - Signal')
            self.ax2.set_ylabel('RX Signal [mV]')
            self.ax2.set_xlabel('time [ms]')
            self.major_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) + 1)
            self.minor_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) * 5 + 1)
            self.ax2.set_xticks(self.major_ticks)
            self.ax2.set_xticks(self.minor_ticks, minor=True)
            self.ax2.grid(which='major', color='#888888', linestyle='-')
            self.ax2.grid(which='minor', color='#888888', linestyle=':')
            self.ax2.grid(which='both', visible=True)
            self.ax2.legend()
            self.ax2.plot(params.timeaxis, params.projx[:, 0], label='Magnitude')

        if params.projy.shape[0] == params.freqencyaxis.shape[0]:
            self.ax3 = self.fig.add_subplot(6, 1, 3)
            self.ax4 = self.fig.add_subplot(6, 1, 4)
            self.ax3.plot(params.freqencyaxis, params.projy[:, 3])
            self.ax3.set_xlim([-params.frequencyplotrange / 2, params.frequencyplotrange / 2])
            self.ax3.set_ylim([0, 1.1 * np.max(params.projy[:, 3])])
            self.ax3.set_title('Y - Spectrum')
            self.ax3.set_ylabel('RX Signal [arb.]')
            self.ax3.set_xlabel(r'$\Delta$ Frequency [Hz]')
            self.major_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 11)
            self.minor_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 51)
            self.ax3.set_xticks(self.major_ticks)
            self.ax3.set_xticks(self.minor_ticks, minor=True)
            self.ax3.grid(which='major', color='#888888', linestyle='-')
            self.ax3.grid(which='minor', color='#888888', linestyle=':')
            self.ax3.grid(which='both', visible=True)
            self.ax4.plot(params.timeaxis, params.projy[:, 0], label='Magnitude')
            self.ax4.plot(params.timeaxis, params.projy[:, 1], label='Real')
            self.ax4.plot(params.timeaxis, params.projy[:, 2], label='Imaginary')
            self.ax4.set_xlim([0, params.timeaxis[int(params.timeaxis.shape[0] - 1)]])
            self.ax4.set_title('Y - Signal')
            self.ax4.set_ylabel('RX Signal [mV]')
            self.ax4.set_xlabel('time [ms]')
            self.major_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) + 1)
            self.minor_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) * 5 + 1)
            self.ax4.set_xticks(self.major_ticks)
            self.ax4.set_xticks(self.minor_ticks, minor=True)
            self.ax4.grid(which='major', color='#888888', linestyle='-')
            self.ax4.grid(which='minor', color='#888888', linestyle=':')
            self.ax4.grid(which='both', visible=True)
            self.ax4.legend()
            self.ax4.plot(params.timeaxis, params.projy[:, 0], label='Magnitude')

        if params.projz.shape[0] == params.freqencyaxis.shape[0]:
            self.ax5 = self.fig.add_subplot(6, 1, 5)
            self.ax6 = self.fig.add_subplot(6, 1, 6)
            self.ax5.plot(params.freqencyaxis, params.projz[:, 3])
            self.ax5.set_xlim([-params.frequencyplotrange / 2, params.frequencyplotrange / 2])
            self.ax5.set_ylim([0, 1.1 * np.max(params.projz[:, 3])])
            self.ax5.set_title('Z - Spectrum')
            self.ax5.set_ylabel('RX Signal [arb.]')
            self.ax5.set_xlabel(r'$\Delta$ Frequency [Hz]')
            self.major_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 11)
            self.minor_ticks = np.linspace(-params.frequencyplotrange / 2, params.frequencyplotrange / 2, 51)
            self.ax5.set_xticks(self.major_ticks)
            self.ax5.set_xticks(self.minor_ticks, minor=True)
            self.ax5.grid(which='major', color='#888888', linestyle='-')
            self.ax5.grid(which='minor', color='#888888', linestyle=':')
            self.ax5.grid(which='both', visible=True)
            self.ax6.plot(params.timeaxis, params.projz[:, 0], label='Magnitude')
            self.ax6.plot(params.timeaxis, params.projz[:, 1], label='Real')
            self.ax6.plot(params.timeaxis, params.projz[:, 2], label='Imaginary')
            self.ax6.set_xlim([0, params.timeaxis[int(params.timeaxis.shape[0] - 1)]])
            self.ax6.set_title('Z - Signal')
            self.ax6.set_ylabel('RX Signal [mV]')
            self.ax6.set_xlabel('time [ms]')
            self.major_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) + 1)
            self.minor_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) * 5 + 1)
            self.ax6.set_xticks(self.major_ticks)
            self.ax6.set_xticks(self.minor_ticks, minor=True)
            self.ax6.grid(which='major', color='#888888', linestyle='-')
            self.ax6.grid(which='minor', color='#888888', linestyle=':')
            self.ax6.grid(which='both', visible=True)
            self.ax6.legend()
            self.ax6.plot(params.timeaxis, params.projz[:, 0], label='Magnitude')

        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 600, 950)
        self.fig_canvas.show()

        if os.path.isfile(params.datapath + '_0.txt') == True and os.path.isfile(params.datapath + '_2.txt') == True:

            self.projzx = np.matrix(np.zeros((params.projz.shape[0], params.projx.shape[0])))
            self.projzx = params.projx[:, 3] * np.transpose(params.projz[:, 3])

            self.IMag_fig = Figure()
            self.IMag_fig.set_facecolor('None')
            self.IMag_canvas = FigureCanvas(self.IMag_fig)

            self.IMag_ax = self.IMag_fig.add_subplot(111)
            self.IMag_ax.grid(False)
            if params.imagefilter == 1: self.IMag_ax.imshow(self.projzx[int(self.projzx.shape[0] / 2 - params.nPE / 2):int(self.projzx.shape[0] / 2 + params.nPE / 2), int(self.projzx.shape[1] / 2 - params.nPE / 2):int(self.projzx.shape[1] / 2 + params.nPE / 2)], interpolation='gaussian', cmap=params.imagecolormap)
            else: self.IMag_ax.imshow(self.projzx[int(self.projzx.shape[0] / 2 - params.nPE / 2):int(self.projzx.shape[0] / 2 + params.nPE / 2), int(self.projzx.shape[1] / 2 - params.nPE / 2):int(self.projzx.shape[1] / 2 + params.nPE / 2)], cmap=params.imagecolormap)
            self.IMag_ax.axis(False)
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')

            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(1030, 40, 550, 550)
            self.IMag_canvas.show()

    def T1_plot_init(self):
        self.fig1 = Figure()
        self.fig1.set_facecolor('None')
        self.fig_canvas1 = FigureCanvas(self.fig1)

        self.ax = self.fig1.add_subplot(111)

        self.ax.plot(params.T1xvalues, params.T1yvalues1, 'o', color='#000000', label='Measurement Data')
        self.ax.plot(params.T1xvalues, params.T1regyvalues1, color='#00BB00', label='Fit')
        self.ax.set_xlabel('TI')
        self.ax.set_ylabel('Signal')
        self.major_ticks = np.linspace(0, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) * 1000, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) + 1)
        self.minor_ticks = np.linspace(0, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) * 1000, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 200) + 1)
        self.ax.set_xticks(self.major_ticks)
        self.ax.set_xticks(self.minor_ticks, minor=True)
        self.ax.grid(which='major', color='#888888', linestyle='-')
        self.ax.grid(which='minor', color='#888888', linestyle=':')
        self.ax.grid(which='both', visible=True)
        self.ax.set_xlim((0, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) * 1000))
        #self.ax.set_ylim(0, 1.1 * np.max(params.T1yvalues1))
        self.ax.legend(loc='lower right')
        self.ax.set_title('T1 = ' + str(params.T1) + 'ms, r = ' + str(round(params.T1linregres.rvalue, 2)))

        self.fig_canvas1.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas1.setGeometry(420, 40, 575, 455)
        self.fig_canvas1.show()

        self.fig2 = Figure()
        self.fig2.set_facecolor('None')
        self.fig_canvas2 = FigureCanvas(self.fig2)

        self.ax = self.fig2.add_subplot(111)

        self.ax.plot(params.T1xvalues, params.T1yvalues2, 'o', color='#000000', label='Measurement Data')
        self.ax.plot(params.T1xvalues, params.T1regyvalues2, color='#00BB00', label='Fit')
        self.ax.set_xlabel('TI')
        self.ax.set_ylabel('ln(Signal_max - Signal)')
        self.major_ticks = np.linspace(0, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) * 1000, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) + 1)
        self.minor_ticks = np.linspace(0, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) * 1000, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 200) + 1)
        self.ax.set_xticks(self.major_ticks)
        self.ax.set_xticks(self.minor_ticks, minor=True)
        self.ax.grid(which='major', color='#888888', linestyle='-')
        self.ax.grid(which='minor', color='#888888', linestyle=':')
        self.ax.grid(which='both', visible=True)
        self.ax.set_xlim((0, math.ceil(params.T1xvalues[int(params.T1xvalues.shape[0] - 1)] / 1000) * 1000))
        self.ax.legend()
        self.ax.set_title('T1 = ' + str(params.T1) + 'ms, r = ' + str(round(params.T1linregres.rvalue, 2)))

        self.fig_canvas2.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas2.setGeometry(1005, 40, 575, 455)
        self.fig_canvas2.show()

    def T1_imaging_plot_init(self):
        self.IComb_fig = Figure()
        self.IComb_canvas = FigureCanvas(self.IComb_fig)
        self.IComb_fig.set_facecolor('None')
        self.IComb_ax = self.IComb_fig.add_subplot(111)
        self.IComb_ax.grid(False)
        if params.imagefilter == 1:
            self.IComb_ax.imshow(params.T1img_mag[params.T1img_mag.shape[0] - 1, :, :], interpolation='gaussian', cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T1imgvalues, interpolation='gaussian', cmap='jet', alpha=0.5)
        else:
            self.IComb_ax.imshow(params.T1img_mag[params.T1img_mag.shape[0] - 1, :, :], cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T1imgvalues, cmap='jet', alpha=0.5)
        self.IComb_ax.axis(False)
        self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
        self.IComb_ax.set_title('T1')
        self.IComb_fig.colorbar(self.cb, label='T1 in ms')
        self.IComb_canvas.draw()
        self.IComb_canvas.setWindowTitle('Plot - ' + params.datapath + '_Image_Magnitude.txt')
        self.IComb_canvas.setGeometry(420, 40, 800, 750)
        self.IComb_canvas.show()

    def T2_plot_init(self):
        self.fig = Figure()
        self.fig.set_facecolor('None')
        self.fig_canvas = FigureCanvas(self.fig)

        self.ax = self.fig.add_subplot(111)

        self.ax.plot(params.T2xvalues, params.T2yvalues, 'o', color='#000000', label='Measurement Data')
        self.ax.plot(params.T2xvalues, params.T2regyvalues, color='#00BB00', label='Fit')
        self.ax.set_xlabel('TE')
        self.ax.set_ylabel('ln(Signal)')
        self.major_ticks = np.linspace(0, math.ceil(params.T2xvalues[int(params.T2xvalues.shape[0] - 1)] / 1000) * 1000, math.ceil(params.T2xvalues[int(params.T2xvalues.shape[0] - 1)] / 1000) + 1)
        self.minor_ticks = np.linspace(0, math.ceil(params.T2xvalues[int(params.T2xvalues.shape[0] - 1)] / 1000) * 1000, math.ceil(params.T2xvalues[int(params.T2xvalues.shape[0] - 1)] / 200) + 1)
        self.ax.set_xticks(self.major_ticks)
        self.ax.set_xticks(self.minor_ticks, minor=True)
        self.ax.grid(which='major', color='#888888', linestyle='-')
        self.ax.grid(which='minor', color='#888888', linestyle=':')
        self.ax.grid(which='both', visible=True)
        self.ax.set_xlim((0, math.ceil(params.T2xvalues[int(params.T2xvalues.shape[0] - 1)] / 1000) * 1000))
        #self.ax.set_ylim(0, 1.1 * np.max(params.T2yvalues))
        self.ax.legend()
        self.ax.set_title('T2 = ' + str(params.T2) + 'ms, r = ' + str(round(params.T2linregres.rvalue, 2)))

        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 575, 455)
        self.fig_canvas.show()

    def T2_imaging_plot_init(self):
        self.IComb_fig = Figure()
        self.IComb_canvas = FigureCanvas(self.IComb_fig)
        self.IComb_fig.set_facecolor('None')
        self.IComb_ax = self.IComb_fig.add_subplot(111)
        self.IComb_ax.grid(False)
        if params.imagefilter == 1:
            self.IComb_ax.imshow(params.T2img_mag[0, :, :], interpolation='gaussian', cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T2imgvalues, interpolation='gaussian', cmap='jet', alpha=0.5)
        else:
            self.IComb_ax.imshow(params.T2img_mag[0, :, :], cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T2imgvalues, cmap='jet', alpha=0.5)
        self.IComb_ax.axis(False)
        self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
        self.IComb_ax.set_title('T2')
        self.IComb_fig.colorbar(self.cb, label='T2 in ms')
        self.IComb_canvas.draw()
        self.IComb_canvas.setWindowTitle('Plot - ' + params.datapath + '_Image_Magnitude.txt')
        self.IComb_canvas.setGeometry(420, 40, 800, 750)
        self.IComb_canvas.show()

    def imaging_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure()
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            self.IMag_fig.set_facecolor('None')
            self.IPha_fig = Figure()
            self.IPha_canvas = FigureCanvas(self.IPha_fig)
            self.IPha_fig.set_facecolor('None')
            self.kMag_fig = Figure()
            self.kMag_canvas = FigureCanvas(self.kMag_fig)
            self.kMag_fig.set_facecolor('None')
            self.kPha_fig = Figure()
            self.kPha_canvas = FigureCanvas(self.kPha_fig)
            self.kPha_fig.set_facecolor('None')

            self.IMag_ax = self.IMag_fig.add_subplot(111)
            self.IPha_ax = self.IPha_fig.add_subplot(111)
            
            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            else: self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)]);
            else: self.IPha_ax.imshow(params.img_pha, cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)]);    
                                                    
            if params.image_grid == 1:
                self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                
                self.IMag_ax.axis(True)
                self.IMag_ax.set_xticks(self.major_ticks)
                self.IMag_ax.set_yticks(self.major_ticks)
                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IMag_ax.grid(which='major', visible=True)
                
                self.IPha_ax.axis(True)
                self.IPha_ax.set_xticks(self.major_ticks)
                self.IPha_ax.set_yticks(self.major_ticks)
                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IPha_ax.grid(which='major', visible=True)
                
                if params.imageorientation == 'XY':
                    self.IMag_ax.set_xlabel('X in mm')
                    self.IMag_ax.set_ylabel('Y in mm')
                    self.IPha_ax.set_xlabel('X in mm')
                    self.IPha_ax.set_ylabel('Y in mm')
                elif params.imageorientation == 'YZ':
                    self.IMag_ax.set_xlabel('Y in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('Y in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                elif params.imageorientation == 'ZX':
                    self.IMag_ax.set_xlabel('Z in mm')
                    self.IMag_ax.set_ylabel('X in mm')
                    self.IPha_ax.set_xlabel('Z in mm')
                    self.IPha_ax.set_ylabel('X in mm')
                elif params.imageorientation == 'YX':
                    self.IMag_ax.set_xlabel('Y in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('Y in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                elif params.imageorientation == 'ZY':
                    self.IMag_ax.set_xlabel('Z in mm')
                    self.IMag_ax.set_ylabel('Y in mm')
                    self.IPha_ax.set_xlabel('Z in mm')
                    self.IPha_ax.set_ylabel('Y in mm')
                elif params.imageorientation == 'XZ':
                    self.IMag_ax.set_xlabel('X in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('X in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                    
            else:
                self.IMag_ax.axis(False)
                self.IMag_ax.grid(False)
                self.IPha_ax.axis(False)
                self.IPha_ax.grid(False)
                    
            if params.sequence == 17 or params.sequence == 19 or params.sequence == 21 \
                or params.sequence == 24 or params.sequence == 26 or params.sequence == 29 \
                or params.sequence == 32 or params.sequence == 34 or params.sequence == 18 \
                or params.sequence == 20 or params.sequence == 22 or params.sequence == 23 \
                or params.sequence == 25 or params.sequence == 27 or params.sequence == 28 \
                or params.sequence == 30 or params.sequence == 31 or params.sequence == 33 \
                or params.sequence == 35 or params.sequence == 36:
                if params.autofreqoffset == 1:
                    self.IMag_ax.set_title('Magnitude Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                else:
                    self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
            else:
                self.IMag_ax.set_title('Magnitude Image')
                self.IPha_ax.set_title('Phase Image')
            
            if params.projection3D == 1:
                self.kMag_ax = self.kMag_fig.add_subplot(111, projection='3d')
                
                if params.sequence == 0 or params.sequence == 1 or params.sequence == 17 or params.sequence == 18:
                    self.kspacestep = params.kspace.shape[1]/(params.nPE*params.radialosfactor)
                    self.radialangles = np.arange(0, 180, params.radialanglestep)

                    for n in range(params.kspace.shape[0]):
                        X = np.zeros(params.nPE*params.radialosfactor)
                        Y = np.zeros(params.nPE*params.radialosfactor)
                        Z = np.zeros(params.nPE*params.radialosfactor)
                        self.radialangleradmod100 = int((math.radians(self.radialangles[n]) % (2*np.pi))*100)
                        
                        for m in range(params.nPE*params.radialosfactor):
                            X[m] = params.nPE/2*params.radialosfactor + math.sin(self.radialangleradmod100/100)*(m-params.nPE/2*params.radialosfactor)
                            Y[m] = params.nPE/2*params.radialosfactor + math.cos(self.radialangleradmod100/100)*(m-params.nPE/2*params.radialosfactor)
                            
                            if params.lnkspacemag == 1: Z[m] = np.log(np.abs(params.kspace[n, int(m*self.kspacestep)]))
                            else: Z[m] = np.abs(params.kspace[n, int(m*self.kspacestep)])
                                
                        self.kMag_ax.plot(X, Y, Z, color='#000000', linewidth=0.5)
                        
                    if params.image_grid == 1:
                        self.kMag_ax.set(xlabel='',ylabel='', zlabel='Signal')
                            
                elif params.sequence == 2 or params.sequence == 3 or params.sequence == 19 or params.sequence == 20:
                    self.kspacestep = params.kspace.shape[1]/(params.nPE*params.radialosfactor)
                    self.radialangles = np.arange(0, 360, params.radialanglestep)
                    
                    for n in range(params.kspace.shape[0]):
                        X = np.zeros(params.nPE*params.radialosfactor)
                        Y = np.zeros(params.nPE*params.radialosfactor)
                        Z = np.zeros(params.nPE*params.radialosfactor)
                        self.radialangleradmod100 = int(math.radians(self.radialangles[n])*100)

                        for m in range(int(params.nPE*params.radialosfactor)):
                            X[m] = params.nPE*params.radialosfactor + math.cos(self.radialangleradmod100/100)*m
                            Y[m] = params.nPE*params.radialosfactor + math.sin(self.radialangleradmod100/100)*m
                            
                            if params.lnkspacemag == 1: Z[m] = np.log(np.abs(params.kspace[n, int(np.round(m*self.kspacestep))]))
                            else: Z[m] = np.abs(params.kspace[n, int(np.round(m*self.kspacestep))])
                        
                        self.kMag_ax.plot(X, Y, Z, color='#000000', linewidth=0.5)
                        
                    if params.image_grid == 1:
                        self.kMag_ax.set(xlabel='',ylabel='', zlabel='Signal')
                        
                else:
                    X = np.linspace(0, params.k_amp.shape[1]/250, num=params.k_amp.shape[1])

                    for n in range(params.k_amp.shape[0]):
                        Y = np.ones(params.k_amp.shape[1])
                        Y = Y * n
                        
                        Z = np.zeros(params.k_amp.shape[1])
                        if params.lnkspacemag == 1:
                            Z = np.log(params.k_amp[n, ])
                        else:
                            Z = params.k_amp[n, :]
                        
                        self.kMag_ax.plot(X, Y, Z, color='#000000', linewidth=0.5)

                    if params.image_grid == 1:
                        self.kMag_ax.set(xlabel='Time [ms]',ylabel='Phase Encoding Step', zlabel='Signal')
                        
                if params.lnkspacemag == 1:
                    self.kMag_ax.set_title('ln(k-Space Magnitude)')
                else:
                    self.kMag_ax.set_title('k-Space Magnitude')
                            
                if params.image_grid == 1:
                    self.kMag_ax.grid(True)
                else:
                    self.kMag_ax.axis(False)
                    self.kMag_ax.grid(False)
                    
            else:
                self.kMag_ax = self.kMag_fig.add_subplot(111)
                self.kMag_ax.grid(False)
                
                if params.lnkspacemag == 1:
                    self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno')
                    self.kMag_ax.set_title('ln(k-Space Magnitude)')
                else:
                    self.kMag_ax.imshow(params.k_amp, cmap='inferno')
                    self.kMag_ax.set_title('k-Space Magnitude')
                
                self.kMag_ax.axis(False)
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
            
            self.kPha_ax = self.kPha_fig.add_subplot(111)
            self.kPha_ax.grid(False)
            self.kPha_ax.imshow(params.k_pha, cmap='inferno')
            self.kPha_ax.axis(False)
            self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')

            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(420, 40, 575, 455)
            self.IPha_canvas.draw()
            self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IPha_canvas.setGeometry(1005, 40, 575, 455)
            self.kMag_canvas.draw()
            self.kMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.kMag_canvas.setGeometry(420, 535, 575, 455)
            self.kPha_canvas.draw()
            self.kPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.kPha_canvas.setGeometry(1005, 535, 575, 455)

            self.IMag_canvas.show()
            self.IPha_canvas.show()
            self.kMag_canvas.show()
            self.kPha_canvas.show()
            
        else:
            self.all_fig = Figure()
            self.all_canvas = FigureCanvas(self.all_fig)
            self.all_fig.set_facecolor('None')

            #gs = GridSpec(2, 2, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(221)
            self.IMag_ax.grid(False)
            self.IPha_ax = self.all_fig.add_subplot(222)
            self.IPha_ax.grid(False)
            
            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            else: self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)]);
            else: self.IPha_ax.imshow(params.img_pha, cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)]);    
                  
            if params.image_grid == 1:
                self.major_ticks = np.linspace(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)), math.floor((params.FOV / 2)) - math.ceil((-params.FOV / 2)) + 1)
                
                self.IMag_ax.axis(True)
                self.IMag_ax.set_xticks(self.major_ticks)
                self.IMag_ax.set_yticks(self.major_ticks)
                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IMag_ax.grid(which='major', visible=True)
                
                self.IPha_ax.axis(True)
                self.IPha_ax.set_xticks(self.major_ticks)
                self.IPha_ax.set_yticks(self.major_ticks)
                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IPha_ax.grid(which='major', visible=True)
                
                if params.imageorientation == 'XY':
                    self.IMag_ax.set_xlabel('X in mm')
                    self.IMag_ax.set_ylabel('Y in mm')
                    self.IPha_ax.set_xlabel('X in mm')
                    self.IPha_ax.set_ylabel('Y in mm')
                elif params.imageorientation == 'YZ':
                    self.IMag_ax.set_xlabel('Y in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('Y in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                elif params.imageorientation == 'ZX':
                    self.IMag_ax.set_xlabel('Z in mm')
                    self.IMag_ax.set_ylabel('X in mm')
                    self.IPha_ax.set_xlabel('Z in mm')
                    self.IPha_ax.set_ylabel('X in mm')
                elif params.imageorientation == 'YX':
                    self.IMag_ax.set_xlabel('Y in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('Y in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                elif params.imageorientation == 'ZY':
                    self.IMag_ax.set_xlabel('Z in mm')
                    self.IMag_ax.set_ylabel('Y in mm')
                    self.IPha_ax.set_xlabel('Z in mm')
                    self.IPha_ax.set_ylabel('Y in mm')
                elif params.imageorientation == 'XZ':
                    self.IMag_ax.set_xlabel('X in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('X in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                
            else:
                self.IMag_ax.axis(False)
                self.IPha_ax.axis(False)
            
            if params.sequence == 17 or params.sequence == 19 or params.sequence == 21 \
                or params.sequence == 24 or params.sequence == 26 or params.sequence == 29 \
                or params.sequence == 32 or params.sequence == 34 or params.sequence == 18 \
                or params.sequence == 20 or params.sequence == 22 or params.sequence == 23 \
                or params.sequence == 25 or params.sequence == 27 or params.sequence == 28 \
                or params.sequence == 30 or params.sequence == 31 or params.sequence == 33 \
                or params.sequence == 35 or params.sequence == 36:
                if params.autofreqoffset == 1:
                    self.IMag_ax.set_title('Magnitude Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                else:
                    self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
            else:
                self.IMag_ax.set_title('Magnitude Image')
                self.IPha_ax.set_title('Phase Image')
                
            if params.projection3D == 1:
                self.kMag_ax = self.all_fig.add_subplot(223, projection='3d')
                
                if params.sequence == 0 or params.sequence == 1 or params.sequence == 17 or params.sequence == 18:
                    self.kspacestep = params.kspace.shape[1]/(params.nPE*params.radialosfactor)
                    self.radialangles = np.arange(0, 180, params.radialanglestep)

                    for n in range(params.kspace.shape[0]):
                        X = np.zeros(params.nPE*params.radialosfactor)
                        Y = np.zeros(params.nPE*params.radialosfactor)
                        Z = np.zeros(params.nPE*params.radialosfactor)
                        self.radialangleradmod100 = int((math.radians(self.radialangles[n]) % (2*np.pi))*100)
                        
                        for m in range(params.nPE*params.radialosfactor):
                            X[m] = params.nPE/2*params.radialosfactor + math.sin(self.radialangleradmod100/100)*(m-params.nPE/2*params.radialosfactor)
                            Y[m] = params.nPE/2*params.radialosfactor + math.cos(self.radialangleradmod100/100)*(m-params.nPE/2*params.radialosfactor)
                            
                            if params.lnkspacemag == 1: Z[m] = np.log(np.abs(params.kspace[n, int(m*self.kspacestep)]))
                            else: Z[m] = np.abs(params.kspace[n, int(m*self.kspacestep)])
                                
                        self.kMag_ax.plot(X, Y, Z, color='#000000', linewidth=0.5)
                        
                    if params.image_grid == 1:
                        self.kMag_ax.set(xlabel='',ylabel='', zlabel='Signal')
                            
                elif params.sequence == 2 or params.sequence == 3 or params.sequence == 19 or params.sequence == 20:
                    self.kspacestep = params.kspace.shape[1]/(params.nPE*params.radialosfactor)
                    self.radialangles = np.arange(0, 360, params.radialanglestep)
                    
                    for n in range(params.kspace.shape[0]):
                        X = np.zeros(params.nPE*params.radialosfactor)
                        Y = np.zeros(params.nPE*params.radialosfactor)
                        Z = np.zeros(params.nPE*params.radialosfactor)
                        self.radialangleradmod100 = int(math.radians(self.radialangles[n])*100)

                        for m in range(int(params.nPE*params.radialosfactor)):
                            X[m] = params.nPE*params.radialosfactor + math.cos(self.radialangleradmod100/100)*m
                            Y[m] = params.nPE*params.radialosfactor + math.sin(self.radialangleradmod100/100)*m
                            
                            if params.lnkspacemag == 1: Z[m] = np.log(np.abs(params.kspace[n, int(np.round(m*self.kspacestep))]))
                            else: Z[m] = np.abs(params.kspace[n, int(np.round(m*self.kspacestep))])
                        
                        self.kMag_ax.plot(X, Y, Z, color='#000000', linewidth=0.5)
                        
                    if params.image_grid == 1:
                        self.kMag_ax.set(xlabel='',ylabel='', zlabel='Signal')
                        
                else:
                    X = np.linspace(0, params.k_amp.shape[1]/250, num=params.k_amp.shape[1])

                    for n in range(params.k_amp.shape[0]):
                        Y = np.ones(params.k_amp.shape[1])
                        Y = Y * n
                        
                        Z = np.zeros(params.k_amp.shape[1])
                        if params.lnkspacemag == 1:
                            Z = np.log(params.k_amp[n, ])
                        else:
                            Z = params.k_amp[n, :]
                        
                        self.kMag_ax.plot(X, Y, Z, color='#000000', linewidth=0.5)

                    if params.image_grid == 1:
                        self.kMag_ax.set(xlabel='Time [ms]',ylabel='Phase Encoding Step', zlabel='Signal')
                        
                if params.lnkspacemag == 1:
                    self.kMag_ax.set_title('ln(k-Space Magnitude)')
                else:
                    self.kMag_ax.set_title('k-Space Magnitude')
                            
                if params.image_grid == 1:
                    self.kMag_ax.grid(True)
                else:
                    self.kMag_ax.axis(False)
                    self.kMag_ax.grid(False)
                    
            else:
                self.kMag_ax = self.all_fig.add_subplot(223)
                self.kMag_ax.grid(False)
                
                if params.lnkspacemag == 1:
                    self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno')
                    self.kMag_ax.set_title('ln(k-Space Magnitude)')
                else:
                    self.kMag_ax.imshow(params.k_amp, cmap='inferno')
                    self.kMag_ax.set_title('k-Space Magnitude')	
                
                self.kMag_ax.axis(False)
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
            
            self.kPha_ax = self.all_fig.add_subplot(224)
            self.kPha_ax.grid(False)
            
            self.kPha_ax.imshow(params.k_pha, cmap='inferno')
            self.kPha_ax.axis(False)
            self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1160, 950)
            self.all_canvas.show()

    def imaging_stitching_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure()
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            self.IMag_fig.set_facecolor('None')
            self.IPha_fig = Figure()
            self.IPha_canvas = FigureCanvas(self.IPha_fig)
            self.IPha_fig.set_facecolor('None')
                
            if params.imageorientation == 'XY' or params.imageorientation == 'ZY' or params.imageorientation == 'YZ' or params.imageorientation == 'YX':
                self.IMag_ax = self.IMag_fig.add_subplot(111)
                self.IMag_ax.grid(False)
                self.IPha_ax = self.IPha_fig.add_subplot(111)
                self.IPha_ax.grid(False)
                
                self.FOV_1 = 0
                self.FOV_2 = 0
                self.FOV_2_start = 0
                self.FOV_2_end = 0
                
                if params.imageorientation == 'XY' or params.imageorientation == 'ZY':
                    self.FOV_1 = params.FOV
                    if params.motor_movement_step <= params.FOV:
                        self.FOV_2 = params.motor_total_image_length + params.motor_movement_step
                        self.FOV_2_start = params.motor_start_position - params.motor_movement_step/2
                        self.FOV_2_end = params.motor_end_position + params.motor_movement_step/2
                    else:
                        self.FOV_2 = params.motor_total_image_length + params.FOV
                        self.FOV_2_start = params.motor_start_position - params.FOV/2
                        self.FOV_2_end = params.motor_end_position + params.FOV/2
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    else: self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    else: self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    
                    if params.image_grid == 1:
                        if self.FOV_2 <= 20:
                            self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 1, 1)
                            self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 1, 1)
                        elif self.FOV_2 > 20 and self.FOV_2 <= 50:
                            self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 2, 2)
                            self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 2, 2)
                        else:
                            self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 4, 4)
                            self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 5, 5)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.x_major_ticks)
                        self.IPha_ax.set_yticks(self.y_major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'XY':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Y$_{PB}$ in mm')
                        elif params.imageorientation == 'ZY':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('Y$_{PB}$ in mm')
                        
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')
                        
                elif params.imageorientation == 'YZ' or params.imageorientation == 'YX':
                    if params.motor_movement_step <= params.FOV:
                        self.FOV_1 = params.motor_total_image_length + params.motor_movement_step
                        self.FOV_1_start = params.motor_start_position - params.motor_movement_step/2
                        self.FOV_1_end = params.motor_end_position + params.motor_movement_step/2
                    else:
                        self.FOV_1 = params.motor_total_image_length + params.FOV
                        self.FOV_1_start = params.motor_start_position - params.FOV/2
                        self.FOV_1_end = params.motor_end_position + params.FOV/2
                    self.FOV_2 = params.FOV
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    else: self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    else: self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    
                    if params.image_grid == 1:
                        if self.FOV_1 <= 20:
                            self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 1, 1)
                            self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 1, 1)
                        elif self.FOV_1 > 20 and self.FOV_1 <= 50:
                            self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 2, 2)
                            self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 2, 2)
                        else:
                            self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 5, 5)
                            self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 4, 4)
                                            
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.x_major_ticks)
                        self.IPha_ax.set_yticks(self.y_major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'YX':
                            self.IMag_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IMag_ax.set_ylabel('X in mm')
                            self.IPha_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_ylabel('X in mm')
                        elif params.imageorientation == 'YZ':
                            self.IMag_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')
                        
                if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                    or params.sequence == 8 or params.sequence == 9:
                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
                else:
                    self.IMag_ax.set_title('Magnitude Image')
                    self.IPha_ax.set_title('Phase Image')
                    
                self.IMag_canvas.draw()
                self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.IMag_canvas.setGeometry(420, 40, 575, 470)
                self.IPha_canvas.draw()
                self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.IPha_canvas.setGeometry(1005, 40, 575, 470)

                self.IMag_canvas.show()
                self.IPha_canvas.show()
                
            elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                self.image_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
                
                if params.projection3D == 1:
                    self.IMag_ax = self.IMag_fig.add_subplot(111, projection='3d')
                    self.IMag_ax.grid(False)
                    
                    if params.projection3D_quality == 1:
#                         #Contour Filled Plot
#                         self.img_st_mag_cut_1 = np.array(np.zeros((params.nPE, params.nPE)))
#                         self.img_st_mag_cut_1_norm = np.array(np.zeros((params.nPE, params.nPE)))
#                         self.img_st_mag_cut_2 = np.array(np.zeros((params.nPE, params.nPE)))
#                        
#                         X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(-params.FOV/2, params.FOV/2, params.nPE))
#                         
#                         levels= np.linspace(params.imageminimum-1e-6, params.imagemaximum, 50)
#                         colors_1 = plt.get_cmap(params.imagecolormap)(np.linspace(0, 1, len(levels)-1))
#                         if params.imageminimum > params.img_st_mag.min():
#                             colors_1[levels[:-1] <= params.imageminimum, 3] = 0
#                             
#                         for n in range(params.motor_image_count):
#                             self.img_st_mag_cut_1 = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
#                             self.img_st_mag_cut_1[self.img_st_mag_cut_1 > params.imagemaximum] = params.imagemaximum
#                             self.img_st_mag_cut_1[self.img_st_mag_cut_1 < params.imageminimum] = params.imageminimum-1e-6
#                             self.img_st_mag_cut_2 = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
#                             self.img_st_mag_cut_2[self.img_st_mag_cut_2 > params.imagemaximum] = params.imagemaximum-1e-6
# 
#                             self.img_st_mag_cut_1_norm = (self.img_st_mag_cut_1 - params.imageminimum-1e-6) / (params.imagemaximum - params.imageminimum-1e-6)
#                                                         
#                             if params.imagefilter == 1: self.IMag_ax.contourf(self.img_st_mag_cut_2, Z, X, zdir='x', offset=self.image_positions[n], levels=levels, colors=colors_1, antialiased=True, extend='neither')
#                             else: self.IMag_ax.contourf(self.img_st_mag_cut_2, Z, X, zdir='x', offset=self.image_positions[n], levels=levels, colors=colors_1, antialiased=False, extend='neither')
# 
#                         self.IMag_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
#                         self.IMag_ax.set_xlim([params.motor_start_position, params.motor_end_position])
#                         
#                         del self.img_st_mag_cut_1, self.img_st_mag_cut_1_norm, self.img_st_mag_cut_2, X, Z, levels, colors_1
                        
                        #Surface Plot
                        self.img_st_mag_cut_1 = np.array(np.zeros((params.nPE, params.nPE)))
                        self.img_st_mag_cut_1_norm = np.array(np.zeros((params.nPE, params.nPE)))
                        self.img_st_mag_cut_2 = np.array(np.zeros((params.nPE, params.nPE)))
                       
                        X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE+1),np.linspace(params.FOV/2, -params.FOV/2, params.nPE+1))
                        
                        for n in range(params.motor_image_count):
                            self.img_st_mag_cut_1[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
                            self.img_st_mag_cut_1[self.img_st_mag_cut_1 > params.imagemaximum] = params.imagemaximum
                            self.img_st_mag_cut_1[self.img_st_mag_cut_1 < params.imageminimum] = params.imageminimum
                            self.img_st_mag_cut_2[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
                            self.img_st_mag_cut_2[self.img_st_mag_cut_2 > params.imagemaximum] = params.imagemaximum
                            
                            Y = np.full_like(X, self.image_positions[n])
                            
                            self.img_st_mag_cut_1_norm = (self.img_st_mag_cut_1 - params.imageminimum) / (params.imagemaximum - params.imageminimum)
                            
                            colors_2 = plt.get_cmap(params.imagecolormap)(np.clip(self.img_st_mag_cut_1_norm, 0, 1))
                            colors_2[self.img_st_mag_cut_2 < params.imageminimum, 3] = 0
                            
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_2, antialiased=False, shade=False, edgecolor='none')
                            
                        self.IMag_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
                        self.IMag_ax.set_xlim([params.motor_start_position, params.motor_end_position])
                        
                        del self.img_st_mag_cut_1, self.img_st_mag_cut_1_norm, self.img_st_mag_cut_2, X, Y, Z, colors_2
                         
#                         #Voxel Plot
#                         self.img_st_mag_cut_1 = np.array(np.zeros((params.motor_image_count, params.nPE, params.nPE)))
#                         self.img_st_mag_cut_1_norm = np.array(np.zeros((params.motor_image_count, params.nPE, params.nPE)))
#                         self.img_st_mag_cut_2 = np.array(np.zeros((params.motor_image_count, params.nPE, params.nPE)))
#                         
#                         for n in range(params.motor_image_count):
#                             self.img_st_mag_cut_1[n, :, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
#                             self.img_st_mag_cut_2[n, :, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
#                             
#                         
#                         self.img_st_mag_cut_1[self.img_st_mag_cut_1 > params.imagemaximum] = params.imagemaximum
#                         self.img_st_mag_cut_1[self.img_st_mag_cut_1 < params.imageminimum] = params.imageminimum
#                         self.img_st_mag_cut_1[self.img_st_mag_cut_2 > params.imagemaximum] = params.imagemaximum
#                               
#                         x_edges = np.linspace(-params.FOV/2, params.FOV/2, self.img_st_mag_cut_2.shape[1]+1)
#                         y_edges = np.linspace(params.motor_start_position - params.slicethickness/2, params.motor_end_position + params.slicethickness/2, self.img_st_mag_cut_2.shape[0]+1)
#                         z_edges = np.linspace(-params.FOV/2, params.FOV/2, self.img_st_mag_cut_2.shape[2]+1)
#                                                 
#                         Y, Z, X = np.meshgrid(y_edges, z_edges, x_edges, indexing='ij')
#                         
#                         self.img_st_mag_cut_1_norm = (self.img_st_mag_cut_1 - params.imageminimum) / (params.imagemaximum - params.imageminimum)
#                         
#                         colors_3 = plt.get_cmap(params.imagecolormap)(np.clip(self.img_st_mag_cut_1_norm, 0, 1))
#                         colors_3[..., 3] = 0.2
#                         colors_3[self.img_st_mag_cut_2 < params.imageminimum, 3] = 0
#                         
#                         self.IMag_ax.voxels(Y, Z, X, self.img_st_mag_cut_1_norm, facecolors=colors_3, shade=False, edgecolor='none')
#                        
#                         self.IMag_ax.set_box_aspect([(params.motor_total_image_length + params.slicethickness)/params.FOV, 1, 1])
#                         self.IMag_ax.set_xlim([params.motor_start_position - params.slicethickness/2, params.motor_end_position + params.slicethickness/2])
#                         
#                         del self.img_st_mag_cut_1, self.img_st_mag_cut_1_norm, self.img_st_mag_cut_2, X, Y, Z, colors_3
                        
                    else:
                        #Contour Plot
                        self.img_st_mag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                        
                        X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        
                        levels = np.linspace(params.imageminimum, params.imagemaximum, 10)
                        
                        for n in range(params.motor_image_count):
                            self.img_st_mag_cut[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
                            
                            self.IMag_ax.contour(self.img_st_mag_cut, Z, X, zdir='x', offset=self.image_positions[n], levels=levels, cmap=params.imagecolormap, extend='neither')
                        
                        self.IMag_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
                        self.IMag_ax.set_xlim([params.motor_start_position, params.motor_end_position])
                        
                        del self.img_st_mag_cut, X, Z, levels
                    
                    if params.image_grid == 1:
                        if params.motor_total_image_length <= 20:
                            self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 1, 1)
                            self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 1, 1)
                        elif params.motor_total_image_length > 20 and params.motor_total_image_length <= 50:
                            self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 2, 2)
                            self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 2, 2)
                        else:
                            self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 5, 5)
                            self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 4, 4)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        self.IMag_ax.grid(True)
                        
                        if params.imageorientation == 'ZX':
                            self.IMag_ax.set(xlabel='\n\nY$_{PB}$',ylabel='Z', zlabel='X')
                        elif params.imageorientation == 'XZ':
                            self.IMag_ax.set(xlabel='\n\nY$_{PB}$',ylabel='X', zlabel='Z')
                    else:
                        self.IMag_ax.axis('off')
                        

                    #self.IMag_fig.patch.set_facecolor('black')
                    #self.IMag_fig.set_facecolor('black')
                    #self.IMag_ax.set_facecolor('black')
                    #self.IMag_ax.xaxis.set_pane_color((0, 0, 0, 1))
                    #self.IMag_ax.yaxis.set_pane_color((0, 0, 0, 1))
                    #self.IMag_ax.zaxis.set_pane_color((0, 0, 0, 1))
                    #self.IMag_ax.tick_params(axis='both', colors='white')
                    #self.IMag_ax.xaxis.label.set_color('white')
                    #self.IMag_ax.yaxis.label.set_color('white')
                    #self.IMag_ax.zaxis.label.set_color('white')
                    #self.IMag_ax.grid(True, color='white')
                    
                    self.IMag_canvas.draw()
                    self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                    self.IMag_canvas.setGeometry(420, 40, 1160, 950)
                    self.IMag_canvas.show()
                        
                else:
                    if params.motor_image_count > 6:
                        gs_IMag = GridSpec(int(np.ceil(params.motor_image_count/6)), 6, figure=self.IMag_fig)
                        gs_IPha = GridSpec(int(np.ceil(params.motor_image_count/6)), 6, figure=self.IPha_fig)
                        
                        for m in range(int(np.ceil(params.motor_image_count/6))):
                            for n in range(6):
                                if m*6 + n < params.motor_image_count:
                                    self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[m, n])
                                    self.IMag_ax.grid(False)
                                    self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[m, n])
                                    self.IPha_ax.grid(False)
                                    
                                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                    else: self.IMag_ax.imshow(params.img_st_mag[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                    else: self.IPha_ax.imshow(params.img_st_pha[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                           
                                    if params.image_grid == 1:
                                        self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                                        
                                        self.IMag_ax.axis('on')
                                        self.IMag_ax.set_xticks(self.major_ticks)
                                        self.IMag_ax.set_yticks(self.major_ticks)
                                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                        self.IMag_ax.grid(which='major', visible=True)
                                        
                                        self.IPha_ax.axis('on')
                                        self.IPha_ax.set_xticks(self.major_ticks)
                                        self.IPha_ax.set_yticks(self.major_ticks)
                                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                        self.IPha_ax.grid(which='major', visible=True)
                      
                                        if params.imageorientation == 'ZX':
                                            self.IMag_ax.set_xlabel('Z in mm')
                                            self.IMag_ax.set_ylabel('X in mm')
                                            self.IPha_ax.set_xlabel('Z in mm')
                                            self.IPha_ax.set_ylabel('X in mm')
                                        elif params.imageorientation == 'XZ':
                                            self.IMag_ax.set_xlabel('X in mm')
                                            self.IMag_ax.set_ylabel('Z in mm')
                                            self.IPha_ax.set_xlabel('X in mm')
                                            self.IPha_ax.set_ylabel('Z in mm')
                                            
                                    else:
                                        self.IMag_ax.axis('off')
                                        self.IPha_ax.axis('off')
                                      
                                    if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                                        or params.sequence == 8 or params.sequence == 9:
                                        if params.autofreqoffset == 1:
                                            self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[(m*6+n)] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                            self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[(m*6+n)] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                        else:
                                            self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                                            self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
                                    else:
                                        self.IMag_ax.set_title('Magnitude Image')
                                        self.IPha_ax.set_title('Phase Image')
                    else:
                        gs_IMag = GridSpec(1, params.motor_image_count, figure=self.IMag_fig)
                        gs_IPha = GridSpec(1, params.motor_image_count, figure=self.IPha_fig)
                        
                        for n in range(params.motor_image_count):
                            self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[0, n])
                            self.IMag_ax.grid(False)
                            self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[0, n])
                            self.IPha_ax.grid(False)
                            
                            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            else: self.IMag_ax.imshow(params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, n*params.nPE:(n+1)*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            else: self.IPha_ax.imshow(params.img_st_pha[:, n*params.nPE:(n+1)*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            
                            if params.image_grid == 1:
                                self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                                
                                self.IMag_ax.axis('on')
                                self.IMag_ax.set_xticks(self.major_ticks)
                                self.IMag_ax.set_yticks(self.major_ticks)
                                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IMag_ax.grid(which='major', visible=True)
                                
                                self.IPha_ax.axis('on')
                                self.IPha_ax.set_xticks(self.major_ticks)
                                self.IPha_ax.set_yticks(self.major_ticks)
                                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IPha_ax.grid(which='major', visible=True)
              
                                if params.imageorientation == 'ZX':
                                    self.IMag_ax.set_xlabel('Z in mm')
                                    self.IMag_ax.set_ylabel('X in mm')
                                    self.IPha_ax.set_xlabel('Z in mm')
                                    self.IPha_ax.set_ylabel('X in mm')
                                elif params.imageorientation == 'XZ':
                                    self.IMag_ax.set_xlabel('X in mm')
                                    self.IMag_ax.set_ylabel('Z in mm')
                                    self.IPha_ax.set_xlabel('X in mm')
                                    self.IPha_ax.set_ylabel('Z in mm')
                                    
                            else:
                                self.IMag_ax.axis('off')
                                self.IPha_ax.axis('off')
                    
                            if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                                or params.sequence == 8 or params.sequence == 9:
                                if params.autofreqoffset == 1:
                                    self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                    self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                else:
                                    self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                                    self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
                            else:
                                self.IMag_ax.set_title('Magnitude Image')
                                self.IPha_ax.set_title('Phase Image')
            
                    self.IMag_canvas.draw()
                    self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                    self.IMag_canvas.setGeometry(420, 40, 575, 470)
                    self.IPha_canvas.draw()
                    self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                    self.IPha_canvas.setGeometry(1005, 40, 575, 470)

                    self.IMag_canvas.show()
                    self.IPha_canvas.show()

        else:
            self.all_fig = Figure()
            self.all_canvas = FigureCanvas(self.all_fig)
            self.all_fig.set_facecolor('None')
            
            if params.imageorientation == 'XY' or params.imageorientation == 'ZY':
                gs = GridSpec(1, 2, figure=self.all_fig)
                self.IMag_ax = self.all_fig.add_subplot(gs[0, 0])
                self.IMag_ax.grid(False)
                self.IPha_ax = self.all_fig.add_subplot(gs[0, 1])
                self.IPha_ax.grid(False)
                
                self.FOV_1 = 0
                self.FOV_2 = 0
                self.FOV_2_start = 0
                self.FOV_2_end = 0
                
                self.FOV_1 = params.FOV
                if params.motor_movement_step <= params.FOV:
                    self.FOV_2 = params.motor_total_image_length + params.motor_movement_step
                    self.FOV_2_start = params.motor_start_position - params.motor_movement_step/2
                    self.FOV_2_end = params.motor_end_position + params.motor_movement_step/2
                else:
                    self.FOV_2 = params.motor_total_image_length + params.FOV
                    self.FOV_2_start = params.motor_start_position - params.FOV/2
                    self.FOV_2_end = params.motor_end_position + params.FOV/2
                    
                if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                else: self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                else: self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])

                if params.image_grid == 1:
                    if self.FOV_2 <= 20:
                        self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 1, 1)
                        self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 1, 1)
                    elif self.FOV_2 > 20 and self.FOV_2 <= 50:
                        self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 2, 2)
                        self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 2, 2)
                    else:
                        self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 4, 4)
                        self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 5, 5) 
                    
                    self.IMag_ax.axis('on')
                    self.IMag_ax.set_xticks(self.x_major_ticks)
                    self.IMag_ax.set_yticks(self.y_major_ticks)
                    self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.IMag_ax.grid(which='major', visible=True)
                    
                    self.IPha_ax.axis('on')
                    self.IPha_ax.set_xticks(self.x_major_ticks)
                    self.IPha_ax.set_yticks(self.y_major_ticks)
                    self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.IPha_ax.grid(which='major', visible=True)
                    
                    if params.imageorientation == 'XY':
                        self.IMag_ax.set_xlabel('X in mm')
                        self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                        self.IMag_ax.set_xlabel('X in mm')
                        self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                    elif params.imageorientation == 'ZY':
                        self.IMag_ax.set_xlabel('Z in mm')
                        self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                        self.IMag_ax.set_xlabel('Z in mm')
                        self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                        
                else:
                    self.IMag_ax.axis('off')
                    self.IPha_ax.axis('off')
                
            elif params.imageorientation == 'YZ' or params.imageorientation == 'YX':
                gs = GridSpec(2, 1, figure=self.all_fig)
                self.IMag_ax = self.all_fig.add_subplot(gs[0, 0])
                self.IMag_ax.grid(False)
                self.IPha_ax = self.all_fig.add_subplot(gs[1, 0])
                self.IPha_ax.grid(False)
                
                self.FOV_1 = 0
                self.FOV_2 = 0
                self.FOV_2_start = 0
                self.FOV_2_end = 0
                
                if params.motor_movement_step <= params.FOV:
                    self.FOV_1 = params.motor_total_image_length + params.motor_movement_step
                    self.FOV_1_start = params.motor_start_position - params.motor_movement_step/2
                    self.FOV_1_end = params.motor_end_position + params.motor_movement_step/2
                else:
                    self.FOV_1 = params.motor_total_image_length + params.FOV
                    self.FOV_1_start = params.motor_start_position - params.FOV/2
                    self.FOV_1_end = params.motor_end_position + params.FOV/2
                self.FOV_2 = params.FOV
                
                if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                else: self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                else: self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    
                if params.image_grid == 1:
                    if self.FOV_1 <= 20:
                        self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 1, 1)
                        self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 1, 1)
                    elif self.FOV_1 > 20 and self.FOV_1 <= 50:
                        self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 1, 2)
                        self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 1, 2)
                    else:
                        self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 1, 5)
                        self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 1, 4)
                    
                    self.IMag_ax.axis('on')
                    self.IMag_ax.set_xticks(self.x_major_ticks)
                    self.IMag_ax.set_yticks(self.y_major_ticks)
                    self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.IMag_ax.grid(which='major', visible=True)
                    
                    self.IPha_ax.axis('on')
                    self.IPha_ax.set_xticks(np.flip(self.x_major_ticks))
                    self.IPha_ax.set_yticks(self.y_major_ticks)
                    self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.IPha_ax.grid(which='major', visible=True)
                    
                    if params.imageorientation == 'YZ':
                        self.IMag_ax.set_xlabel('Y$_{PB}$ in mm')
                        self.IMag_ax.set_ylabel('Z in mm')
                        self.IPha_ax.set_xlabel('Y$_{PB}$ in mm')
                        self.IPha_ax.set_ylabel('Z in mm')
                    elif params.imageorientation == 'YX':
                        self.IMag_ax.set_xlabel('Y$_{PB}$ in mm')
                        self.IMag_ax.set_ylabel('X in mm')
                        self.IPha_ax.set_xlabel('Y$_{PB}$ in mm')
                        self.IPha_ax.set_ylabel('X in mm')
                        
                else:
                    self.IMag_ax.axis('off')
                    self.IPha_ax.axis('off')
                        
                if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                    or params.sequence == 8 or params.sequence == 9:
                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
                else:
                    self.IMag_ax.set_title('Magnitude Image')
                    self.IPha_ax.set_title('Phase Image')

                self.all_canvas.draw()
                self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.all_canvas.setGeometry(420, 40, 1160, 950)
                self.all_canvas.show()
                
            elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                self.image_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
                
                if params.projection3D == 1:
                    self.IMag_ax = self.all_fig.add_subplot(111, projection='3d')
                    self.IMag_ax.grid(False)
                    
                    if params.projection3D_quality == 1:
                        #Surface Plot
                        self.img_st_mag_cut_1 = np.array(np.zeros((params.nPE, params.nPE)))
                        self.img_st_mag_cut_1_norm = np.array(np.zeros((params.nPE, params.nPE)))
                        self.img_st_mag_cut_2 = np.array(np.zeros((params.nPE, params.nPE)))
                       
                        X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE+1),np.linspace(params.FOV/2, -params.FOV/2, params.nPE+1))
                        
                        for n in range(params.motor_image_count):
                            self.img_st_mag_cut_1[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
                            self.img_st_mag_cut_1[self.img_st_mag_cut_1 > params.imagemaximum] = params.imagemaximum
                            self.img_st_mag_cut_1[self.img_st_mag_cut_1 < params.imageminimum] = params.imageminimum
                            self.img_st_mag_cut_2[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
                            self.img_st_mag_cut_2[self.img_st_mag_cut_2 > params.imagemaximum] = params.imagemaximum
                            
                            Y = np.full_like(X, self.image_positions[n])
                            
                            self.img_st_mag_cut_1_norm = (self.img_st_mag_cut_1 - params.imageminimum) / (params.imagemaximum - params.imageminimum)
                            
                            colors_2 = plt.get_cmap(params.imagecolormap)(np.clip(self.img_st_mag_cut_1_norm, 0, 1))
                            colors_2[self.img_st_mag_cut_2 < params.imageminimum, 3] = 0
                            
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_2, antialiased=False, shade=False, edgecolor='none')
                            
                        self.IMag_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
                        self.IMag_ax.set_xlim([params.motor_start_position, params.motor_end_position])
                        
                        del self.img_st_mag_cut_1, self.img_st_mag_cut_1_norm, self.img_st_mag_cut_2, X, Y, Z, colors_2
                        
                    else:
                        #Contour Plot
                        self.img_st_mag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                        
                        X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        
                        levels = np.linspace(params.imageminimum, params.imagemaximum, 10)
                        
                        for n in range(params.motor_image_count):
                            self.img_st_mag_cut[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
                            
                            self.IMag_ax.contour(self.img_st_mag_cut, Z, X, zdir='x', offset=self.image_positions[n], levels=levels, cmap=params.imagecolormap, extend='neither')
                        
                        self.IMag_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
                        self.IMag_ax.set_xlim([params.motor_start_position, params.motor_end_position])
                        
                        del self.img_st_mag_cut, X, Z, levels
                    
                    if params.image_grid == 1:
                        if params.motor_total_image_length <= 20:
                            self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 1, 1)
                            self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 1, 1)
                        elif params.motor_total_image_length > 20 and params.motor_total_image_length <= 50:
                            self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 2, 2)
                            self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 2, 2)
                        else:
                            self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 5, 5)
                            self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 4, 4)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        self.IMag_ax.grid(True)
                        
                        if params.imageorientation == 'ZX':
                            self.IMag_ax.set(xlabel='Y$_{PB}$',ylabel='Z', zlabel='X')
                        elif params.imageorientation == 'XZ':
                            self.IMag_ax.set(xlabel='Y$_{PB}$',ylabel='X', zlabel='Z')
                    else:
                        self.IMag_ax.axis('off')
                        
#                 if params.projection3D == 1:
#                     self.IMag_ax = self.all_fig.add_subplot(121, projection='3d')
#                     self.IMag_ax.grid(False)
#                     self.IPha_ax = self.all_fig.add_subplot(122, projection='3d')
#                     self.IPha_ax.grid(False)
#                     
#                     self.img_st_mag_cut_1 = np.array(np.zeros((params.nPE, params.nPE)))
#                     self.img_st_mag_cut_2 = np.array(np.zeros((params.nPE, params.nPE)))
#                     self.img_st_pha_cut = np.array(np.zeros((params.nPE, params.nPE)))
#                    
#                     X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(-params.FOV/2, params.FOV/2, params.nPE))
#                     
#                     for n in range(params.motor_image_count):
#                         self.img_st_mag_cut_1[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE]
#                         self.img_st_mag_cut_1[self.img_st_mag_cut_1 < params.imageminimum] = np.nan
#                         self.img_st_mag_cut_2[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE]
#                         self.img_st_mag_cut_2[self.img_st_mag_cut_2 < params.imageminimum] = params.imageminimum
#                         self.img_st_pha_cut[:, :] = params.img_st_pha[:, n*params.nPE:(n+1)*params.nPE]
#                         
#                         Y = np.full_like(X, self.image_positions[n])
#                         Y[np.isnan(self.img_st_mag_cut_1)] = np.nan
#                         Y = np.rot90(Y, 3)
# 
#                         colors_1 = plt.get_cmap(params.imagecolormap)((np.rot90(self.img_st_mag_cut_2, 3) - params.imageminimum)/(params.imagemaximum - params.imageminimum))
#                         colors_2 = plt.get_cmap('gray')(np.rot90(self.img_st_pha_cut, 3))
#                         
#                         self.IMag_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_1, antialiased=False, linewidth=0)
#                         self.IPha_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_2, antialiased=False, linewidth=0)
# 
#                     self.IMag_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
#                     self.IMag_ax.set_xlim([params.motor_start_position, params.motor_end_position])
#                     
#                     self.IPha_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
#                     self.IPha_ax.set_xlim([params.motor_start_position, params.motor_end_position])
#                     
#                     if params.image_grid == 1:
#                         self.IMag_ax.grid(True)
#                         self.IPha_ax.grid(True)
#                         if params.imageorientation == 'ZX':
#                             self.IMag_ax.set(xlabel='Y',ylabel='Z', zlabel='X')
#                         elif params.imageorientation == 'XZ':
#                             self.IMag_ax.set(xlabel='Y',ylabel='X', zlabel='Z')
#                     else:
#                         self.IMag_ax.axis('off')
#                         self.IPha_ax.axis('off')
                    
                else:
                    if params.motor_image_count > 6:
                        gs = GridSpec(int(2 * np.ceil(params.motor_image_count/6)), 6, figure=self.all_fig)
                        
                        for m in range(int(np.ceil(params.motor_image_count/6))):
                            for n in range(6):
                                if m*6 + n < params.motor_image_count:
                                    self.IMag_ax = self.all_fig.add_subplot(gs[m, n])
                                    self.IMag_ax.grid(False)
                                    self.IPha_ax = self.all_fig.add_subplot(gs[int(m + np.ceil(params.motor_image_count/6)), n])
                                    self.IPha_ax.grid(False)
                                    
                                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                    else: self.IMag_ax.imshow(params.img_st_mag[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                    else: self.IPha_ax.imshow(params.img_st_pha[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])       
                                    
                                    if params.image_grid == 1:
                                        self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                                        
                                        self.IMag_ax.axis('on')
                                        self.IMag_ax.set_xticks(self.major_ticks)
                                        self.IMag_ax.set_yticks(self.major_ticks)
                                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                        self.IMag_ax.grid(which='major', visible=True)
                                        
                                        self.IPha_ax.axis('on')
                                        self.IPha_ax.set_xticks(self.major_ticks)
                                        self.IPha_ax.set_yticks(self.major_ticks)
                                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                        self.IPha_ax.grid(which='major', visible=True)
                      
                                        if params.imageorientation == 'ZX':
                                            self.IMag_ax.set_xlabel('Z in mm')
                                            self.IMag_ax.set_ylabel('X in mm')
                                            self.IPha_ax.set_xlabel('Z in mm')
                                            self.IPha_ax.set_ylabel('X in mm')
                                        elif params.imageorientation == 'XZ':
                                            self.IMag_ax.set_xlabel('X in mm')
                                            self.IMag_ax.set_ylabel('Z in mm')
                                            self.IPha_ax.set_xlabel('X in mm')
                                            self.IPha_ax.set_ylabel('Z in mm')
                                            
                                    else:
                                        self.IMag_ax.axis('off')
                                        self.IPha_ax.axis('off')
                            
                                    if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                                        or params.sequence == 8 or params.sequence == 9:
                                        if params.autofreqoffset == 1:
                                            self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[(m*6+n)] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                            self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[(m*6+n)] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                        else:
                                            self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                                            self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
                                    else:
                                        self.IMag_ax.set_title('Magnitude Image')
                                        self.IPha_ax.set_title('Phase Image')
                
                    else:
                        gs = GridSpec(2, params.motor_image_count, figure=self.all_fig)
                        
                        for n in range(params.motor_image_count):
                            self.IMag_ax = self.all_fig.add_subplot(gs[0, n])
                            self.IMag_ax.grid(False)
                            self.IPha_ax = self.all_fig.add_subplot(gs[1, n])
                            self.IPha_ax.grid(False)
                            
                            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            else: self.IMag_ax.imshow(params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, n*params.nPE:(n+1)*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            else: self.IPha_ax.imshow(params.img_st_pha[:, n*params.nPE:(n+1)*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                    
                            
                            if params.image_grid == 1:
                                self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                                
                                self.IMag_ax.axis('on')
                                self.IMag_ax.set_xticks(self.major_ticks)
                                self.IMag_ax.set_yticks(self.major_ticks)
                                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IMag_ax.grid(which='major', visible=True)
                                
                                self.IPha_ax.axis('on')
                                self.IPha_ax.set_xticks(self.major_ticks)
                                self.IPha_ax.set_yticks(self.major_ticks)
                                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IPha_ax.grid(which='major', visible=True)
              
                                if params.imageorientation == 'ZX':
                                    self.IMag_ax.set_xlabel('Z in mm')
                                    self.IMag_ax.set_ylabel('X in mm')
                                    self.IPha_ax.set_xlabel('Z in mm')
                                    self.IPha_ax.set_ylabel('X in mm')
                                elif params.imageorientation == 'XZ':
                                    self.IMag_ax.set_xlabel('X in mm')
                                    self.IMag_ax.set_ylabel('Z in mm')
                                    self.IPha_ax.set_xlabel('X in mm')
                                    self.IPha_ax.set_ylabel('Z in mm')
                                    
                            else:
                                self.IMag_ax.axis('off')
                                self.IPha_ax.axis('off')
                    
                            if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                                or params.sequence == 8 or params.sequence == 9:
                                if params.autofreqoffset == 1:
                                    self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                    self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                                else:
                                    self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                                    self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
                            else:
                                self.IMag_ax.set_title('Magnitude Image')
                                self.IPha_ax.set_title('Phase Image')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1160, 950)
            self.all_canvas.show()
            
    def imaging_stitching_single_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure()
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            self.IMag_fig.set_facecolor('None')
            self.IPha_fig = Figure()
            self.IPha_canvas = FigureCanvas(self.IPha_fig)
            self.IPha_fig.set_facecolor('None')

            self.IMag_ax = self.IMag_fig.add_subplot(111)
            self.IPha_ax = self.IPha_fig.add_subplot(111)
            
            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            else: self.IMag_ax.imshow(params.img_st_mag[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            else: self.IPha_ax.imshow(params.img_st_pha[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                                                           
            if params.image_grid == 1:
                self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                
                self.IMag_ax.axis(True)
                self.IMag_ax.set_xticks(self.major_ticks)
                self.IMag_ax.set_yticks(self.major_ticks)
                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IMag_ax.grid(which='major', visible=True)
                
                self.IPha_ax.axis(True)
                self.IPha_ax.set_xticks(self.major_ticks)
                self.IPha_ax.set_yticks(self.major_ticks)
                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IPha_ax.grid(which='major', visible=True)
                
                if params.imageorientation == 'ZX':
                    self.IMag_ax.set_xlabel('Z in mm')
                    self.IMag_ax.set_ylabel('X in mm')
                    self.IPha_ax.set_xlabel('Z in mm')
                    self.IPha_ax.set_ylabel('X in mm')
                elif params.imageorientation == 'XZ':
                    self.IMag_ax.set_xlabel('X in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('X in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                    
            else:
                self.IMag_ax.axis(False)
                self.IMag_ax.grid(False)
                self.IPha_ax.axis(False)
                self.IPha_ax.grid(False)
                
            self.image_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
                    
            if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                or params.sequence == 8 or params.sequence == 9:
                if params.autofreqoffset == 1:
                    self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[params.image_stitching_slice-1] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[params.image_stitching_slice-1] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                else:
                    self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
            else:
                self.IMag_ax.set_title('Magnitude Image')
                self.IPha_ax.set_title('Phase Image')

            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(420, 40, 575, 455)
            self.IPha_canvas.draw()
            self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IPha_canvas.setGeometry(1005, 40, 575, 455)
            self.IMag_canvas.show()
            self.IPha_canvas.show()
            
        else:
            self.all_fig = Figure()
            self.all_canvas = FigureCanvas(self.all_fig)
            self.all_fig.set_facecolor('None')

            #gs = GridSpec(2, 2, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(121)
            self.IMag_ax.grid(False)
            self.IPha_ax = self.all_fig.add_subplot(122)
            self.IPha_ax.grid(False)
            
            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            else: self.IMag_ax.imshow(params.img_st_mag[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
            else: self.IPha_ax.imshow(params.img_st_pha[:, (params.image_stitching_slice-1)*params.nPE:params.image_stitching_slice*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                        
            if params.image_grid == 1:
                self.major_ticks = np.linspace(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)), math.floor((params.FOV / 2)) - math.ceil((-params.FOV / 2)) + 1)
                
                self.IMag_ax.axis(True)
                self.IMag_ax.set_xticks(self.major_ticks)
                self.IMag_ax.set_yticks(self.major_ticks)
                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IMag_ax.grid(which='major', visible=True)
                
                self.IPha_ax.axis(True)
                self.IPha_ax.set_xticks(self.major_ticks)
                self.IPha_ax.set_yticks(self.major_ticks)
                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                self.IPha_ax.grid(which='major', visible=True)
                
                if params.imageorientation == 'ZX':
                    self.IMag_ax.set_xlabel('Z in mm')
                    self.IMag_ax.set_ylabel('X in mm')
                    self.IPha_ax.set_xlabel('Z in mm')
                    self.IPha_ax.set_ylabel('X in mm')
                elif params.imageorientation == 'XZ':
                    self.IMag_ax.set_xlabel('X in mm')
                    self.IMag_ax.set_ylabel('Z in mm')
                    self.IPha_ax.set_xlabel('X in mm')
                    self.IPha_ax.set_ylabel('Z in mm')
                
            else:
                self.IMag_ax.axis(False)
                self.IPha_ax.axis(False)
            
            self.image_positions = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
                    
            if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                or params.sequence == 8 or params.sequence == 9:
                if params.autofreqoffset == 1:
                    self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[params.image_stitching_slice-1] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[params.image_stitching_slice-1] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                else:
                    self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                    self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
            else:
                self.IMag_ax.set_title('Magnitude Image')
                self.IPha_ax.set_title('Phase Image')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1160, 950)
            self.all_canvas.show()

    def imaging_3D_plot_init(self):
        self.image_positions = np.linspace(-params.slicethickness/2 + (params.slicethickness/params.SPEsteps)/2, params.slicethickness/2 - (params.slicethickness/params.SPEsteps)/2, params.SPEsteps)
        
        if params.imagplots == 1:
            
            if params.projection3D == 1:
                self.IMag_fig = Figure()
                self.IMag_canvas = FigureCanvas(self.IMag_fig)
                self.IMag_fig.set_facecolor('None')
                self.IPha_fig = Figure()
                self.IPha_canvas = FigureCanvas(self.IPha_fig)
                self.IPha_fig.set_facecolor('None')
                self.kMag_fig = Figure()
                self.kMag_canvas = FigureCanvas(self.kMag_fig)
                self.kMag_fig.set_facecolor('None')
                self.kPha_fig = Figure()
                self.kPha_canvas = FigureCanvas(self.kPha_fig)
                self.kPha_fig.set_facecolor('None')
                
                self.IMag_ax = self.IMag_fig.add_subplot(111, projection='3d')
                self.IMag_ax.grid(False)
                #self.IPha_ax = self.IPha_fig.add_subplot(111, projection='3d')
                #self.IPha_ax.grid(False)
                self.kMag_ax = self.kMag_fig.add_subplot(111, projection='3d')
                self.kMag_ax.grid(False)
                #self.kPha_ax = self.kPha_fig.add_subplot(111, projection='3d')
                #self.kPha_ax.grid(False) 
                
                if params.projection3D_quality == 1:
                    #Surface Plot
                    self.img_mag_cut_1 = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_mag_cut_1_norm = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_mag_cut_2 = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_pha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_pha_cut_norm = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_kmag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_kmag_cut_norm = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_kpha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_kpha_cut_norm = np.array(np.zeros((params.nPE, params.nPE)))
                
                    if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                        X1, Y1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        X2, Y2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                        Y1, Z1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Y2, Z2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                        Z1, X1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Z2, X2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    
                    cols_per_bin = params.k_amp.shape[2] // params.nPE
                    cols_total = params.nPE * (params.k_amp.shape[2] // params.nPE)
                    start_idx = (params.k_amp.shape[2] - cols_total) // 2
                    end_idx = start_idx + cols_total
                    
                    for n in range(params.img_mag.shape[0]):
                        self.img_mag_cut_1[:, :] = params.img_mag[n, :, :].copy()
                        self.img_mag_cut_1[self.img_mag_cut_1 > params.imagemaximum] = params.imagemaximum
                        self.img_mag_cut_1[self.img_mag_cut_1 < params.imageminimum] = params.imageminimum
                        self.img_mag_cut_2[:, :] = params.img_mag[n, :, :].copy()
                        self.img_mag_cut_2[self.img_mag_cut_2 > params.imagemaximum] = params.imagemaximum
                        #self.img_pha_cut[:, :] = params.img_pha[n, :, :].copy()
                        self.img_kmag_cut[:, :] = params.k_amp[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        #self.img_kpha_cut[:, :] = params.k_pha[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        
                        if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                            Z1 = np.full_like(X1, self.image_positions[n])
                            Z2 = np.full_like(X2, n+1)
                        elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                            X1 = np.full_like(Y1, self.image_positions[n])
                            X2 = np.full_like(Y2, n+1)
                        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                            Y1 = np.full_like(Z1, self.image_positions[n])
                            Y2 = np.full_like(Z2, n+1)
                        
                        self.img_mag_cut_1_norm = (self.img_mag_cut_1 - params.imageminimum) / (params.imagemaximum - params.imageminimum)
                        #self.img_pha_cut_norm = (self.img_pha_cut - self.img_pha_cut.min()) / (self.img_pha_cut.max() - self.img_pha_cut.min())
                        self.img_kmag_cut_norm = (self.img_kmag_cut - self.img_kmag_cut) / (self.img_kmag_cut.max() - self.img_kmag_cut.min())
                        #self.img_kpha_cut_norm = (self.img_kpha_cut - self.img_kpha_cut.min()) / (self.img_kpha_cut.max() - self.img_kpha_cut.min())

                        colors_1 = plt.get_cmap(params.imagecolormap)(np.clip(self.img_mag_cut_1_norm, 0, 1))
                        colors_1[self.img_mag_cut_2 < params.imageminimum, 3] = 0
                        #colors_2 = plt.get_cmap('gray')(np.clip(self.img_pha_cut_norm, 0, 1))
                        #colors_2[self.img_mag_cut_2 < params.imageminimum, 3] = 0
                        colors_3 = plt.get_cmap('inferno')(np.clip((self.img_kmag_cut - params.k_amp.min()) / (params.k_amp.max() - params.k_amp.min()), 0, 1))
                        colors_3[self.img_kmag_cut < 0.1*params.k_amp.max(), 3] = 0
                        #colors_4 = plt.get_cmap('inferno')(np.clip((self.img_kpha_cut - params.k_pha.min()) / (params.k_pha.max() - params.k_pha.min()), 0, 1))
                        
                        if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=False, shade=False, edgecolor='none')
                            #if params.imagefilter == 1: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            #else: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            self.kMag_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_3, antialiased=True, shade=False, edgecolor='none')
                            #self.kPha_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_4, antialiased=True, shade=False, edgecolor='none')
                        elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':    
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=False, shade=False, edgecolor='none')
                            #if params.imagefilter == 1: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            #else: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            self.kMag_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_3, antialiased=True, shade=False, edgecolor='none')
                            #self.kPha_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_4, antialiased=True, shade=False, edgecolor='none')
                        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':    
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=False, shade=False, edgecolor='none')
                            #if params.imagefilter == 1: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            #else: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            self.kMag_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_3, antialiased=True, shade=False, edgecolor='none')
                            #self.kPha_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_4, antialiased=True, shade=False, edgecolor='none')
                                                         
                else:
                    #Contour Plot
                    self.img_mag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_pha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_kmag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_kpha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    
                    if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                        X1, Y1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        X2, Y2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                        Y1, Z1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Y2, Z2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                        Z1, X1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Z2, X2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    
                    levels1 = np.linspace(params.imageminimum, params.imagemaximum, 20)
                    #levels2 = np.linspace(params.img_pha.min(), params.pha_mag.max(), 20)
                    levels3 = np.linspace(params.k_amp.min(), params.k_amp.max(), 20)
                    #levels4 = np.linspace(params.k_pha.min(), params.k_pha.max(), 20)
                    
                    cols_per_bin = params.k_amp.shape[2] // params.nPE
                    cols_total = params.nPE * (params.k_amp.shape[2] // params.nPE)
                    start_idx = (params.k_amp.shape[2] - cols_total) // 2
                    end_idx = start_idx + cols_total
                    
                    for n in range(params.img_mag.shape[0]):
                        self.img_mag_cut[:, :] = params.img_mag[n, :, :].copy()
                        #self.img_pha_cut[:, :] = params.img_pha[n, :, :].copy()
                        self.img_kmag_cut[:, :] = params.k_amp[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        #self.img_kpha_cut[:, :] = params.k_pha[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        
                        if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                            self.IMag_ax.contour(X1, Y1, self.img_mag_cut, zdir='z', offset=self.image_positions[n], levels=levels1, cmap=params.imagecolormap, extend='neither')
                            #self.IPha_ax.contour(X1, Y1, self.img_pha_cut, zdir='z', offset=self.image_positions[n], levels=levels2, cmap='gray', extend='neither')
                            self.kMag_ax.contour(X2, Y2, self.img_kmag_cut, zdir='z', offset=n+1, levels=levels3, cmap='inferno', extend='neither')
                            #self.kPha_ax.contour(X2, Y2, self.img_kpha_cut, zdir='z', offset=n+1, levels=levels4, cmap='inferno', extend='neither')
                        elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                            self.IMag_ax.contour(self.img_mag_cut, Y1, Z1, zdir='x', offset=self.image_positions[n], levels=levels1, cmap=params.imagecolormap, extend='neither')
                            #self.IPha_ax.contour(self.img_pha_cut, Y1, Z1, zdir='x', offset=self.image_positions[n], levels=levels2, cmap='gray', extend='neither')
                            self.kMag_ax.contour(self.img_kmag_cut, Y2, Z2, zdir='x', offset=n+1, levels=levels3, cmap='inferno', extend='neither')
                            #self.kPha_ax.contour(self.img_kpha_cut, Y2, Z2, zdir='x', offset=n+1, levels=levels4, cmap='inferno', extend='neither')
                        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                            self.IMag_ax.contour(X1, self.img_mag_cut, Z1, zdir='y', offset=self.image_positions[n], levels=levels1, cmap=params.imagecolormap, extend='neither')
                            #self.IPha_ax.contour(X1, self.img_pha_cut, Z1, zdir='y', offset=self.image_positions[n], levels=levels2, cmap='gray', extend='neither')
                            self.kMag_ax.contour(X2, self.img_kmag_cut, Z2, zdir='y', offset=n+1, levels=levels3, cmap='inferno', extend='neither')
                            #self.kPha_ax.contour(X2, self.img_kpha_cut, Z2, zdir='y', offset=n+1, levels=levels4, cmap='inferno', extend='neither')
                
                if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                    self.IMag_ax.set_box_aspect([1, 1, params.slicethickness/params.FOV])
                    self.IMag_ax.set_zlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    #self.IPha_ax.set_box_aspect([1, 1, params.slicethickness/params.FOV])
                    #self.IPha_ax.set_zlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    self.kMag_ax.set_box_aspect([1, 1, params.img_mag.shape[0]/params.FOV])
                    self.kMag_ax.set_zlim([1, (params.img_mag.shape[0])])
                    #self.kPha_ax.set_box_aspect([1, 1, params.img_mag.shape[0]/params.FOV])
                    #self.kPha_ax.set_zlim([1, (params.img_mag.shape[0])])
                elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                    self.IMag_ax.set_box_aspect([params.slicethickness/params.FOV, 1, 1])
                    self.IMag_ax.set_xlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    #self.IPha_ax.set_box_aspect([params.img_mag.shape[0]/params.FOV, 1, 1])
                    #self.IPha_ax.set_xlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    self.kMag_ax.set_box_aspect([params.img_mag.shape[0]/params.FOV, 1, 1])
                    self.kMag_ax.set_xlim([1, (params.img_mag.shape[0])])
                    #self.kPha_ax.set_box_aspect([params.img_mag.shape[0]/params.FOV, 1, 1])
                    #self.kPha_ax.set_xlim([1, (params.img_mag.shape[0])])
                elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                    self.IMag_ax.set_box_aspect([1, params.slicethickness/params.FOV, 1])
                    self.IMag_ax.set_ylim([(-params.slicethickness/2), (params.slicethickness/2)])
                    #self.IPha_ax.set_box_aspect([1, params.slicethickness/params.FOV, 1])
                    #self.IPha_ax.set_ylim([(-params.slicethickness/2), (params.slicethickness/2)])
                    self.kMag_ax.set_box_aspect([1, params.img_mag.shape[0]/params.FOV, 1])
                    self.kMag_ax.set_ylim([1, (params.img_mag.shape[0])])
                    #self.kPha_ax.set_box_aspect([1, params.img_mag.shape[0]/params.FOV, 1])
                    #self.kPha_ax.set_ylim([1, (params.img_mag.shape[0])])
                
                if params.image_grid == 1:
                    self.major_ticks_1 = self.image_positions
                    
                    if params.FOV <= 10: self.major_ticks_2 = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 1, 1)
                    elif params.FOV > 10 and params.FOV <= 20: self.major_ticks_2 = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 2, 2)
                    else: self.major_ticks_2 = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 4, 4)
                    
                    if params.k_amp.shape[2]/250 <= 10: self.major_ticks_3 = np.arange(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2 + 1, 1)
                    elif params.k_amp.shape[2]/250 > 10 and params.k_amp.shape[2]/250 <= 20: self.major_ticks_3 = np.arange(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2 + 2, 2)
                    else: self.major_ticks_3 = np.arange(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2 + 4, 4)
                    
                    if params.nPE <= 10: self.major_ticks_4 = np.arange(-params.nPE/2, params.nPE/2 + 1, 1)
                    elif params.nPE > 10 and params.nPE <= 20: self.major_ticks_4 = np.arange(-params.nPE/2, params.nPE/2 + 2, 2)
                    else: self.major_ticks_4 = np.arange(-params.nPE/2, params.nPE/2  + 4, 4)
                    
                    self.major_ticks_5 = np.arange(1, params.img_mag.shape[0] + 1, 1)
                  
                    self.IMag_ax.axis('on')
                    #self.IPha_ax.axis('on')
                    self.IMag_ax.set(xlabel='X',ylabel='Y', zlabel='Z')
                    #self.IPha_ax.set(xlabel='X',ylabel='Y', zlabel='Z')
                    
                    if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                        self.IMag_ax.set_xticks(self.major_ticks_2)
                        self.IMag_ax.set_yticks(self.major_ticks_2)
                        self.IMag_ax.set_zticks(self.major_ticks_1)
                        #self.IPha_ax.set_xticks(self.major_ticks_2)
                        #self.IPha_ax.set_yticks(self.major_ticks_2)
                        #self.IPha_ax.set_zticks(self.major_ticks_1)
                        self.kMag_ax.set(xlabel='Sample', ylabel='Phase Encoding Step', zlabel='3D Phase Encoding Step')
                        #self.kPha_ax.set(xlabel='Sample', ylabel='Phase Encoding Step', zlabel='3D Phase Encoding Step')
                        self.kMag_ax.set_xticks(self.major_ticks_3)
                        self.kMag_ax.set_yticks(self.major_ticks_4)
                        self.kMag_ax.set_zticks(self.major_ticks_5)
                        #self.kPha_ax.set_xticks(self.major_ticks_3)
                        #self.kPha_ax.set_yticks(self.major_ticks_4)
                        #self.kPha_ax.set_zticks(self.major_ticks_5)
                    elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                        self.IMag_ax.set_yticks(self.major_ticks_2)
                        self.IMag_ax.set_zticks(self.major_ticks_2)
                        self.IMag_ax.set_xticks(self.major_ticks_1)
                        #self.IPha_ax.set_yticks(self.major_ticks_2)
                        #self.IPha_ax.set_zticks(self.major_ticks_2)
                        #self.IPha_ax.set_xticks(self.major_ticks_1)
                        self.kMag_ax.set(ylabel='Sample', zlabel='Phase Encoding Step', xlabel='3D Phase Encoding Step')
                        #self.kPha_ax.set(ylabel='Sample', zlabel='Phase Encoding Step', xlabel='3D Phase Encoding Step')
                        self.kMag_ax.set_xticks(self.major_ticks_5)
                        self.kMag_ax.set_yticks(self.major_ticks_3)
                        self.kMag_ax.set_zticks(self.major_ticks_4)
                        #self.kPha_ax.set_xticks(self.major_ticks_5)
                        #self.kPha_ax.set_yticks(self.major_ticks_3)
                        #self.kPha_ax.set_zticks(self.major_ticks_4)
                    elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                        self.IMag_ax.set_zticks(self.major_ticks_2)
                        self.IMag_ax.set_xticks(self.major_ticks_2)
                        self.IMag_ax.set_yticks(self.major_ticks_1)
                        #self.IPha_ax.set_zticks(self.major_ticks_2)
                        #self.IPha_ax.set_xticks(self.major_ticks_2)
                        #self.IPha_ax.set_yticks(self.major_ticks_1)
                        self.kMag_ax.set(zlabel='Sample', xlabel='Phase Encoding Step', ylabel='3D Phase Encoding Step')
                        #self.kPha_ax.set(zlabel='Sample', xlabel='Phase Encoding Step', ylabel='3D Phase Encoding Step')
                        self.kMag_ax.set_xticks(self.major_ticks_4)
                        self.kMag_ax.set_yticks(self.major_ticks_5)
                        self.kMag_ax.set_zticks(self.major_ticks_3)
                        #self.kPha_ax.set_xticks(self.major_ticks_4)
                        #self.kPha_ax.set_yticks(self.major_ticks_5)
                        #self.kPha_ax.set_zticks(self.major_ticks_3) 
                        
                    self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.IMag_ax.grid(which='major', visible=True)
                    self.IMag_ax.grid(True)
                    #self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    #self.IPha_ax.grid(which='major', visible=True)
                    #self.IPha_ax.grid(True)
                    self.kMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.kMag_ax.grid(which='major', visible=True)
                    self.kMag_ax.grid(True)
                    #self.kPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    #self.kPha_ax.grid(which='major', visible=True)
                    #self.kPha_ax.grid(True)

                else:
                    self.IMag_ax.axis('off')
                    #self.IPha_ax.axis('off')
                    self.kMag_ax.axis('off')
                    #self.kPha_ax.axis('off')
                    
                self.IMag_canvas.draw()
                self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.IMag_canvas.setGeometry(420, 40, 575, 455)
                self.IMag_canvas.show()
                #self.IPha_canvas.draw()
                #self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                #self.IPha_canvas.setGeometry(1005, 40, 575, 455)
                #self.IPha_canvas.show()
                self.kMag_canvas.draw()
                self.kMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.kMag_canvas.setGeometry(420, 535, 575, 455)
                self.kMag_canvas.show()
                #self.kPha_canvas.draw()
                #self.kPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                #self.kPha_canvas.setGeometry(1005, 535, 575, 455)
                #self.kPha_canvas.show()
                    
            else:
                self.IMag_fig = Figure()
                self.IMag_canvas = FigureCanvas(self.IMag_fig)
                self.IMag_fig.set_facecolor('None')
                self.IPha_fig = Figure()
                self.IPha_canvas = FigureCanvas(self.IPha_fig)
                self.IPha_fig.set_facecolor('None')
                self.kMag_fig = Figure()
                self.kMag_canvas = FigureCanvas(self.kMag_fig)
                self.kMag_fig.set_facecolor('None')
                self.kPha_fig = Figure()
                self.kPha_canvas = FigureCanvas(self.kPha_fig)
                self.kPha_fig.set_facecolor('None')
                
                gs_IMag = GridSpec(1, params.img_mag.shape[0], figure=self.IMag_fig)
                gs_IPha = GridSpec(1, params.img_mag.shape[0], figure=self.IPha_fig)
                gs_kMag = GridSpec(1, params.img_mag.shape[0], figure=self.kMag_fig)
                gs_kPha = GridSpec(1, params.img_mag.shape[0], figure=self.kPha_fig)
                
                for n in range(params.img_mag.shape[0]):
                    self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[0, n])
                    self.IMag_ax.grid(False)
                    self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[0, n])
                    self.IPha_ax.grid(False)
                    self.kMag_ax = self.kMag_fig.add_subplot(gs_kMag[0, n])
                    self.kMag_ax.grid(False)
                    self.kPha_ax = self.kPha_fig.add_subplot(gs_kPha[0, n])
                    self.kPha_ax.grid(False)
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    else: self.IMag_ax.imshow(params.img_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    else: self.IPha_ax.imshow(params.img_pha[n, :, :], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                        
                    if params.image_grid == 1:
                        self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.major_ticks)
                        self.IMag_ax.set_yticks(self.major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.major_ticks)
                        self.IPha_ax.set_yticks(self.major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'XY':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Y in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Y in mm')
                        elif params.imageorientation == 'YZ':
                            self.IMag_ax.set_xlabel('Y in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        elif params.imageorientation == 'ZX':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('X in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('X in mm')
                        elif params.imageorientation == 'YX':
                            self.IMag_ax.set_xlabel('Y in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        elif params.imageorientation == 'ZY':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('Y in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('Y in mm')
                        elif params.imageorientation == 'XZ':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                            
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')

                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        
                    if params.lnkspacemag == 1:
                        self.kMag_ax.imshow(np.log(params.k_amp[n, :, :]), cmap='inferno', vmin=np.min(np.log(params.k_amp)), vmax=np.max(np.log(params.k_amp)))
                        self.kMag_ax.set_title('ln(k-Space Magnitude) ' + str(n+1))
                    else:
                        self.kMag_ax.imshow(params.k_amp[n, :, :], cmap='inferno', vmin=np.min(params.k_amp), vmax=np.max(params.k_amp))
                        self.kMag_ax.set_title('k-Space Magnitude ' + str(n+1))
                        
                    self.kMag_ax.axis('off')
                    self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                    
                    self.kPha_ax.imshow(params.k_pha[n, :, :], cmap='inferno')
                    self.kPha_ax.axis('off')
                    self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
                    self.kPha_ax.set_title('k-Space Phase ' + str(n+1))
                    
                self.IMag_canvas.draw()
                self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.IMag_canvas.setGeometry(420, 40, 575, 455)
                self.IMag_canvas.show()
                self.IPha_canvas.draw()
                self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.IPha_canvas.setGeometry(1005, 40, 575, 455)
                self.IPha_canvas.show()
                self.kMag_canvas.draw()
                self.kMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.kMag_canvas.setGeometry(420, 535, 575, 455)
                self.kMag_canvas.show()
                self.kPha_canvas.draw()
                self.kPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.kPha_canvas.setGeometry(1005, 535, 575, 455)
                self.kPha_canvas.show()
        
        else:
            self.all_fig = Figure()
            self.all_canvas = FigureCanvas(self.all_fig)
            self.all_fig.set_facecolor('None')
            
            if params.projection3D == 1:
                self.IMag_ax = self.all_fig.add_subplot(211, projection='3d')
                self.IMag_ax.grid(False)
                #self.IPha_ax = self.all_fig.add_subplot(222, projection='3d')
                #self.IPha_ax.grid(False)
                self.kMag_ax = self.all_fig.add_subplot(212, projection='3d')
                self.kMag_ax.grid(False)
                #self.kPha_ax = self.all_fig.add_subplot(224, projection='3d')
                #self.kPha_ax.grid(False)
                
                if params.projection3D_quality == 1:
                    #Surface Plot
                    self.img_mag_cut_1 = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_mag_cut_1_norm = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_mag_cut_2 = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_pha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_pha_cut_norm = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_kmag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_kmag_cut_norm = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_kpha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_kpha_cut_norm = np.array(np.zeros((params.nPE, params.nPE)))
                
                    if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                        X1, Y1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        X2, Y2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                        Y1, Z1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Y2, Z2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                        Z1, X1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Z2, X2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    
                    cols_per_bin = params.k_amp.shape[2] // params.nPE
                    cols_total = params.nPE * (params.k_amp.shape[2] // params.nPE)
                    start_idx = (params.k_amp.shape[2] - cols_total) // 2
                    end_idx = start_idx + cols_total
                    
                    for n in range(params.img_mag.shape[0]):
                        self.img_mag_cut_1[:, :] = params.img_mag[n, :, :].copy()
                        self.img_mag_cut_1[self.img_mag_cut_1 > params.imagemaximum] = params.imagemaximum
                        self.img_mag_cut_1[self.img_mag_cut_1 < params.imageminimum] = params.imageminimum
                        self.img_mag_cut_2[:, :] = params.img_mag[n, :, :].copy()
                        self.img_mag_cut_2[self.img_mag_cut_2 > params.imagemaximum] = params.imagemaximum
                        #self.img_pha_cut[:, :] = params.img_pha[n, :, :].copy()
                        self.img_kmag_cut[:, :] = params.k_amp[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        #self.img_kpha_cut[:, :] = params.k_pha[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        
                        if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                            Z1 = np.full_like(X1, self.image_positions[n])
                            Z2 = np.full_like(X2, n+1)
                        elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                            X1 = np.full_like(Y1, self.image_positions[n])
                            X2 = np.full_like(Y2, n+1)
                        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                            Y1 = np.full_like(Z1, self.image_positions[n])
                            Y2 = np.full_like(Z2, n+1)
                        
                        self.img_mag_cut_1_norm = (self.img_mag_cut_1 - params.imageminimum) / (params.imagemaximum - params.imageminimum)
                        #self.img_pha_cut_norm = (self.img_pha_cut - self.img_pha_cut.min()) / (self.img_pha_cut.max() - self.img_pha_cut.min())
                        self.img_kmag_cut_norm = (self.img_kmag_cut - self.img_kmag_cut) / (self.img_kmag_cut.max() - self.img_kmag_cut.min())
                        #self.img_kpha_cut_norm = (self.img_kpha_cut - self.img_kpha_cut.min()) / (self.img_kpha_cut.max() - self.img_kpha_cut.min())

                        colors_1 = plt.get_cmap(params.imagecolormap)(np.clip(self.img_mag_cut_1_norm, 0, 1))
                        colors_1[self.img_mag_cut_2 < params.imageminimum, 3] = 0
                        #colors_2 = plt.get_cmap('gray')(np.clip(self.img_pha_cut_norm, 0, 1))
                        #colors_2[self.img_mag_cut_2 < params.imageminimum, 3] = 0
                        colors_3 = plt.get_cmap('inferno')(np.clip((self.img_kmag_cut - params.k_amp.min()) / (params.k_amp.max() - params.k_amp.min()), 0, 1))
                        colors_3[self.img_kmag_cut < 0.1*params.k_amp.max(), 3] = 0
                        #colors_4 = plt.get_cmap('inferno')(np.clip((self.img_kpha_cut - params.k_pha.min()) / (params.k_pha.max() - params.k_pha.min()), 0, 1))
                        
                        if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=False, shade=False, edgecolor='none')
                            #if params.imagefilter == 1: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            #else: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            self.kMag_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_3, antialiased=True, shade=False, edgecolor='none')
                            #self.kPha_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_4, antialiased=True, shade=False, edgecolor='none')
                        elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':    
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=False, shade=False, edgecolor='none')
                            #if params.imagefilter == 1: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            #else: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            self.kMag_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_3, antialiased=True, shade=False, edgecolor='none')
                            #self.kPha_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_4, antialiased=True, shade=False, edgecolor='none')
                        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':    
                            if params.imagefilter == 1: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=True, shade=False, edgecolor='none')
                            else: self.IMag_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_1, antialiased=False, shade=False, edgecolor='none')
                            #if params.imagefilter == 1: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            #else: self.IPha_ax.plot_surface(X1, Y1, Z1, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
                            self.kMag_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_3, antialiased=True, shade=False, edgecolor='none')
                            #self.kPha_ax.plot_surface(X2, Y2, Z2, rcount=params.nPE+1, ccount=params.nPE+1, facecolors=colors_4, antialiased=True, shade=False, edgecolor='none')
                                                         
                else:
                    #Contour Plot
                    self.img_mag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_pha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    self.img_kmag_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    #self.img_kpha_cut = np.array(np.zeros((params.nPE, params.nPE)))
                    
                    if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                        X1, Y1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        X2, Y2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                        Y1, Z1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Y2, Z2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                        Z1, X1 = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
                        Z2, X2 = np.meshgrid(np.linspace(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2, params.nPE),np.linspace(params.nPE/2, -params.nPE/2, params.nPE))
                    
                    levels1 = np.linspace(params.imageminimum, params.imagemaximum, 20)
                    #levels2 = np.linspace(params.img_pha.min(), params.pha_mag.max(), 20)
                    levels3 = np.linspace(params.k_amp.min(), params.k_amp.max(), 20)
                    #levels4 = np.linspace(params.k_pha.min(), params.k_pha.max(), 20)
                    
                    cols_per_bin = params.k_amp.shape[2] // params.nPE
                    cols_total = params.nPE * (params.k_amp.shape[2] // params.nPE)
                    start_idx = (params.k_amp.shape[2] - cols_total) // 2
                    end_idx = start_idx + cols_total
                    
                    for n in range(params.img_mag.shape[0]):
                        self.img_mag_cut[:, :] = params.img_mag[n, :, :].copy()
                        #self.img_pha_cut[:, :] = params.img_pha[n, :, :].copy()
                        self.img_kmag_cut[:, :] = params.k_amp[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        #self.img_kpha_cut[:, :] = params.k_pha[n, :, start_idx:end_idx].copy().reshape(params.nPE, params.nPE, cols_per_bin).mean(axis=2)
                        
                        if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                            self.IMag_ax.contour(X1, Y1, self.img_mag_cut, zdir='z', offset=self.image_positions[n], levels=levels1, cmap=params.imagecolormap, extend='neither')
                            #self.IPha_ax.contour(X1, Y1, self.img_pha_cut, zdir='z', offset=self.image_positions[n], levels=levels2, cmap='gray', extend='neither')
                            self.kMag_ax.contour(X2, Y2, self.img_kmag_cut, zdir='z', offset=n+1, levels=levels3, cmap='inferno', extend='neither')
                            #self.kPha_ax.contour(X2, Y2, self.img_kpha_cut, zdir='z', offset=n+1, levels=levels4, cmap='inferno', extend='neither')
                        elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                            self.IMag_ax.contour(self.img_mag_cut, Y1, Z1, zdir='x', offset=self.image_positions[n], levels=levels1, cmap=params.imagecolormap, extend='neither')
                            #self.IPha_ax.contour(self.img_pha_cut, Y1, Z1, zdir='x', offset=self.image_positions[n], levels=levels2, cmap='gray', extend='neither')
                            self.kMag_ax.contour(self.img_kmag_cut, Y2, Z2, zdir='x', offset=n+1, levels=levels3, cmap='inferno', extend='neither')
                            #self.kPha_ax.contour(self.img_kpha_cut, Y2, Z2, zdir='x', offset=n+1, levels=levels4, cmap='inferno', extend='neither')
                        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                            self.IMag_ax.contour(X1, self.img_mag_cut, Z1, zdir='y', offset=self.image_positions[n], levels=levels1, cmap=params.imagecolormap, extend='neither')
                            #self.IPha_ax.contour(X1, self.img_pha_cut, Z1, zdir='y', offset=self.image_positions[n], levels=levels2, cmap='gray', extend='neither')
                            self.kMag_ax.contour(X2, self.img_kmag_cut, Z2, zdir='y', offset=n+1, levels=levels3, cmap='inferno', extend='neither')
                            #self.kPha_ax.contour(X2, self.img_kpha_cut, Z2, zdir='y', offset=n+1, levels=levels4, cmap='inferno', extend='neither')
                
                if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                    self.IMag_ax.set_box_aspect([1, 1, params.slicethickness/params.FOV])
                    self.IMag_ax.set_zlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    #self.IPha_ax.set_box_aspect([1, 1, params.slicethickness/params.FOV])
                    #self.IPha_ax.set_zlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    self.kMag_ax.set_box_aspect([1, 1, params.img_mag.shape[0]/params.FOV])
                    self.kMag_ax.set_zlim([1, (params.img_mag.shape[0])])
                    #self.kPha_ax.set_box_aspect([1, 1, params.img_mag.shape[0]/params.FOV])
                    #self.kPha_ax.set_zlim([1, (params.img_mag.shape[0])])
                elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                    self.IMag_ax.set_box_aspect([params.slicethickness/params.FOV, 1, 1])
                    self.IMag_ax.set_xlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    #self.IPha_ax.set_box_aspect([params.img_mag.shape[0]/params.FOV, 1, 1])
                    #self.IPha_ax.set_xlim([(-params.slicethickness/2), (params.slicethickness/2)])
                    self.kMag_ax.set_box_aspect([params.img_mag.shape[0]/params.FOV, 1, 1])
                    self.kMag_ax.set_xlim([1, (params.img_mag.shape[0])])
                    #self.kPha_ax.set_box_aspect([params.img_mag.shape[0]/params.FOV, 1, 1])
                    #self.kPha_ax.set_xlim([1, (params.img_mag.shape[0])])
                elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                    self.IMag_ax.set_box_aspect([1, params.slicethickness/params.FOV, 1])
                    self.IMag_ax.set_ylim([(-params.slicethickness/2), (params.slicethickness/2)])
                    #self.IPha_ax.set_box_aspect([1, params.slicethickness/params.FOV, 1])
                    #self.IPha_ax.set_ylim([(-params.slicethickness/2), (params.slicethickness/2)])
                    self.kMag_ax.set_box_aspect([1, params.img_mag.shape[0]/params.FOV, 1])
                    self.kMag_ax.set_ylim([1, (params.img_mag.shape[0])])
                    #self.kPha_ax.set_box_aspect([1, params.img_mag.shape[0]/params.FOV, 1])
                    #self.kPha_ax.set_ylim([1, (params.img_mag.shape[0])])
                
                if params.image_grid == 1:
                    self.major_ticks_1 = self.image_positions
                    
                    if params.FOV <= 10: self.major_ticks_2 = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 1, 1)
                    elif params.FOV > 10 and params.FOV <= 20: self.major_ticks_2 = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 2, 2)
                    else: self.major_ticks_2 = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 4, 4)
                    
                    if params.k_amp.shape[2]/250 <= 10: self.major_ticks_3 = np.arange(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2 + 1, 1)
                    elif params.k_amp.shape[2]/250 > 10 and params.k_amp.shape[2]/250 <= 20: self.major_ticks_3 = np.arange(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2 + 2, 2)
                    else: self.major_ticks_3 = np.arange(-(params.k_amp.shape[2]/250)/2, (params.k_amp.shape[2]/250)/2 + 4, 4)
                    
                    if params.nPE <= 10: self.major_ticks_4 = np.arange(-params.nPE/2, params.nPE/2 + 1, 1)
                    elif params.nPE > 10 and params.nPE <= 20: self.major_ticks_4 = np.arange(-params.nPE/2, params.nPE/2 + 2, 2)
                    else: self.major_ticks_4 = np.arange(-params.nPE/2, params.nPE/2  + 4, 4)
                    
                    self.major_ticks_5 = np.arange(1, params.img_mag.shape[0] + 1, 1)
                  
                    self.IMag_ax.axis('on')
                    #self.IPha_ax.axis('on')
                    self.IMag_ax.set(xlabel='X',ylabel='Y', zlabel='Z')
                    #self.IPha_ax.set(xlabel='X',ylabel='Y', zlabel='Z')
                    
                    if params.imageorientation == 'XY' or params.imageorientation == 'YX':
                        self.IMag_ax.set_xticks(self.major_ticks_2)
                        self.IMag_ax.set_yticks(self.major_ticks_2)
                        self.IMag_ax.set_zticks(self.major_ticks_1)
                        #self.IPha_ax.set_xticks(self.major_ticks_2)
                        #self.IPha_ax.set_yticks(self.major_ticks_2)
                        #self.IPha_ax.set_zticks(self.major_ticks_1)
                        self.kMag_ax.set(xlabel='Sample', ylabel='Phase Encoding Step', zlabel='3D Phase Encoding Step')
                        #self.kPha_ax.set(xlabel='Sample', ylabel='Phase Encoding Step', zlabel='3D Phase Encoding Step')
                        self.kMag_ax.set_xticks(self.major_ticks_3)
                        self.kMag_ax.set_yticks(self.major_ticks_4)
                        self.kMag_ax.set_zticks(self.major_ticks_5)
                        #self.kPha_ax.set_xticks(self.major_ticks_3)
                        #self.kPha_ax.set_yticks(self.major_ticks_4)
                        #self.kPha_ax.set_zticks(self.major_ticks_5)
                    elif params.imageorientation == 'YZ' or params.imageorientation == 'ZY':
                        self.IMag_ax.set_yticks(self.major_ticks_2)
                        self.IMag_ax.set_zticks(self.major_ticks_2)
                        self.IMag_ax.set_xticks(self.major_ticks_1)
                        #self.IPha_ax.set_yticks(self.major_ticks_2)
                        #self.IPha_ax.set_zticks(self.major_ticks_2)
                        #self.IPha_ax.set_xticks(self.major_ticks_1)
                        self.kMag_ax.set(ylabel='Sample', zlabel='Phase Encoding Step', xlabel='3D Phase Encoding Step')
                        #self.kPha_ax.set(ylabel='Sample', zlabel='Phase Encoding Step', xlabel='3D Phase Encoding Step')
                        self.kMag_ax.set_xticks(self.major_ticks_5)
                        self.kMag_ax.set_yticks(self.major_ticks_3)
                        self.kMag_ax.set_zticks(self.major_ticks_4)
                        #self.kPha_ax.set_xticks(self.major_ticks_5)
                        #self.kPha_ax.set_yticks(self.major_ticks_3)
                        #self.kPha_ax.set_zticks(self.major_ticks_4)
                    elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                        self.IMag_ax.set_zticks(self.major_ticks_2)
                        self.IMag_ax.set_xticks(self.major_ticks_2)
                        self.IMag_ax.set_yticks(self.major_ticks_1)
                        #self.IPha_ax.set_zticks(self.major_ticks_2)
                        #self.IPha_ax.set_xticks(self.major_ticks_2)
                        #self.IPha_ax.set_yticks(self.major_ticks_1)
                        self.kMag_ax.set(zlabel='Sample', xlabel='Phase Encoding Step', ylabel='3D Phase Encoding Step')
                        #self.kPha_ax.set(zlabel='Sample', xlabel='Phase Encoding Step', ylabel='3D Phase Encoding Step')
                        self.kMag_ax.set_xticks(self.major_ticks_4)
                        self.kMag_ax.set_yticks(self.major_ticks_5)
                        self.kMag_ax.set_zticks(self.major_ticks_3)
                        #self.kPha_ax.set_xticks(self.major_ticks_4)
                        #self.kPha_ax.set_yticks(self.major_ticks_5)
                        #self.kPha_ax.set_zticks(self.major_ticks_3) 
                        
                    self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.IMag_ax.grid(which='major', visible=True)
                    self.IMag_ax.grid(True)
                    #self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    #self.IPha_ax.grid(which='major', visible=True)
                    #self.IPha_ax.grid(True)
                    self.kMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    self.kMag_ax.grid(which='major', visible=True)
                    self.kMag_ax.grid(True)
                    #self.kPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                    #self.kPha_ax.grid(which='major', visible=True)
                    #self.kPha_ax.grid(True)

                else:
                    self.IMag_ax.axis('off')
                    #self.IPha_ax.axis('off')
                    self.kMag_ax.axis('off')
                    #self.kPha_ax.axis('off')
                                
            else:
                gs = GridSpec(4, params.img_mag.shape[0], figure=self.all_fig)
                
                for n in range(params.img_mag.shape[0]):
                    self.IMag_ax = self.all_fig.add_subplot(gs[0, n])
                    self.IMag_ax.grid(False)
                    self.IPha_ax = self.all_fig.add_subplot(gs[1, n])
                    self.IPha_ax.grid(False)
                    self.kMag_ax = self.all_fig.add_subplot(gs[2, n])
                    self.kMag_ax.grid(False)
                    self.kPha_ax = self.all_fig.add_subplot(gs[3, n])
                    self.kPha_ax.grid(False)
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    else: self.IMag_ax.imshow(params.img_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    else: self.IPha_ax.imshow(params.img_pha[n, :, :], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    
                    if params.image_grid == 1:
                        self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.major_ticks)
                        self.IMag_ax.set_yticks(self.major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.major_ticks)
                        self.IPha_ax.set_yticks(self.major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'XY':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Y in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Y in mm')
                        elif params.imageorientation == 'YZ':
                            self.IMag_ax.set_xlabel('Y in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        elif params.imageorientation == 'ZX':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('X in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('X in mm')
                        elif params.imageorientation == 'YX':
                            self.IMag_ax.set_xlabel('Y in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        elif params.imageorientation == 'ZY':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('Y in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('Y in mm')
                        elif params.imageorientation == 'XZ':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                            
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')

                    self.image_positions = np.linspace(-params.slicethickness/(params.SPEsteps/2)+(params.slicethickness/params.SPEsteps)/2, +params.slicethickness/(params.SPEsteps/2)-(params.slicethickness/params.SPEsteps)/2, params.SPEsteps)
                    
                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        
                    if params.lnkspacemag == 1:
                        self.kMag_ax.imshow(np.log(params.k_amp[n, :, :]), cmap='inferno', vmin=np.min(np.log(params.k_amp)), vmax=np.max(np.log(params.k_amp)))
                        self.kMag_ax.set_title('ln(k-Space Magnitude) ' + str(n+1))
                    else:
                        self.kMag_ax.imshow(params.k_amp[n, :, :], cmap='inferno', vmin=np.min(params.k_amp), vmax=np.max(params.k_amp))
                        self.kMag_ax.set_title('k-Space Magnitude ' + str(n+1))
                        
                    self.kMag_ax.axis('off')
                    self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                    
                    self.kPha_ax.imshow(params.k_pha[n, :, :], cmap='inferno')
                    self.kPha_ax.axis('off')
                    self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
                    self.kPha_ax.set_title('k-Space Phase ' + str(n+1))
                    
            self.all_fig.tight_layout()

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1160, 950)
            self.all_canvas.show()

    def imaging_stitching_3D_plot_init(self):
        #self.image_positions_1 = np.linspace(-params.slicethickness/2 + (params.slicethickness/params.SPEsteps)/2, params.slicethickness/2 - (params.slicethickness/params.SPEsteps)/2, params.SPEsteps)
        #self.image_positions_2 = np.linspace(params.motor_start_position, params.motor_end_position, num=params.motor_image_count)
        
        if params.imagplots == 1:
            self.IMag_fig = Figure()
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            self.IMag_fig.set_facecolor('None')
            self.IPha_fig = Figure()
            self.IPha_canvas = FigureCanvas(self.IPha_fig)
            self.IPha_fig.set_facecolor('None')
                
            if params.imageorientation == 'XY' or params.imageorientation == 'ZY' or params.imageorientation == 'YZ' or params.imageorientation == 'YX':
                self.IMag_ax = self.IMag_fig.add_subplot(111)
                self.IMag_ax.grid(False)
                self.IPha_ax = self.IPha_fig.add_subplot(111)
                self.IPha_ax.grid(False)
                
                self.FOV_1 = 0
                self.FOV_2 = 0
                self.FOV_2_start = 0
                self.FOV_2_end = 0
                
                if params.imageorientation == 'XY' or params.imageorientation == 'ZY':
                    self.FOV_1 = params.FOV
                    if params.motor_movement_step <= params.FOV:
                        self.FOV_2 = params.motor_total_image_length + params.motor_movement_step
                        self.FOV_2_start = params.motor_start_position - params.motor_movement_step/2
                        self.FOV_2_end = params.motor_end_position + params.motor_movement_step/2
                    else:
                        self.FOV_2 = params.motor_total_image_length + params.FOV
                        self.FOV_2_start = params.motor_start_position - params.FOV/2
                        self.FOV_2_end = params.motor_end_position + params.FOV/2
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    else: self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    else: self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    
                    if params.image_grid == 1:
                        if self.FOV_2 <= 20:
                            self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 1, 1)
                            self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 1, 1)
                        elif self.FOV_2 > 20 and self.FOV_2 <= 50:
                            self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 2, 2)
                            self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 2, 2)
                        else:
                            self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 4, 4)
                            self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 5, 5)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.x_major_ticks)
                        self.IPha_ax.set_yticks(self.y_major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'XY':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Y$_{PB}$ in mm')
                        elif params.imageorientation == 'ZY':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('Y$_{PB}$ in mm')
                        
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')
                        
                elif params.imageorientation == 'YZ' or params.imageorientation == 'YX':
                    if params.motor_movement_step <= params.FOV:
                        self.FOV_1 = params.motor_total_image_length + params.motor_movement_step
                        self.FOV_1_start = params.motor_start_position - params.motor_movement_step/2
                        self.FOV_1_end = params.motor_end_position + params.motor_movement_step/2
                    else:
                        self.FOV_1 = params.motor_total_image_length + params.FOV
                        self.FOV_1_start = params.motor_start_position - params.FOV/2
                        self.FOV_1_end = params.motor_end_position + params.FOV/2
                    self.FOV_2 = params.FOV
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    else: self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    else: self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    
                    if params.image_grid == 1:
                        if self.FOV_1 <= 20:
                            self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 1, 1)
                            self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 1, 1)
                        elif self.FOV_1 > 20 and self.FOV_1 <= 50:
                            self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 2, 2)
                            self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 2, 2)
                        else:
                            self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 5, 5)
                            self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 4, 4)
                                            
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.x_major_ticks)
                        self.IPha_ax.set_yticks(self.y_major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'YX':
                            self.IMag_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IMag_ax.set_ylabel('X in mm')
                            self.IPha_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_ylabel('X in mm')
                        elif params.imageorientation == 'YZ':
                            self.IMag_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y$_{PB}$ in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')
                        
                if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                    or params.sequence == 8 or params.sequence == 9:
                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
                else:
                    self.IMag_ax.set_title('Magnitude Image')
                    self.IPha_ax.set_title('Phase Image')
                    
                self.IMag_canvas.draw()
                self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.IMag_canvas.setGeometry(420, 40, 575, 470)
                self.IPha_canvas.draw()
                self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                self.IPha_canvas.setGeometry(1005, 40, 575, 470)

                self.IMag_canvas.show()
                self.IPha_canvas.show()
                
            elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                self.imagecrop_image_pixel = int((params.motor_movement_step * params.SPEsteps) / params.slicethickness)
                self.imagecrop_total_pixel = int(self.imagecrop_image_pixel * params.motor_image_count)
                self.imageexp_total_pixel = (self.imagecrop_image_pixel * (params.motor_image_count - 1) + params.SPEsteps)
                self.image_positions_1 = np.linspace(params.motor_start_position, params.motor_end_position, params.motor_image_count)

                if params.projection3D == 1:
                    self.IMag_ax = self.IMag_fig.add_subplot(111, projection='3d')
                    self.IMag_ax.grid(False)
                    
                    if params.projection3D_quality == 1:
                        print('WIP')
#                         #Surface Plot
#                         self.img_st_mag_cut_1 = np.array(np.zeros((params.nPE, params.nPE)))
#                         self.img_st_mag_cut_1_norm = np.array(np.zeros((params.nPE, params.nPE)))
#                         self.img_st_mag_cut_2 = np.array(np.zeros((params.nPE, params.nPE)))
#                        
#                         X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE+1),np.linspace(params.FOV/2, -params.FOV/2, params.nPE+1))
#                         print(self.image_positions_1)
# 
#                         if params.motor_movement_step <= params.slicethickness:
#                             for m in range(params.motor_image_count):
#                                 for n in range(self.imagecrop_image_pixel):
#                                     self.img_st_mag_cut_1[:, :] = params.img_st_mag[m*self.imagecrop_image_pixel+n, :, :].copy()
#                                     self.img_st_mag_cut_1[self.img_st_mag_cut_1 > params.imagemaximum] = params.imagemaximum
#                                     self.img_st_mag_cut_1[self.img_st_mag_cut_1 < params.imageminimum] = params.imageminimum
#                                     self.img_st_mag_cut_2[:, :] = params.img_st_mag[m*self.imagecrop_image_pixel+n, :, :].copy()
#                                     self.img_st_mag_cut_2[self.img_st_mag_cut_2 > params.imagemaximum] = params.imagemaximum
#                                     
#                                     Y = np.full_like(X, self.image_positions_1[m] - (self.imagecrop_image_pixel/2)*(params.slicethickness/params.SPEsteps) + (params.slicethickness/params.SPEsteps)/2  + n*(params.slicethickness/params.SPEsteps))
# 
#                                     self.img_st_mag_cut_1_norm = (self.img_st_mag_cut_1 - params.imageminimum) / (params.imagemaximum - params.imageminimum)
#                                     
#                                     colors_2 = plt.get_cmap(params.imagecolormap)(np.clip(self.img_st_mag_cut_1_norm, 0, 1))
#                                     colors_2[self.img_st_mag_cut_2 < params.imageminimum, 3] = 0
#                                     
#                                     if params.imagefilter == 1: self.IMag_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_2, antialiased=True, shade=False, edgecolor='none')
#                                     else: self.IMag_ax.plot_surface(Y, Z, X, rstride=1, cstride=1, facecolors=colors_2, antialiased=False, shade=False, edgecolor='none')
#                                     
#                         self.IMag_ax.set_box_aspect([(params.motor_total_image_length + params.slicethickness)/params.FOV, 1, 1])
#                         self.IMag_ax.set_xlim([params.motor_start_position - params.slicethickness/2, params.motor_end_position + params.slicethickness/2])
#                         
#                         del self.img_st_mag_cut_1, self.img_st_mag_cut_1_norm, self.img_st_mag_cut_2, X, Y, Z, colors_2
#                          
# #                         #Voxel Plot
# #                         self.img_st_mag_cut_1 = np.array(np.zeros((params.motor_image_count, params.nPE, params.nPE)))
# #                         self.img_st_mag_cut_1_norm = np.array(np.zeros((params.motor_image_count, params.nPE, params.nPE)))
# #                         self.img_st_mag_cut_2 = np.array(np.zeros((params.motor_image_count, params.nPE, params.nPE)))
# #                         
# #                         for n in range(params.motor_image_count):
# #                             self.img_st_mag_cut_1[n, :, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
# #                             self.img_st_mag_cut_2[n, :, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
# #                             
# #                         
# #                         self.img_st_mag_cut_1[self.img_st_mag_cut_1 > params.imagemaximum] = params.imagemaximum
# #                         self.img_st_mag_cut_1[self.img_st_mag_cut_1 < params.imageminimum] = params.imageminimum
# #                         self.img_st_mag_cut_1[self.img_st_mag_cut_2 > params.imagemaximum] = params.imagemaximum
# #                               
# #                         x_edges = np.linspace(-params.FOV/2, params.FOV/2, self.img_st_mag_cut_2.shape[1]+1)
# #                         y_edges = np.linspace(params.motor_start_position - params.slicethickness/2, params.motor_end_position + params.slicethickness/2, self.img_st_mag_cut_2.shape[0]+1)
# #                         z_edges = np.linspace(-params.FOV/2, params.FOV/2, self.img_st_mag_cut_2.shape[2]+1)
# #                                                 
# #                         Y, Z, X = np.meshgrid(y_edges, z_edges, x_edges, indexing='ij')
# #                         
# #                         self.img_st_mag_cut_1_norm = (self.img_st_mag_cut_1 - params.imageminimum) / (params.imagemaximum - params.imageminimum)
# #                         
# #                         colors_3 = plt.get_cmap(params.imagecolormap)(np.clip(self.img_st_mag_cut_1_norm, 0, 1))
# #                         colors_3[..., 3] = 0.2
# #                         colors_3[self.img_st_mag_cut_2 < params.imageminimum, 3] = 0
# #                         
# #                         self.IMag_ax.voxels(Y, Z, X, self.img_st_mag_cut_1_norm, facecolors=colors_3, shade=False, edgecolor='none')
# #                        
# #                         self.IMag_ax.set_box_aspect([(params.motor_total_image_length + params.slicethickness)/params.FOV, 1, 1])
# #                         self.IMag_ax.set_xlim([params.motor_start_position - params.slicethickness/2, params.motor_end_position + params.slicethickness/2])
# #                         
# #                         del self.img_st_mag_cut_1, self.img_st_mag_cut_1_norm, self.img_st_mag_cut_2, X, Y, Z, colors_3
#                         
#                     else:
#                         #Contour Plot
#                         self.img_st_mag_cut = np.array(np.zeros((params.nPE, params.nPE)))
#                         
#                         X, Z = np.meshgrid(np.linspace(-params.FOV/2, params.FOV/2, params.nPE),np.linspace(params.FOV/2, -params.FOV/2, params.nPE))
#                         
#                         levels = np.linspace(params.imageminimum, params.imagemaximum, 10)
#                         
#                         for n in range(params.motor_image_count):
#                             self.img_st_mag_cut[:, :] = params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE].copy()
#                             
#                             self.IMag_ax.contour(self.img_st_mag_cut, Z, X, zdir='x', offset=self.image_positions[n], levels=levels, cmap=params.imagecolormap, extend='neither')
#                         
#                         self.IMag_ax.set_box_aspect([(params.motor_total_image_length)/params.FOV, 1, 1])
#                         self.IMag_ax.set_xlim([params.motor_start_position, params.motor_end_position])
#                         
#                         del self.img_st_mag_cut, X, Z, levels
#                     
#                     if params.image_grid == 1:
#                         if params.motor_total_image_length <= 20:
#                             self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 1, 1)
#                             self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 1, 1)
#                         elif params.motor_total_image_length > 20 and params.motor_total_image_length <= 50:
#                             self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 2, 2)
#                             self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 2, 2)
#                         else:
#                             self.x_major_ticks = np.arange(math.ceil(params.motor_start_position), math.floor(params.motor_end_position) + 5, 5)
#                             self.y_major_ticks = np.arange(math.ceil(-params.FOV / 2), math.floor(params.FOV / 2) + 4, 4)
#                         
#                         self.IMag_ax.axis('on')
#                         self.IMag_ax.set_xticks(self.x_major_ticks)
#                         self.IMag_ax.set_yticks(self.y_major_ticks)
#                         self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
#                         self.IMag_ax.grid(which='major', visible=True)
#                         self.IMag_ax.grid(True)
#                         
#                         if params.imageorientation == 'ZX':
#                             self.IMag_ax.set(xlabel='\n\nY$_{PB}$',ylabel='Z', zlabel='X')
#                         elif params.imageorientation == 'XZ':
#                             self.IMag_ax.set(xlabel='\n\nY$_{PB}$',ylabel='X', zlabel='Z')
#                     else:
#                         self.IMag_ax.axis('off')
#                         
# 
#                     #self.IMag_fig.patch.set_facecolor('black')
#                     #self.IMag_fig.set_facecolor('black')
#                     #self.IMag_ax.set_facecolor('black')
#                     #self.IMag_ax.xaxis.set_pane_color((0, 0, 0, 1))
#                     #self.IMag_ax.yaxis.set_pane_color((0, 0, 0, 1))
#                     #self.IMag_ax.zaxis.set_pane_color((0, 0, 0, 1))
#                     #self.IMag_ax.tick_params(axis='both', colors='white')
#                     #self.IMag_ax.xaxis.label.set_color('white')
#                     #self.IMag_ax.yaxis.label.set_color('white')
#                     #self.IMag_ax.zaxis.label.set_color('white')
#                     #self.IMag_ax.grid(True, color='white')
#                     
#                     self.IMag_canvas.draw()
#                     self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
#                     self.IMag_canvas.setGeometry(420, 40, 1160, 950)
#                     self.IMag_canvas.show()
                        
                else:
# #                     if params.motor_image_count > 6:
# #                         gs_IMag = GridSpec(int(np.ceil(params.motor_image_count/6)), 6, figure=self.IMag_fig)
# #                         gs_IPha = GridSpec(int(np.ceil(params.motor_image_count/6)), 6, figure=self.IPha_fig)
# #                         
# #                         for m in range(int(np.ceil(params.motor_image_count/6))):
# #                             for n in range(6):
# #                                 if m*6 + n < params.motor_image_count:
# #                                     self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[m, n])
# #                                     self.IMag_ax.grid(False)
# #                                     self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[m, n])
# #                                     self.IPha_ax.grid(False)
# #                                     
# #                                     if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                                     else: self.IMag_ax.imshow(params.img_st_mag[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                                     if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                                     else: self.IPha_ax.imshow(params.img_st_pha[:, (m*6+n)*params.nPE:((m*6+n)+1)*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                                            
# #                                     if params.image_grid == 1:
# #                                         self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
# #                                         
# #                                         self.IMag_ax.axis('on')
# #                                         self.IMag_ax.set_xticks(self.major_ticks)
# #                                         self.IMag_ax.set_yticks(self.major_ticks)
# #                                         self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
# #                                         self.IMag_ax.grid(which='major', visible=True)
# #                                         
# #                                         self.IPha_ax.axis('on')
# #                                         self.IPha_ax.set_xticks(self.major_ticks)
# #                                         self.IPha_ax.set_yticks(self.major_ticks)
# #                                         self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
# #                                         self.IPha_ax.grid(which='major', visible=True)
# #                       
# #                                         if params.imageorientation == 'ZX':
# #                                             self.IMag_ax.set_xlabel('Z in mm')
# #                                             self.IMag_ax.set_ylabel('X in mm')
# #                                             self.IPha_ax.set_xlabel('Z in mm')
# #                                             self.IPha_ax.set_ylabel('X in mm')
# #                                         elif params.imageorientation == 'XZ':
# #                                             self.IMag_ax.set_xlabel('X in mm')
# #                                             self.IMag_ax.set_ylabel('Z in mm')
# #                                             self.IPha_ax.set_xlabel('X in mm')
# #                                             self.IPha_ax.set_ylabel('Z in mm')
# #                                             
# #                                     else:
# #                                         self.IMag_ax.axis('off')
# #                                         self.IPha_ax.axis('off')
# #                                       
# #                                     if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
# #                                         or params.sequence == 8 or params.sequence == 9:
# #                                         if params.autofreqoffset == 1:
# #                                             self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[(m*6+n)] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
# #                                             self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[(m*6+n)] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
# #                                         else:
# #                                             self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
# #                                             self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
# #                                     else:
# #                                         self.IMag_ax.set_title('Magnitude Image')
# #                                         self.IPha_ax.set_title('Phase Image')
# #                     else:
# #                         gs_IMag = GridSpec(1, params.motor_image_count, figure=self.IMag_fig)
# #                         gs_IPha = GridSpec(1, params.motor_image_count, figure=self.IPha_fig)
# #                         
# #                         for n in range(params.motor_image_count):
# #                             self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[0, n])
# #                             self.IMag_ax.grid(False)
# #                             self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[0, n])
# #                             self.IPha_ax.grid(False)
# #                             
# #                             if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                             else: self.IMag_ax.imshow(params.img_st_mag[:, n*params.nPE:(n+1)*params.nPE], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                             if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[:, n*params.nPE:(n+1)*params.nPE], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                             else: self.IPha_ax.imshow(params.img_st_pha[:, n*params.nPE:(n+1)*params.nPE], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
# #                             
# #                             if params.image_grid == 1:
# #                                 self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
# #                                 
# #                                 self.IMag_ax.axis('on')
# #                                 self.IMag_ax.set_xticks(self.major_ticks)
# #                                 self.IMag_ax.set_yticks(self.major_ticks)
# #                                 self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
# #                                 self.IMag_ax.grid(which='major', visible=True)
# #                                 
# #                                 self.IPha_ax.axis('on')
# #                                 self.IPha_ax.set_xticks(self.major_ticks)
# #                                 self.IPha_ax.set_yticks(self.major_ticks)
# #                                 self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
# #                                 self.IPha_ax.grid(which='major', visible=True)
# #               
# #                                 if params.imageorientation == 'ZX':
# #                                     self.IMag_ax.set_xlabel('Z in mm')
# #                                     self.IMag_ax.set_ylabel('X in mm')
# #                                     self.IPha_ax.set_xlabel('Z in mm')
# #                                     self.IPha_ax.set_ylabel('X in mm')
# #                                 elif params.imageorientation == 'XZ':
# #                                     self.IMag_ax.set_xlabel('X in mm')
# #                                     self.IMag_ax.set_ylabel('Z in mm')
# #                                     self.IPha_ax.set_xlabel('X in mm')
# #                                     self.IPha_ax.set_ylabel('Z in mm')
# #                                     
# #                             else:
# #                                 self.IMag_ax.axis('off')
# #                                 self.IPha_ax.axis('off')
# #                     
# #                             if params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
# #                                 or params.sequence == 8 or params.sequence == 9:
# #                                 if params.autofreqoffset == 1:
# #                                     self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
# #                                     self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness) + 'mm)')
# #                                 else:
# #                                     self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness) + 'mm)')
# #                                     self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness) + 'mm)')
# #                             else:
# #                                 self.IMag_ax.set_title('Magnitude Image')
# #                                 self.IPha_ax.set_title('Phase Image')
# #             
# #                     self.IMag_canvas.draw()
# #                     self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
# #                     self.IMag_canvas.setGeometry(420, 40, 575, 470)
# #                     self.IPha_canvas.draw()
# #                     self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
# #                     self.IPha_canvas.setGeometry(1005, 40, 575, 470)
# # 
# #                     self.IMag_canvas.show()
# #                     self.IPha_canvas.show()
        
 
                    self.IMag_fig = Figure()
                    self.IMag_canvas = FigureCanvas(self.IMag_fig)
                    self.IMag_fig.set_facecolor('None')
                    #self.IPha_fig = Figure()
                    #self.IPha_canvas = FigureCanvas(self.IPha_fig)
                    #self.IPha_fig.set_facecolor('None')
                    
                    for n in range(params.img_st_mag.shape[0]):
                        if params.imageorientation == 'XY' or params.imageorientation == 'ZY':
                            gs_IMag = GridSpec(1, params.img_st_mag.shape[0], figure=self.IMag_fig)
                            gs_IPha = GridSpec(1, params.img_st_mag.shape[0], figure=self.IPha_fig)
                            
                            self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[0, n])
                            self.IMag_ax.grid(False)
                            self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[0, n])
                            self.IPha_ax.grid(False)
                            
                            self.FOV_1 = params.FOV
                            if params.motor_movement_step <= params.FOV:
                                self.FOV_2 = params.motor_total_image_length + params.motor_movement_step
                                self.FOV_2_start = params.motor_start_position - params.motor_movement_step/2
                                self.FOV_2_end = params.motor_end_position + params.motor_movement_step/2
                            else:
                                self.FOV_2 = params.motor_total_image_length + params.FOV
                                self.FOV_2_start = params.motor_start_position - params.FOV/2
                                self.FOV_2_end = params.motor_end_position + params.FOV/2
                                
                            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                            else: self.IMag_ax.imshow(params.img_st_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                            else: self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                            
                            if params.image_grid == 1:
                                self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 1, 1)
                                self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 1, 1)
                                
                                self.IMag_ax.axis('on')
                                self.IMag_ax.set_xticks(self.x_major_ticks)
                                self.IMag_ax.set_yticks(self.y_major_ticks)
                                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IMag_ax.grid(which='major', visible=True)
                                
                                self.IPha_ax.axis('on')
                                self.IPha_ax.set_xticks(self.x_major_ticks)
                                self.IPha_ax.set_yticks(self.y_major_ticks)
                                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IPha_ax.grid(which='major', visible=True)
                                
                                if params.imageorientation == 'XY':
                                    self.IMag_ax.set_xlabel('X in mm')
                                    self.IMag_ax.set_ylabel('Y in mm')
                                    self.IPha_ax.set_xlabel('X in mm')
                                    self.IPha_ax.set_ylabel('Y in mm')
                                elif params.imageorientation == 'ZY':
                                    self.IMag_ax.set_xlabel('Z in mm')
                                    self.IMag_ax.set_ylabel('Y in mm')
                                    self.IPha_ax.set_xlabel('Z in mm')
                                    self.IPha_ax.set_ylabel('Y in mm')
                                
                            else:
                                self.IMag_ax.axis('off')
                                self.IPha_ax.axis('off')
                                
                            self.image_positions = np.linspace(-params.slicethickness/(params.SPEsteps/2)+(params.slicethickness/params.SPEsteps)/2, +params.slicethickness/(params.SPEsteps/2)-(params.slicethickness/params.SPEsteps)/2, params.SPEsteps)

                            if params.autofreqoffset == 1:
                                self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                            else:
                                self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                
                        elif params.imageorientation == 'YZ' or params.imageorientation == 'YX':
                            gs_IMag = GridSpec(params.img_st_mag.shape[0], 1, figure=self.IMag_fig)
                            gs_IPha = GridSpec(params.img_st_mag.shape[0], 1, figure=self.IPha_fig)
                    
                            self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[n, 0])
                            self.IMag_ax.grid(False)
                            self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[n, 0])
                            self.IPha_ax.grid(False)
                            
                            if params.motor_movement_step <= params.FOV:
                                self.FOV_1 = params.motor_total_image_length + params.motor_movement_step
                                self.FOV_1_start = params.motor_start_position - params.motor_movement_step/2
                                self.FOV_1_end = params.motor_end_position + params.motor_movement_step/2
                            else:
                                self.FOV_1 = params.motor_total_image_length + params.FOV
                                self.FOV_1_start = params.motor_start_position - params.FOV/2
                                self.FOV_1_end = params.motor_end_position + params.FOV/2
                            self.FOV_2 = params.FOV
                            
                            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                            else: self.IMag_ax.imshow(params.img_st_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                            else: self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                                
                                
                            if params.image_grid == 1:
                                self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 1, 1)
                                self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 1, 1)
                                
                                self.IMag_ax.axis('on')
                                self.IMag_ax.set_xticks(self.x_major_ticks)
                                self.IMag_ax.set_yticks(self.y_major_ticks)
                                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IMag_ax.grid(which='major', visible=True)
                                
                                self.IPha_ax.axis('on')
                                self.IPha_ax.set_xticks(self.x_major_ticks)
                                self.IPha_ax.set_yticks(self.y_major_ticks)
                                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IPha_ax.grid(which='major', visible=True)
                                
                                if params.imageorientation == 'YZ':
                                    self.IMag_ax.set_xlabel('Y in mm')
                                    self.IMag_ax.set_ylabel('Z in mm')
                                    self.IPha_ax.set_xlabel('Y in mm')
                                    self.IPha_ax.set_ylabel('Z in mm')
                                elif params.imageorientation == 'YX':
                                    self.IMag_ax.set_xlabel('Y in mm')
                                    self.IMag_ax.set_ylabel('Z in mm')
                                    self.IPha_ax.set_xlabel('Y in mm')
                                    self.IPha_ax.set_ylabel('Z in mm')
                                
                            else:
                                self.IMag_ax.axis('off')
                                self.IPha_ax.axis('off')
                                
                            self.image_positions = np.linspace(-params.slicethickness/(params.SPEsteps/2)+(params.slicethickness/params.SPEsteps)/2, +params.slicethickness/(params.SPEsteps/2)-(params.slicethickness/params.SPEsteps)/2, params.SPEsteps)

                            if params.autofreqoffset == 1:
                                self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                            else:
                                self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                
                        elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                            gs_IMag = GridSpec(1, params.img_st_mag.shape[0], figure=self.IMag_fig)
                            gs_IPha = GridSpec(1, params.img_st_mag.shape[0], figure=self.IPha_fig)
                    
                            self.IMag_ax = self.IMag_fig.add_subplot(gs_IMag[0, n])
                            self.IMag_ax.grid(False)
                            self.IPha_ax = self.IPha_fig.add_subplot(gs_IPha[0, n])
                            self.IPha_ax.grid(False)
                            
                            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            else: self.IMag_ax.imshow(params.img_st_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            else: self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                            
                            if params.image_grid == 1:
                                self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                                
                                self.IMag_ax.axis('on')
                                self.IMag_ax.set_xticks(self.major_ticks)
                                self.IMag_ax.set_yticks(self.major_ticks)
                                self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IMag_ax.grid(which='major', visible=True)
                                
                                self.IPha_ax.axis('on')
                                self.IPha_ax.set_xticks(self.major_ticks)
                                self.IPha_ax.set_yticks(self.major_ticks)
                                self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                                self.IPha_ax.grid(which='major', visible=True)
                                
                                if params.imageorientation == 'ZX':
                                    self.IMag_ax.set_xlabel('Z in mm')
                                    self.IMag_ax.set_ylabel('X in mm')
                                    self.IPha_ax.set_xlabel('Z in mm')
                                    self.IPha_ax.set_ylabel('X in mm')
                                elif params.imageorientation == 'XZ':
                                    self.IMag_ax.set_xlabel('X in mm')
                                    self.IMag_ax.set_ylabel('Z in mm')
                                    self.IPha_ax.set_xlabel('X in mm')
                                    self.IPha_ax.set_ylabel('Z in mm')
                                
                            else:
                                self.IMag_ax.axis('off')
                                self.IPha_ax.axis('off')
                                
                            self.image_positions = np.linspace(params.motor_start_position - params.motor_movement_step/2 + (params.slicethickness/params.SPEsteps)/2, params.motor_end_position + params.motor_movement_step/2 - (params.slicethickness/params.SPEsteps)/2, num=params.img_st_mag.shape[0])

                            if params.autofreqoffset == 1:
                                self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                            else:
                                self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                                
                    self.IMag_canvas.draw()
                    self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                    self.IMag_canvas.setGeometry(420, 40, 575, 470)
                    self.IPha_canvas.draw()
                    self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
                    self.IPha_canvas.setGeometry(1005, 40, 575, 470)

                    self.IMag_canvas.show()
                    self.IPha_canvas.show()
                
        else:
            self.all_fig = Figure()
            self.all_canvas = FigureCanvas(self.all_fig)
            self.all_fig.set_facecolor('None')
            
            
            if params.imageorientation == 'XY' or params.imageorientation == 'ZY':
                gs = GridSpec(2, params.img_st_mag.shape[0], figure=self.all_fig)

                for n in range(params.img_st_mag.shape[0]):
                    self.IMag_ax = self.all_fig.add_subplot(gs[0, n])
                    self.IMag_ax.grid(False)
                    self.IPha_ax = self.all_fig.add_subplot(gs[1, n])
                    self.IPha_ax.grid(False)
                    
                    self.FOV_1 = params.FOV
                    if params.motor_movement_step <= params.FOV:
                        self.FOV_2 = params.motor_total_image_length + params.motor_movement_step
                        self.FOV_2_start = params.motor_start_position - params.motor_movement_step/2
                        self.FOV_2_end = params.motor_end_position + params.motor_movement_step/2
                    else:
                        self.FOV_2 = params.motor_total_image_length + params.FOV
                        self.FOV_2_start = params.motor_start_position - params.FOV/2
                        self.FOV_2_end = params.motor_end_position + params.FOV/2
                        
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    else: self.IMag_ax.imshow(params.img_st_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                    else: self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray', extent=[(-self.FOV_1 / 2), (self.FOV_1 / 2), self.FOV_2_start, self.FOV_2_end])
                        
                    if params.image_grid == 1:
                        self.x_major_ticks = np.arange(math.ceil(-self.FOV_1 / 2), math.floor(self.FOV_1 / 2) + 1, 1)
                        self.y_major_ticks = np.arange(math.ceil(self.FOV_2_start), math.floor(self.FOV_2_end) + 1, 1)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.x_major_ticks)
                        self.IPha_ax.set_yticks(self.y_major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'XY':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Y in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Y in mm')
                        elif params.imageorientation == 'ZY':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('Y in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('Y in mm')
                        
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')
                        
                    self.image_positions = np.linspace(-params.slicethickness/(params.SPEsteps/2)+(params.slicethickness/params.SPEsteps)/2, +params.slicethickness/(params.SPEsteps/2)-(params.slicethickness/params.SPEsteps)/2, params.SPEsteps)

                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        
            elif params.imageorientation == 'YZ' or params.imageorientation == 'YX':
                gs = GridSpec(params.img_st_mag.shape[0], 2, figure=self.all_fig)

                for n in range(params.img_st_mag.shape[0]):
                    self.IMag_ax = self.all_fig.add_subplot(gs[n, 0])
                    self.IMag_ax.grid(False)
                    self.IPha_ax = self.all_fig.add_subplot(gs[n, 1])
                    self.IPha_ax.grid(False)
                    
                    if params.motor_movement_step <= params.FOV:
                        self.FOV_1 = params.motor_total_image_length + params.motor_movement_step
                        self.FOV_1_start = params.motor_start_position - params.motor_movement_step/2
                        self.FOV_1_end = params.motor_end_position + params.motor_movement_step/2
                    else:
                        self.FOV_1 = params.motor_total_image_length + params.FOV
                        self.FOV_1_start = params.motor_start_position - params.FOV/2
                        self.FOV_1_end = params.motor_end_position + params.FOV/2
                    self.FOV_2 = params.FOV
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    else: self.IMag_ax.imshow(params.img_st_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])
                    else: self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray', extent=[self.FOV_1_start, self.FOV_1_end, (-self.FOV_2 / 2), (self.FOV_2 / 2)])  
                        
                    if params.image_grid == 1:
                        self.x_major_ticks = np.arange(math.ceil(self.FOV_1_start), math.floor(self.FOV_1_end) + 1, 1)
                        self.y_major_ticks = np.arange(math.ceil(-self.FOV_2 / 2), math.floor(self.FOV_2 / 2) + 1, 1)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.x_major_ticks)
                        self.IMag_ax.set_yticks(self.y_major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.x_major_ticks)
                        self.IPha_ax.set_yticks(self.y_major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'YZ':
                            self.IMag_ax.set_xlabel('Y in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        elif params.imageorientation == 'YX':
                            self.IMag_ax.set_xlabel('Y in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('Y in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')
                        
                    self.image_positions = np.linspace(-params.slicethickness/(params.SPEsteps/2)+(params.slicethickness/params.SPEsteps)/2, +params.slicethickness/(params.SPEsteps/2)-(params.slicethickness/params.SPEsteps)/2, params.SPEsteps)

                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                      
            elif params.imageorientation == 'ZX' or params.imageorientation == 'XZ':
                gs = GridSpec(2, params.img_st_mag.shape[0], figure=self.all_fig)

                for n in range(params.img_st_mag.shape[0]):
                    self.IMag_ax = self.all_fig.add_subplot(gs[0, n])
                    self.IMag_ax.grid(False)
                    self.IPha_ax = self.all_fig.add_subplot(gs[1, n])
                    self.IPha_ax.grid(False)
                    
                    if params.imagefilter == 1: self.IMag_ax.imshow(params.img_st_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    else: self.IMag_ax.imshow(params.img_st_mag[n, :, :], cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    if params.imagefilter == 1: self.IPha_ax.imshow(params.img_st_pha[n, :, :], interpolation='gaussian', cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                    else: self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray', extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
                        
                    
                    if params.image_grid == 0:
                        self.major_ticks = np.arange(math.ceil((-params.FOV / 2)), math.floor((params.FOV / 2)) + 1, 1)
                        
                        self.IMag_ax.axis('on')
                        self.IMag_ax.set_xticks(self.major_ticks)
                        self.IMag_ax.set_yticks(self.major_ticks)
                        self.IMag_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IMag_ax.grid(which='major', visible=True)
                        
                        self.IPha_ax.axis('on')
                        self.IPha_ax.set_xticks(self.major_ticks)
                        self.IPha_ax.set_yticks(self.major_ticks)
                        self.IPha_ax.grid(which='major', color='#CCCCCC', linestyle='-')
                        self.IPha_ax.grid(which='major', visible=True)
                        
                        if params.imageorientation == 'ZX':
                            self.IMag_ax.set_xlabel('Z in mm')
                            self.IMag_ax.set_ylabel('X in mm')
                            self.IPha_ax.set_xlabel('Z in mm')
                            self.IPha_ax.set_ylabel('X in mm')
                        elif params.imageorientation == 'XZ':
                            self.IMag_ax.set_xlabel('X in mm')
                            self.IMag_ax.set_ylabel('Z in mm')
                            self.IPha_ax.set_xlabel('X in mm')
                            self.IPha_ax.set_ylabel('Z in mm')
                        
                    else:
                        self.IMag_ax.axis('off')
                        self.IPha_ax.axis('off')
                    
                    self.image_positions = np.linspace(params.motor_start_position - params.motor_movement_step/2 + (params.slicethickness/params.SPEsteps)/2, params.motor_end_position + params.motor_movement_step/2 - (params.slicethickness/params.SPEsteps)/2, num=params.img_st_mag.shape[0])

                    if params.autofreqoffset == 1:
                        self.IMag_ax.set_title('Magnitude Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ ' + str(self.image_positions[n] + params.sliceoffset) + 'mm (' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                    else:
                        self.IMag_ax.set_title('Magnitude Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')
                        self.IPha_ax.set_title('Phase Image @ Offset' + str(params.slicethickness / params.SPEsteps) + 'mm)')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1160, 950)
            self.all_canvas.show()

    def imaging_diff_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure()
            self.IMag_canvas = FigureCanvas(self.IMag_fig)
            self.IMag_fig.set_facecolor('None')
            self.IDiff_fig = Figure()
            self.IDiff_canvas = FigureCanvas(self.IDiff_fig)
            self.IDiff_fig.set_facecolor('None')
            self.IComb_fig = Figure()
            self.IComb_canvas = FigureCanvas(self.IComb_fig)
            self.IComb_fig.set_facecolor('None')
            self.IPha_fig = Figure()
            self.IPha_canvas = FigureCanvas(self.IPha_fig)
            self.IPha_fig.set_facecolor('None')
            self.kMag_fig = Figure()
            self.kMag_canvas = FigureCanvas(self.kMag_fig)
            self.kMag_fig.set_facecolor('None')
            self.kPha_fig = Figure()
            self.kPha_canvas = FigureCanvas(self.kPha_fig)
            self.kPha_fig.set_facecolor('None')

            self.IMag_ax = self.IMag_fig.add_subplot(111)
            self.IMag_ax.grid(False)
            self.IDiff_ax = self.IDiff_fig.add_subplot(111)
            self.IDiff_ax.grid(False)
            self.IComb_ax = self.IComb_fig.add_subplot(111)
            self.IComb_ax.grid(False)
            self.IPha_ax = self.IPha_fig.add_subplot(111)
            self.IPha_ax.grid(False)
            self.kMag_ax = self.kMag_fig.add_subplot(111)
            self.kMag_ax.grid(False)
            self.kPha_ax = self.kPha_fig.add_subplot(111)
            self.kPha_ax.grid(False)

            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
            else: self.IMag_ax.imshow(params.img_mag, cmap='gray')
            self.IMag_ax.axis('off')
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IDiff_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap)
            self.IDiff_ax.axis('off')
            self.IDiff_ax.set_aspect(1.0 / self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            self.IComb_ax.axis('off')
            self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray')
            else: self.IPha_ax.imshow(params.img_pha, cmap='gray')
            self.IPha_ax.axis('off')
            self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno')
                self.kMag_ax.axis('off')
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno')
                self.kMag_ax.axis('off')
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno')
            self.kPha_ax.axis('off')
            self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
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
            self.all_fig = Figure()
            self.all_canvas = FigureCanvas(self.all_fig)
            self.all_fig.set_facecolor('None')

            gs = GridSpec(2, 3, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(gs[0, 0])
            self.IMag_ax.grid(False)
            self.IDiff_ax = self.all_fig.add_subplot(gs[0, 1])
            self.IDiff_ax.grid(False)
            self.IComb_ax = self.all_fig.add_subplot(gs[0, 2])
            self.IComb_ax.grid(False)
            self.IPha_ax = self.all_fig.add_subplot(gs[1, 0])
            self.IPha_ax.grid(False)
            self.kMag_ax = self.all_fig.add_subplot(gs[1, 1])
            self.kMag_ax.grid(False)
            self.kPha_ax = self.all_fig.add_subplot(gs[1, 2])
            self.kPha_ax.grid(False)

            if params.imagefilter == 1: self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
            else: self.IMag_ax.imshow(params.img_mag, cmap='gray')
            self.IMag_ax.axis('off')
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IDiff_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap)
            self.IDiff_ax.axis('off')
            self.IDiff_ax.set_aspect(1.0 / self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            self.IComb_ax.axis('off')
            self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
            if params.imagefilter == 1: self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray')
            else: self.IPha_ax.imshow(params.img_pha, cmap='gray')
            self.IPha_ax.axis('off')
            self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno')
                self.kMag_ax.axis('off')
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno')
                self.kMag_ax.axis('off')
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno')
            self.kPha_ax.axis('off')
            self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1300, 750)
            self.all_canvas.show()
            
    def save_spectrum_data(self):
        if params.GUImode == 0:
            self.datatxt = np.matrix(np.zeros((params.freqencyaxis.shape[0], 2)))
            self.datatxt[:, 0] = params.freqencyaxis.reshape(params.freqencyaxis.shape[0], 1)
            self.datatxt[:, 1] = params.spectrumfft
            
            if params.agriMRI_mode == 1:
                self.datapath_temp = ''
                self.datapath_temp = params.datapath
                self.agriMRI_folder_structure_temp = ''
                self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Spectrum_data'
                if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                np.savetxt(params.datapath + '_Spectrum_data.txt', self.datatxt)
                params.datapath = self.datapath_temp
                params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
            else: np.savetxt('data/Spectrum_data/' + params.datapath + '_Spectrum_data.txt', self.datatxt)
            
            print('Spectrum data saved!')
        elif params.GUImode == 2:
            self.datatxt = np.matrix(np.zeros((params.T1xvalues.shape[0], 3)))
            self.datatxt[:, 0] = params.T1xvalues.reshape(params.T1xvalues.shape[0], 1)
            self.datatxt[:, 1] = params.T1yvalues1.reshape(params.T1yvalues1.shape[0], 1)
            self.datatxt[:, 2] = params.T1regyvalues1.reshape(params.T1regyvalues1.shape[0], 1)
            
            if params.agriMRI_mode == 1:
                self.datapath_temp = ''
                self.datapath_temp = params.datapath
                self.agriMRI_folder_structure_temp = ''
                self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/T_data'
                if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                np.savetxt(params.datapath + '_T1_data.txt', self.datatxt)
                params.datapath = self.datapath_temp
                params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
            else: np.savetxt('data/T_data/' + params.datapath + '_T1_data.txt', self.datatxt)
            
            print('T1 data saved!')
        elif params.GUImode == 3:
            self.datatxt = np.matrix(np.zeros((params.T2xvalues.shape[0], 3)))
            self.datatxt[:, 0] = params.T2xvalues.reshape(params.T2xvalues.shape[0], 1)
            self.datatxt[:, 1] = params.T2yvalues.reshape(params.T2yvalues.shape[0], 1)
            self.datatxt[:, 2] = params.T2regyvalues.reshape(params.T2regyvalues.shape[0], 1)
            
            if params.agriMRI_mode == 1:
                self.datapath_temp = ''
                self.datapath_temp = params.datapath
                self.agriMRI_folder_structure_temp = ''
                self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/T_data'
                if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                np.savetxt(params.datapath + '_T2_data.txt', self.datatxt)
                params.datapath = self.datapath_temp
                params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
            else: np.savetxt('data/T_data/' + params.datapath + '_T2_data.txt', self.datatxt)
            
            print('T2 data saved!')

    def save_mag_image_data(self):
        if params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36:
                self.datatxt = np.matrix(np.zeros((params.img_mag.shape[1], params.img_mag.shape[0] * params.img_mag.shape[2])))
                for m in range(params.img_mag.shape[0]):
                    self.datatxt[:, m * params.img_mag.shape[2]:m * params.img_mag.shape[2] + params.img_mag.shape[2]] = params.img_mag[m, :, :]
                
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_3D_Magnitude_Image_data.txt', self.datatxt)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_3D_Magnitude_Image_data.txt', self.datatxt)
                
                print('Magnitude 3D image data saved!')
            elif params.sequence == 14 or params.sequence == 31:
                print('WIP! (Diffusion)')
            elif params.sequence == 15 or params.sequence == 16 or params.sequence == 32 or params.sequence == 33:
                print('WIP! (Flow compensation)')
            else:
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_Magnitude_Image_data.txt', params.img_mag)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_Magnitude_Image_data.txt', params.img_mag)
                
                print('Magnitude image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 10:
                #print('WIP!')
                self.datatxt = np.matrix(np.zeros((params.img_st_mag.shape[1], params.img_st_mag.shape[0] * params.img_st_mag.shape[2])))
                for m in range(params.img_st_mag.shape[0]):
                    self.datatxt[:, m * params.img_st_mag.shape[2]:m * params.img_st_mag.shape[2] + params.img_st_mag.shape[2]] = params.img_st_mag[m, :, :]
                
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_3D_Magnitude_Image_Stitching_data.txt', self.datatxt)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_3D_Magnitude_Image_Stitching_data.txt', self.datatxt)
                
                print('Magnitude 3D image stitching data saved!')
            else:
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_Magnitude_Image_Stitching_data.txt', params.img_st_mag)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_Magnitude_Image_Stitching_data.txt', params.img_st_mag)
                
                print('Magnitude image stitching data saved!')

    def save_pha_image_data(self):
        if params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36:
                self.datatxt = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0] * params.img_pha.shape[2])))
                for m in range(params.img_pha.shape[0]):
                    self.datatxt[:, m * params.img_pha.shape[2]:m * params.img_pha.shape[2] + params.img_pha.shape[2]] = params.img_pha[m, :, :]
                
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_3D_Phase_Image_data.txt', self.datatxt)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_3D_Phase_Image_data.txt', self.datatxt)
                
                print('Phase 3D image data saved!')
            elif params.sequence == 14 or params.sequence == 31:
                print('WIP! (Diffusion)')
            elif params.sequence == 15 or params.sequence == 16 or params.sequence == 32 or params.sequence == 33:
                print('WIP! (Flow compensation)')
            else:
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_Phase_Image_data.txt', params.img_pha)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_Phase_Image_data.txt', params.img_pha)
                
                print('Phase image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 10:
                #print('WIP!')
                self.datatxt = np.matrix(np.zeros((params.img_st_pha.shape[1], params.img_st_pha.shape[0] * params.img_st_pha.shape[2])))
                for m in range(params.img_st_pha.shape[0]):
                    self.datatxt[:, m * params.img_st_pha.shape[2]:m * params.img_st_pha.shape[2] + params.img_st_pha.shape[2]] = params.img_st_pha[m, :, :]
                
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_3D_Phase_Image_Stitching_data.txt', self.datatxt)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_3D_Phase_Image_Stitching_data.txt', self.datatxt)
                
                print('Phase 3D image stitching data saved!')
            else:
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_Phase_Image_Stitching_data.txt', params.img_st_pha)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_Phase_Image_Stitching_data.txt', params.img_st_pha)
                
                print('Phase image stitching data saved!')

    def save_image_data(self):
        if params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36:
                self.datatxt = np.matrix(np.zeros((params.img.shape[1], params.img.shape[0] * params.img.shape[2])))
                for m in range(params.img.shape[0]):
                    self.datatxt[:, m * params.img.shape[2]:m * params.img.shape[2] + params.img.shape[2]] = params.img[m, :, :]
                
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_3D_Image_data.txt', self.datatxt)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_3D_Image_data.txt', self.datatxt)
                
                print('3D image data saved!')
            elif params.sequence == 14 or params.sequence == 31:
                print('WIP! (Diffusion)')
            elif params.sequence == 15 or params.sequence == 16 or params.sequence == 32 or params.sequence == 33:
                print('WIP! (Flow compensation)')
            else:
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_Image_data.txt', params.img)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_Image_data.txt', params.img)
                
                print('Image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 10:
                #print('WIP!')
                self.datatxt = np.matrix(np.zeros((params.img_st.shape[1], params.img_st.shape[0] * params.img_st.shape[2])))
                for m in range(params.img_st.shape[0]):
                    self.datatxt[:, m * params.img_st.shape[2]:m * params.img_st.shape[2] + params.img_st.shape[2]] = params.img_st[m, :, :]
                
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_3D_Image_Stitching_data.txt', self.datatxt)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_3D_Image_Stitching_data.txt', self.datatxt)
                
                print('3D image stitching data saved!')
            else:
                if params.agriMRI_mode == 1:
                    self.datapath_temp = ''
                    self.datapath_temp = params.datapath
                    self.agriMRI_folder_structure_temp = ''
                    self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.agriMRI_folder_structure = params.agriMRI_folder_structure + '/Image_data'
                    if os.path.isdir(params.agriMRI_folder_structure) != True: os.mkdir(params.agriMRI_folder_structure)
                    params.datapath = params.agriMRI_folder_structure + '/' + params.datapath
                    np.savetxt(params.datapath + '_Image_Stitching_data.txt', params.img_st)
                    params.datapath = self.datapath_temp
                    params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp
                else: np.savetxt('data/Image_data/' + params.datapath + '_Image_Stitching_data.txt', params.img_st)
                
                print('Image stitching data saved!')
        
    def view_3D_layers(self):
        if self.dialog_3D_layers == None:
            self.dialog_3D_layers = View3DLayersDialog(parent = self)
            self.dialog_3D_layers.show()
        else:
            self.dialog_3D_layers.hide()
            self.dialog_3D_layers.show()
    
    def animate(self):
        if params.GUImode == 1 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 17 \
                                    or params.sequence == 18):
            #Radial full
            proc.animate_radial_full()
        elif params.GUImode == 1 and (params.sequence == 2 or params.sequence == 3 or params.sequence == 19 \
                                      or params.sequence == 20):
            #Radial half
            proc.animate_radial_half()
        elif params.GUImode == 1 and (params.sequence == 4 or params.sequence == 5 or params.sequence == 7 \
                                      or params.sequence == 8 or params.sequence == 9  or params.sequence == 10 \
                                      or params.sequence == 15  or params.sequence == 16 or params.sequence == 21 \
                                      or params.sequence == 22 or params.sequence == 24 or params.sequence == 25 \
                                      or params.sequence == 26 or params.sequence == 27 or params.sequence == 32 \
                                      or params.sequence == 33):
            #Cartesian
            proc.animate_cartesian()
        elif params.GUImode == 1 and (params.sequence == 6 or params.sequence == 23):
            #Cartesian in-out
            proc.animate_cartesian_IO()
        elif params.GUImode == 1 and (params.sequence == 11 or params.sequence == 28):
            #TSE
            print('\033[1m' + 'WIP' + '\033[0m')
        elif params.GUImode == 1 and (params.sequence == 12 or params.sequence == 13 or params.sequence == 29 \
                                       or params.sequence == 30):
            #EPI
            print('\033[1m' + 'WIP' + '\033[0m')
        else: print('Sequence not defined!')
        
    def histogram(self):
        if params.imagecolormap == 'viridis':
            cm = plt.cm.viridis
        elif params.imagecolormap == 'jet':
            cm = plt.cm.jet
        elif params.imagecolormap == 'gray':
            cm = plt.cm.gray
        elif params.imagecolormap == 'bone':
            cm = plt.cm.bone
        elif params.imagecolormap == 'inferno':
            cm = plt.cm.inferno
        elif params.imagecolormap == 'plasma':
            cm = plt.cm.plasma
        
        self.hist_fig = Figure()
        self.hist_canvas = FigureCanvas(self.hist_fig)
        self.hist_fig.set_facecolor('None')

        self.hist_ax = self.hist_fig.add_subplot(111)
        self.hist_ax.grid(False)

        if params.GUImode == 1:
            N, bins, patches = self.hist_ax.hist(params.img_mag.reshape(-1), bins=50, range=(params.imageminimum, params.imagemaximum))
        elif params.GUImode == 5:
            N, bins, patches = self.hist_ax.hist(params.img_st_mag.reshape(-1), bins=50, range=(params.imageminimum, params.imagemaximum))
        
        for i, p in enumerate(patches):
            plt.setp(p, 'facecolor', cm(i/50))
            
        self.hist_ax.set_xlim([params.imageminimum, params.imagemaximum])
        
        self.hist_canvas.draw()
        self.hist_canvas.setWindowTitle('Histogram - ' + params.datapath + '.txt')
        self.hist_canvas.setGeometry(10, 490, 400, 350)
        self.hist_canvas.show()
        
class SerialReader(QObject):
    data_received =pyqtSignal(str)
    
    class Type(Enum):
        SAR = 0
        MOTOR = 1
    
    def __init__(self, serial_port, type=Type.SAR):
        super().__init__()
        self.type = type
        self.serial_port = serial_port
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial)
        self.timer.start(100)
        
    def read_serial(self):
        if self.serial_port.inWaiting() > 0:
            data = self.decode_data(self.my_readline())
            self.serial_port.flushOutput()
            self.data_received.emit(data)
            
    def decode_data(self,byte_data):
        byte_data = byte_data[:-2]
        
        if(self.type == self.Type.MOTOR):
            self.message = byte_data
            return self.message.decode('utf-8')
        else:
            if len(byte_data)< 4:
                return 'MTS'
            self.message = byte_data[:-4]
            self.checksum_recived = byte_data[-4:]
            self.checksum_calculated = zlib.crc32(self.message).to_bytes(4,'big')
            if self.checksum_recived == self.checksum_calculated:
                return self.message.decode()
            else:
                return 'CSC'
        
    def my_readline(self):
        self.buffer = bytearray()
        while self.buffer[-2:] != b'\r\n' and self.serial_port.inWaiting() > 0:       
            self.buffer += self.serial_port.read(1)    
        return self.buffer


class SARMonitorWindow(SAR_Window_Form, SAR_Window_Base):
    connected = pyqtSignal()
    
    trigger_no_sar = pyqtSignal()
    
    def __init__(self, parent=None):
        super(SARMonitorWindow, self).__init__(parent)
        self.setupUi(self)
        
        self.load_params()        
        params.loadSarCal()
        self.ui = loadUi('ui/sar.ui')
        self.setWindowTitle('SAR Monitor')
        self.setGeometry(420, 40, 540, 470)
        
        self.SAR_Cal_pushButton.setEnabled(False)
        self.SAR_Send_Lookup_pushButton.setEnabled(False)
        self.SAR_New_Pat_pushButton.setEnabled(False)
        self.SAR_Error_Clear_pushButton.setEnabled(False)
        self.SAR_Log_Data_pushButton.setEnabled(False)
        
        self.SAR_Enable_radioButton.toggled.connect(self.update_params)
        
        self.SAR_Limit_doubleSpinBox.setKeyboardTracking(False)
        self.SAR_Limit_doubleSpinBox.valueChanged.connect(self.update_params)
        self.SAR_6mLimit_doubleSpinBox.setKeyboardTracking(False)
        self.SAR_6mLimit_doubleSpinBox.valueChanged.connect(self.update_params)
        self.SAR_Tran_doubleSpinBox.setKeyboardTracking(False)
        self.SAR_Tran_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.SAR_Max_Power_doubleSpinBox.setKeyboardTracking(False)
        self.SAR_Max_Power_doubleSpinBox.valueChanged.connect(self.update_params)
        
        self.SAR_Stop_pushButton.clicked.connect(self.stop_sar)
        
        self.SAR_New_Pos_pushButton.setEnabled(False)
        self.SAR_Error_Clear_pushButton.clicked.connect(self.err_clear)
        
        self.SAR_New_Pat_pushButton.clicked.connect(self.new_pat)
        self.SAR_New_Pos_pushButton.clicked.connect(self.new_pos)
        
        self.SAR_Log_Data_pushButton.clicked.connect(self.load_data)
        
        self.SAR_Power_W_pushButton.clicked.connect(self.power_in_mW)
        self.SAR_Power_dBm_pushButton.clicked.connect(self.power_in_dBm)
        
        self.SAR_Cal_pushButton.clicked.connect(self.load_cal_data)
        self.SAR_Calc_Lookup_pushButton.clicked.connect(self.calc_lookup)
        self.SAR_Send_Lookup_pushButton.clicked.connect(self.send_lookup)
        
        self.serial=None
        if self.serial_init():
            QTimer.singleShot(1,self.post_init)
            return
        
        self.save_var = 0
        self.array_count=0
        self.err_count=0
        
        self.data_array = []
        
        self.folder_path = 'sar/sardata'            
        self.cal_path = 'sar/sarcal'
        self.log_path = 'sar/sarlog'
            
        params.SAR_status='com'
        
        self.SAR_10sLimit_lineEdit.setReadOnly(True)
        self.SAR_6mLimit_lineEdit.setReadOnly(True)
        self.SAR_PeakLimit_lineEdit.setReadOnly(True)
        
        self.last_Data=''
        self.log_init()

    
    def post_init(self):
        self.trigger_no_sar.emit()
        
    def serial_init(self):       
        ports = list(serial.tools.list_ports.comports())        
        for port in ports:
            try:
                self.serial = serial.Serial(port.device, 112500, timeout=0.5, rtscts=False, xonxoff=False)
                self.serial.setRTS(False)
                mes = b'ident\x04\x4e\x78\xb2\r\n\t'
                if self.serial.inWaiting()==0:
                    self.serial.write(mes)
                    response= self.serial.readline()
                    if response[0:6] == b'sar2.0':
                        self.serial.setRTS(False)
                        self.serial_reader=SerialReader(self.serial)
                        self.serial_reader.data_received.connect(self.on_serial_data_received)
                        print(f'SAR-Monitor connected to port: {port}')
                        print(params.connectionmode)
                        self.SAR_Cal_pushButton.setEnabled(params.connectionmode)
                        self.SAR_Send_Lookup_pushButton.setEnabled(True)
                        self.SAR_New_Pat_pushButton.setEnabled(True)
                        self.SAR_Error_Clear_pushButton.setEnabled(True)
                        self.SAR_Log_Data_pushButton.setEnabled(True)
                        
                        return False               
                self.serial.close()
                
            except Exception as e:
                    print(f'Could not write to port: {port} - {e}')
           
        return True 
        
    def log_init(self):
        params.SAR_LOG_counter += 1
        self.time = datetime.datetime.now().strftime('%d-%m-%Y')
        self.file_name = f'SAR_Log_{params.SAR_LOG_counter}.txt'
        
        if params.SAR_LOG_counter==10:
            params.SAR_LOG_counter=0
            
        self.logfile_path = os.path.join(self.log_path,self.file_name)
        
        if os.path.exists(self.logfile_path):
            os.remove(self.logfile_path)
        
        with open(self.logfile_path,'a') as file:
            file.writelines(f'Date: {self.time}\n')
    
    def power_in_mW(self):
        params.SAR_power_unit='mW'
        self.SAR_Power_W_pushButton.setEnabled(False)
        self.SAR_Power_dBm_pushButton.setEnabled(True)
        
        self.label_10s.setText('SAR 10s Limit [mW]')
        self.label_6m.setText('SAR 6m Limit [mW]')
        self.label_peak.setText('Peak Limit [mW]')
        
        self.label_MaxP.setText('Max. Amplifier Power [mW]')
        
        params.SAR_limit=round(self.dBm_to_mW(params.SAR_limit),2)
        self.SAR_Limit_doubleSpinBox.setValue(params.SAR_limit)
        
        params.SAR_6mlimit=round(self.dBm_to_mW(params.SAR_6mlimit),2)
        self.SAR_6mLimit_doubleSpinBox.setValue(params.SAR_6mlimit)
        
        params.SAR_peak_limit=round(self.dBm_to_mW(params.SAR_peak_limit),2)
        self.SAR_Tran_doubleSpinBox.setValue(params.SAR_peak_limit)
        
        params.SAR_max_power = round(self.dBm_to_mW(params.SAR_max_power),2)
        self.SAR_Max_Power_doubleSpinBox.setValue(params.SAR_max_power)
        
        params.saveFileParameter()
        
        if self.SAR_10sLimit_lineEdit.text() != '':
            self.SAR_10sLimit_lineEdit.setText(f'{round(self.dBm_to_mW(float(self.SAR_10sLimit_lineEdit.text())),1)}')
            self.SAR_6mLimit_lineEdit.setText(f'{round(self.dBm_to_mW(float(self.SAR_6mLimit_lineEdit.text())),1)}')
            self.SAR_PeakLimit_lineEdit.setText(f'{round(self.dBm_to_mW(float(self.SAR_PeakLimit_lineEdit.text())),1)}')
    
    def power_in_dBm(self):
        params.SAR_power_unit='dBm'
        self.SAR_Power_W_pushButton.setEnabled(True)
        self.SAR_Power_dBm_pushButton.setEnabled(False)
        
        self.label_10s.setText('SAR 10s Limit [dBm]')
        self.label_6m.setText('SAR 6m Limit [dBm]')
        self.label_peak.setText('Peak Limit [dBm]')
        
        self.label_MaxP.setText('Max. Amplifier Power [dBm]')
        
        params.SAR_limit=round(self.mW_to_dBm(params.SAR_limit),2)
        self.SAR_Limit_doubleSpinBox.setValue(params.SAR_limit)
        
        params.SAR_6mlimit=round(self.mW_to_dBm(params.SAR_6mlimit),2)
        self.SAR_6mLimit_doubleSpinBox.setValue(params.SAR_6mlimit)
        
        params.SAR_peak_limit=round(self.mW_to_dBm(params.SAR_peak_limit),2)
        self.SAR_Tran_doubleSpinBox.setValue(params.SAR_peak_limit)
        
        params.SAR_max_power = round(self.mW_to_dBm(params.SAR_max_power),2)
        self.SAR_Max_Power_doubleSpinBox.setValue(params.SAR_max_power)
        
        params.saveFileParameter()
        
        if self.SAR_10sLimit_lineEdit.text() != '':
            self.SAR_10sLimit_lineEdit.setText(f'{round(self.mW_to_dBm(float(self.SAR_10sLimit_lineEdit.text())),1)}')
            self.SAR_6mLimit_lineEdit.setText(f'{round(self.mW_to_dBm(float(self.SAR_6mLimit_lineEdit.text())),1)}')
            self.SAR_PeakLimit_lineEdit.setText(f'{round(self.mW_to_dBm(float(self.SAR_PeakLimit_lineEdit.text())),1)}')
        
    def dBm_to_mW(self,P_dBm):
        return (10**(P_dBm/10))
    
    def mW_to_dBm(self,P_mW):
        return 10*math.log10(P_mW)
               
    def load_cal_data(self):
        print('load cal')
        
        msg_box  = QMessageBox()
        msg_box.setWindowTitle('Load Calibration Data')
        msg_box.setText('Loading the calibration data may take up to 15 minutes and will overwrite the raw data of the last SAR measurement. Do you still want to proceed?')
        msg_box.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        result = msg_box.exec()
        
        if result == QMessageBox.Yes:
            self.GUImode_temp = 0
            self.GUImode_temp = params.GUImode
            self.sequence_temp = 0
            self.sequence_temp = params.sequence
            
            params.GUImode = 0
            params.sequence = 27
            #params.saveFileParameter()
                    
            self.data_array.clear()
            
            self.write_message('raw')
            seq.sequence_upload()
            
            params.GUImode = self.GUImode_temp
            params.sequence = self.sequence_temp
            
            self.overlay = Overlay(self)
        else:
            print('No')
        
    def calc_lookup(self):
        params.loadSarCal()
        if params.SAR_cal_raw == []:
            print('No SAR calibration raw data!')
        else:
            if list!=type(params.SAR_cal_raw):
                params.SAR_cal_raw = params.SAR_cal_raw.tolist()
                
            self.find_plateau(params.SAR_cal_raw[0][0:2500])
            
            x=params.SAR_cal_mean
            x_new=np.linspace(0,4096-1,4096)
            if params.SAR_power_unit == 'dBm':
                y=np.concatenate(([0],np.linspace(0,int(self.convert_tran((10**(params.SAR_max_power/10)))),21)[3:]))
            if params.SAR_power_unit == 'mW':
                y=np.concatenate(([0],np.linspace(0,int(self.convert_tran(params.SAR_max_power)),21)[3:]))
            y_new = np.array([int(np.ceil(self.linear_extrapolation(xi,x,y))) for xi in x_new])
            params.SAR_cal_lookup=y_new**2
            
            params.saveFileParameter()
            
            self.cal_plot()

            
    def send_lookup(self):
        if params.SAR_cal_lookup == []:
            print('No lookup data!')
        else:
            msg_box  = QMessageBox()
            msg_box.setWindowTitle('Send lookup table')
            msg_box.setText('Check if all plateuaus have been correctly identified and the lookup table is correct. Press Yes to send the lookup table.')
            msg_box.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)
            result = msg_box.exec()
            if result == QMessageBox.Yes:
                self.save_var=11
                self.command= f'c0:{params.SAR_cal_lookup[0]}'
                self.write_message(self.command)
                self.array_count=1
                self.overlay = Overlay(self)
             
    def write_message(self,data):
        with open(self.logfile_path,'a') as file:
            self.time = datetime.datetime.now().strftime('%H-%M-%S')
            file.writelines(f'send({self.time}): {data}\n')
        
        self.data_bytes = data.encode('utf-8')
        self.checksum_byte = struct.pack('>I',zlib.crc32(data.encode('utf-8')))
        self.delimiter_bytes = '\r\n\t'.encode('utf-8')
        self.message = self.data_bytes + self.checksum_byte + self.delimiter_bytes
        print(self.message)
        self.serial.write(self.message)
        
    def convert_limit(self,limit):
        if params.SAR_power_unit == 'dBm':
            limit=(10**(limit/10))/1000
        if params.SAR_power_unit == 'mW':
            limit=limit/1000
        m=1.9698
        b=0.0017
        Norm= 3.3/4095
        return str(math.floor(((math.sqrt(limit*50)*m+b)**2)/Norm**2))

    def convert_tran(self,limit):
        if params.SAR_power_unit == 'dBm':
            limit=(10**(limit/10))/1000
        if params.SAR_power_unit == 'mW':
            limit=limit/1000
        m=1.9698
        b=0.0017
        Norm= 3.3/4095
        return str(math.floor(((math.sqrt(limit*50)*m+b))/Norm))

    def stop_sar(self):
        params.SAR_status = 1
        self.write_message('s') 
        params.SAR_limit=0
        params.SAR_6mlimit=0
        params.SAR_peak_limit=0
        self.SAR_Limit_doubleSpinBox.setValue(0.0)
        self.SAR_6mLimit_doubleSpinBox.setValue(0.0)
        self.SAR_Tran_doubleSpinBox.setValue(0.0)
        
    def new_pat(self):      
        params.SAR_LOG_counter += 1
        self.time = datetime.datetime.now().strftime('%d-%m-%Y')
        self.file_name = f'SAR_Log_{params.SAR_LOG_counter}.txt'      
        if params.SAR_LOG_counter==10:
            params.SAR_LOG_counter=0    
        self.logfile_path = os.path.join(self.log_path,self.file_name)
        if os.path.exists(self.logfile_path):
            os.remove(self.logfile_path)
        with open(self.logfile_path,'a') as file:
                    file.writelines(f'Date: {self.time}\n')
        self.SAR_New_Pat_pushButton.setEnabled(False)
        self.write_message('s')
        time.sleep(0.1)
        self.save_var=21
        
    def new_pos(self): 
        if params.SAR_status == 'samp':
            self.SAR_New_Pos_pushButton.setEnabled(False)
            self.write_message('s')
            time.sleep(0.1)
            self.save_var=22
            
    def err_clear(self):
        self.SAR_New_Pat_pushButton.setEnabled(True)
        if params.SAR_status == 'com': self.SAR_Status_lineEdit.setText('Communication')
        self.SAR_New_Pos_pushButton.setEnabled(False)
        
    def load_data(self):       
        self.time = datetime.datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        self.file_name = f'SAR_Data_{params.SAR_LOG_counter}.txt'   
        self.file_path = os.path.join(self.folder_path,self.file_name)
        if os.path.exists(self.logfile_path):
            os.remove(self.logfile_path)    
        with open(self.logfile_path,'a') as file:
            file.writelines(f'Date: {self.time}\n')
        self.save_var = 1      
        self.data_array.clear()       
        self.write_message('r6min')        
        self.overlay = Overlay(self)      
        
    def cal_plot(self):        
        self.fig = Figure()
        self.fig.set_facecolor('None')
        self.fig_canvas = FigureCanvas(self.fig)

        self.ax1 = self.fig.add_subplot(3, 1, 1)
        self.ax1.plot(np.linspace(0,2499,2500), params.SAR_cal_raw[0][0:2500], '-', linewidth=0.5)
        for n in range(len(params.SAR_cal_mean)-1):
            start = params.SAR_cal_start[n]
            end = params.SAR_cal_end[n+1]
            self.ax1.plot(np.linspace(start,end,(end-start)), params.SAR_cal_raw[0][start:end], '.', color='#0000BB')
            self.ax1.axhline(y=params.SAR_cal_mean[n+1], color='#0000BB', linestyle='--')
        self.ax1.set_xlim([0, 2500])
        self.ax1.set_title('Calibration Rawdata')
        self.ax1.set_ylabel('ADC')
        self.ax1.set_xlabel('time [ms]')
        self.major_ticks = params.SAR_cal_mean
        self.ax1.set_yticks(self.major_ticks, minor=False)
        self.ax1.grid(which='major', color='#888888', linestyle='-')
        self.ax1.grid(which='major', visible=True)
            
        self.ax2 = self.fig.add_subplot(3, 1, 2)
        if params.SAR_power_unit == 'dBm':
            self.ax2.plot(np.concatenate(([0],np.linspace(0,(10**(params.SAR_max_power/10)),21)[3:])),params.SAR_cal_mean ,'o', color='#0000BB')
            self.ax2.set_xlim([0, 10**(params.SAR_max_power/10)])
        if params.SAR_power_unit == 'mW':
            self.ax2.plot(np.concatenate(([0],np.linspace(0,params.SAR_max_power,21)[3:])),params.SAR_cal_mean ,'o', color='#0000BB')
            self.ax2.set_xlim([0, params.SAR_max_power])
        self.ax2.set_title('ADC vs. Amplifier Power')
        self.ax2.set_ylabel('ADC')
        self.ax2.set_xlabel('Power [mW]')
        self.ax2.grid(which='major', color='#888888', linestyle='-')
        self.ax2.grid(which='major', visible=True)

        self.ax3 = self.fig.add_subplot(3, 1, 3)
        self.ax3.plot( np.linspace(0,4095,4096), params.SAR_cal_lookup ,'-', color='#000000')
        self.ax3.plot( params.SAR_cal_mean, np.concatenate(([0],np.linspace(0,int(self.convert_tran(params.SAR_max_power)),21)[3:]))**2 ,'o', color='#0000BB')
        self.ax3.set_xlim([0,4095])
        self.ax3.set_title('Lookup Table')
        self.ax3.set_ylabel('Lookup ADC²')
        self.ax3.set_xlabel('ADC')
        self.ax3.grid(which='major', color='#888888', linestyle='-')
        self.ax3.grid(which='major', visible=True)

        self.fig_canvas.setWindowTitle('SAR Calibration')
        self.fig_canvas.setGeometry(980, 40, 600, 950)
        self.fig_canvas.show()
        
    def linear_extrapolation(self,x_new,x,y):
        if x_new < x[0]:
            return 0
        elif x_new > x[-1]:
            slope=(y[-1]-y[-2])/(x[-1]-x[-2])
            return y[-1]+slope*(x_new-x[-1])
        else:
            return np.interp(x_new,x,y)
    
    def find_plateau(self,sardata):
        threshhold = 150
        steps = 5 
        start = 0
        end = 0
        var = 0
        found = 0
        plats = []
        zeros=np.array([])
        params.SAR_cal_start = []
        params.SAR_cal_end = []
        data = np.convolve(sardata,[1,4,4,-4,-10,-4,4,4,1],mode='same')
        
        i = 20
        params.SAR_cal_end.append(15)
        while i < len(data)-1:
            if data[i] > threshhold:
                found=0
                while data[i] > 0 and i<len(data)-1:
                    i += 1
                var=i
                for a in range(steps):
                    if data[i] < -threshhold:
                        found=1
                    i += 1
                    if i==len(data):
                        i -= 1
                if found==1:
                    start=var
                    arr=np.array(sardata[end+3:start-3])
                    params.SAR_cal_start.append(start+2)
                    zeros=np.concatenate((zeros,arr))
                    found=0
            if data[i] < -threshhold:
                found=0
                while data[i] < 0 and i<len(data)-1:
                    i += 1
                var=i
                for a in range(steps):
                    if data[i] > threshhold:
                        found=1
                    i += 1
                    if i==len(data):
                        i -= 1
                if found==1:
                    end=var
                    params.SAR_cal_end.append(end-2)
                    plats.append(sardata[start+2:end-2])
                    found=0
            i += 1
        
        calmean=[0]
        for plat in plats: 
            calmean.append(int(np.ceil(np.mean(plat))))
        calmean[0]=int(np.ceil(np.mean(zeros)))
        params.SAR_cal_mean=calmean
        
    def on_serial_data_received(self,data):
        print(data)
        if (self.save_var==21 or self.save_var==22) and data == 'err:stop':
            self.write_message('s')
            time.sleep(0.1)
        
        if data == 'SARstop' or data == 'stop':
            if self.save_var==21:
                self.write_message('new pat')       
                self.command= f'l10s{self.convert_limit(params.SAR_limit)}'
                self.write_message(self.command)
                self.command= f'l6m{self.convert_limit(params.SAR_6mlimit)}'
                self.write_message(self.command)
                self.command= f'tran{self.convert_limit(params.SAR_peak_limit)}'
                self.write_message(self.command)
                self.SAR_10sLimit_lineEdit.setText(f'{params.SAR_limit}')
                self.SAR_6mLimit_lineEdit.setText(f'{params.SAR_6mlimit}')
                self.SAR_PeakLimit_lineEdit.setText(f'{params.SAR_peak_limit}')
                self.save_var=0
                self.write_message('start') 
            if self.save_var==22:
                self.command= f'l10s{self.convert_limit(params.SAR_limit)}'
                self.write_message(self.command)
                self.command= f'l6m{self.convert_limit(params.SAR_6mlimit)}'
                self.write_message(self.command)
                self.command= f'tran{self.convert_limit(params.SAR_peak_limit)}'
                self.write_message(self.command)
                self.SAR_10sLimit_lineEdit.setText(f'{params.SAR_limit}')
                self.SAR_6mLimit_lineEdit.setText(f'{params.SAR_6mlimit}')
                self.SAR_PeakLimit_lineEdit.setText(f'{params.SAR_peak_limit}') 
                self.write_message('new pos')
                self.save_var=0    
        
        if self.save_var==11:
            if data.isdigit() == False :
                if self.err_count < 5:
                    self.command= f'c{self.array_count-1}:{params.SAR_cal_lookup[self.array_count-1]}'
                    self.write_message(self.command)
                    self.err_count += 1
                else:
                    print(data)
                    self.save_var=0
                    self.overlay.deleteLater()
            else: 
                self.err_count=0
                if self.array_count < 4096:
                    self.command= f'c{self.array_count}:{params.SAR_cal_lookup[self.array_count]}'
                    self.write_message(self.command)
                    self.array_count+=1
                else:
                    self.save_var=0
                    self.overlay.deleteLater() 
        
        if self.save_var==10: 
            if data.isdigit() == False :
                if self.err_count < 5:
                    self.command= f'rc{self.array_count-1}'
                    self.write_message(self.command)
                    self.err_count += 1
                else:
                    print(data)
                    self.save_var=0
                    self.overlay.deleteLater()
            else: 
                self.err_count=0
                self.data_array.append(int(data))
                if len(self.data_array) > 2499:
                    params.SAR_cal_raw=self.data_array
                    params.saveSarCal()
                    self.file_name = f'SAR_Cal_{params.SAR_LOG_counter}.txt'   
                    self.file_path = os.path.join(self.cal_path,self.file_name)
                    np.savetxt(self.file_path,self.data_array)
                    self.data_array.clear()
                    self.save_var=0
                    self.overlay.deleteLater()
                else:
                    self.command= f'rc{self.array_count}'
                    self.write_message(self.command)
                    self.array_count+=1
                        
        if self.save_var == 0:
            alert = ('tranlimit','reflimit','6minlimit','10slimit')
            ERR = ('MTS','CSC')
            if not(self.last_Data=='SARstop' and data in alert):
                try:
                    with open(self.logfile_path,'a') as file:
                        self.time = datetime.datetime.now().strftime('%H-%M-%S')
                        file.writelines(f'catch({self.time}): {data}\n')
                except AttributeError:
                    print('AttributeError')
            self.last_Data=data    
            if data =='raw ok':
                self.write_message('rc0')
                self.array_count=1
                self.save_var=10
            if data == 'err:re':
                self.overlay.deleteLater()
            if data =='start':
                self.SAR_Status_lineEdit.setText('Sampling')
                time.sleep(1)
                self.SAR_New_Pos_pushButton.setEnabled(True)
                params.SAR_status ='samp'
            elif data == 'npos ok':
                time.sleep(5)        
                self.write_message('start')
            elif data.startswith('err:'):
                self.SAR_Status_lineEdit.setText(data)
                params.SAR_status = 'com'
            elif data in alert:
                self.SAR_Status_lineEdit.setText(data)
                self.SAR_New_Pos_pushButton.setEnabled(False)
                if data == 'tranlimit':
                    self.SAR_Status_lineEdit.setText('Peak limit')
                elif data == 'refllimit':
                    self.SAR_Status_lineEdit.setText('Reflection limit')
                elif data == '10slimit':
                    self.SAR_Status_lineEdit.setText('10s limit')
                elif data == '6minlimit':
                    self.SAR_Status_lineEdit.setText('6min limit')                   
                params.SAR_status ='com'
            elif data in ERR:
                self.SAR_New_Pos_pushButton.setEnabled(False)
                self.SAR_Status_lineEdit.setText(data)
                params.SAR_status ='com'
            else:
                params.SAR_status = 'com'
                self.SAR_Status_lineEdit.setText('Communication')
            
        if self.save_var == 5 :
            self.data_array.append(data)      
            if len(self.data_array) > 1999 :        
                with open(self.file_path,'a') as file:
                    file.writelines('raw_Array: \n[')          
                for i in range(len(self.data_array)-1):
                    self.data_array[i] += '; '                              
                for i in range(len(self.data_array)):              
                    with open(self.file_path,'a') as file:
                        file.writelines(self.data_array[i])
                        if (i+1) % 20 == 0:
                            file.writelines('\n')  
                with open(self.file_path,'a') as file:
                    file.writelines(']\n\n')    
                self.overlay.deleteLater()    
                self.data_array.clear()
                self.save_var=0    
            else:
                self.command= f'rr{self.array_count}'
                self.write_message(self.command)
                self.array_count+=1        
        
        if self.save_var == 4 :
            self.data_array.append(data)
            if len(self.data_array) > 999 :    
                with open(self.file_path,'a') as file:
                    file.writelines('10s_Array: \n[')
                for i in range(len(self.data_array)-1):
                    self.data_array[i] += '; '                   
                for i in range(len(self.data_array)):              
                    with open(self.file_path,'a') as file:
                        file.writelines(self.data_array[i])
                        if (i+1) % 20 == 0:
                            file.writelines('\n')
                with open(self.file_path,'a') as file:
                    file.writelines(']\n\n')     
                self.data_array.clear()
                self.save_var=5
                self.write_message('rr0')
                self.array_count=1     
            else:
                self.command= f'rs{self.array_count}'
                self.write_message(self.command)
                self.array_count+=1
     
        if self.save_var == 3 :
            self.data_array.append(data) 
            if len(self.data_array) > 35 :
                with open(self.file_path,'a') as file:
                    file.writelines('6min_Array: \n[')
                for i in range(len(self.data_array)-1):
                    self.data_array[i] += '; ' 
                for i in range(len(self.data_array)):              
                    with open(self.file_path,'a') as file:
                        file.writelines(self.data_array[i])
                with open(self.file_path,'a') as file:
                    file.writelines(']\n\n')    
                self.data_array.clear()
                self.save_var=4
                self.write_message('rs0')
                self.array_count=1  
            else:
                self.command= f'rm{self.array_count}'
                self.write_message(self.command)
                self.array_count+=1
                 
        if self.save_var == 2 :
            with open(self.file_path,'a') as file:
                file.writelines('10sec_Mean: ' + data + '\n\n')
            self.save_var=3
            self.write_message('rm0')
            self.array_count=1
            
        if self.save_var == 1 :          
            with open(self.file_path,'a') as file:
                file.writelines('6min_Mean: ' + data + '\n')
            self.save_var=2
            self.write_message('r10sec')

    def load_params(self):
        if params.SAR_enable == 1: self.SAR_Enable_radioButton.setChecked(True)
        
        self.SAR_Limit_doubleSpinBox.setValue(params.SAR_limit)
        self.SAR_6mLimit_doubleSpinBox.setValue(params.SAR_6mlimit)
        self.SAR_Tran_doubleSpinBox.setValue(params.SAR_peak_limit)
        self.SAR_Max_Power_doubleSpinBox.setValue(params.SAR_max_power)
        
        if params.SAR_status == 'com': self.SAR_Status_lineEdit.setText('Communication')
        elif params.SAR_status == 'samp': self.SAR_Status_lineEdit.setText('Sampling')
        else: self.SAR_Status_lineEdit.setText('Error')
        
        if params.SAR_power_unit == 'dBm':
            self.label_10s.setText('SAR 10s Limit [dBm]')
            self.label_6m.setText('SAR 6m Limit [dBm]')
            self.label_peak.setText('Peak Limit [dBm]')
            self.label_MaxP.setText('Max. Amplifier Power [dBm]')
            self.SAR_Power_dBm_pushButton.setEnabled(False)
            
        if params.SAR_power_unit == 'mW':
            self.label_10s.setText('SAR 10s Limit [mW]')
            self.label_6m.setText('SAR 6m Limit [mW]')
            self.label_peak.setText('Peak Limit [mW]')
            self.label_MaxP.setText('Max. Amplifier Power [mW]')
            self.SAR_Power_W_pushButton.setEnabled(False)
            
    def update_params(self):
        if self.SAR_Enable_radioButton.isChecked(): params.SAR_enable = 1
        else: params.SAR_enable = 0
        
        params.SAR_limit = self.SAR_Limit_doubleSpinBox.value()
        params.SAR_6mlimit = self.SAR_6mLimit_doubleSpinBox.value()
        params.SAR_peak_limit = self.SAR_Tran_doubleSpinBox.value()
        
        params.SAR_max_power = self.SAR_Max_Power_doubleSpinBox.value()
        
        params.saveFileParameter()
        
class Overlay(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size())
        #self.setFixedSize(QSize(550,250))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet('background-color: rgba(0,0,0,128)')
        label = QLabel('...', self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-size: 24px;")
        
        layout = QVBoxLayout(self)
        layout.addWidget(label)
        self.setLayout(layout)
        
        self.show()
        
    def mousePessEvent(self, event):
        pass
    
    def keyPressEvent(self, event):
        pass


class MotorToolsWindow(Motor_Window_Form, Motor_Window_Base):
    connect = pyqtSignal()

    def __init__(self, parent=None, motor=None):
        super(MotorToolsWindow, self).__init__(parent)
        self.setupUi(self)

        self.motor = motor

        self.load_params()

        self.ui = loadUi('ui/motor_tools.ui')
        self.setWindowTitle('Motor Tools')
        self.setGeometry(420, 40, 390, 340)

        self.Motor_MoveTo_doubleSpinBox.valueChanged.connect(lambda: self.new_move_value(box='to'))
        self.Motor_MoveBy_doubleSpinBox.valueChanged.connect(lambda: self.new_move_value(box='by'))
        self.Motor_Apply_pushButton.clicked.connect(lambda: self.apply())
        self.Motor_Home_pushButton.clicked.connect(lambda: self.home())
        
        self.Motor_MoveToCenter_pushButton.clicked.connect(lambda: self.move_to_center())
        
    def load_params(self):
        self.Motor_Limit_Negative_lineEdit.setText(str(params.motor_axis_limit_negative))
        self.Motor_Limit_Positive_lineEdit.setText(str(params.motor_axis_limit_positive))
        self.Motor_MoveBy_doubleSpinBox.setMaximum(params.motor_axis_limit_positive - params.motor_actual_position)
        self.Motor_MoveBy_doubleSpinBox.setMinimum(params.motor_axis_limit_negative - params.motor_actual_position)
        self.Motor_MoveTo_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.Motor_MoveTo_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        self.Motor_Position_lineEdit.setText(str(params.motor_actual_position))
        self.Motor_MoveTo_doubleSpinBox.setValue(params.motor_goto_position)
        
        self.Motor_Apply_pushButton.setEnabled(params.motor_available)
        self.Motor_Home_pushButton.setEnabled(params.motor_available)
        self.Motor_MoveToCenter_pushButton.setEnabled(params.motor_available)

    def home(self):
        self.Motor_Home_pushButton.setEnabled(False)
        self.Motor_Apply_pushButton.setEnabled(False)
        self.Motor_MoveToCenter_pushButton.setEnabled(False)
        home_s = 'G28\r\n'
        self.motor.write(home_s.encode('utf-8'))

        time.sleep(0.1)

        response_s = 'M118 R0: homing finished\r\n'
        self.motor.write(response_s.encode('utf-8'))

        params.motor_actual_position = params.motor_axis_limit_negative

        self.Motor_Position_lineEdit.setText(str(params.motor_actual_position))
        self.Motor_MoveBy_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.Motor_MoveBy_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)

        print('Motor Control - Homing Message send to device')

    def apply(self):
        print('Moving...')
        
        if params.motor_goto_position != params.motor_actual_position:
            self.Motor_Home_pushButton.setEnabled(False)
            self.Motor_Apply_pushButton.setEnabled(False)
            self.Motor_MoveToCenter_pushButton.setEnabled(False)
        
            apply_s = 'G0 ' + str(params.motor_goto_position) + '\r\n'
            self.motor.write(apply_s.encode('utf-8'))

            time.sleep(0.1)

            response_s = 'M118 R0: finished moving\r\n'
            self.motor.write(response_s.encode('utf-8'))

            params.motor_actual_position = params.motor_goto_position
            self.Motor_Position_lineEdit.setText(str(params.motor_actual_position))
            self.new_move_value(box='to')
            self.Motor_MoveBy_doubleSpinBox.setMaximum(params.motor_axis_limit_positive - params.motor_actual_position)
            self.Motor_MoveBy_doubleSpinBox.setMinimum(params.motor_axis_limit_negative - params.motor_actual_position)

    def new_move_value(self, box=None):
        self.Motor_MoveBy_doubleSpinBox.blockSignals(True)
        self.Motor_MoveTo_doubleSpinBox.blockSignals(True)

        if box == 'to':
            params.motor_goto_position = self.Motor_MoveTo_doubleSpinBox.value()
            self.Motor_MoveBy_doubleSpinBox.setValue((params.motor_goto_position - params.motor_actual_position))
        elif box == 'by':
            params.motor_goto_position = params.motor_actual_position + self.Motor_MoveBy_doubleSpinBox.value()
            self.Motor_MoveTo_doubleSpinBox.setValue(params.motor_goto_position)
        
        self.Motor_MoveBy_doubleSpinBox.blockSignals(False)
        self.Motor_MoveTo_doubleSpinBox.blockSignals(False)

    def move_to_center(self):
        self.Motor_Home_pushButton.setEnabled(False)
        self.Motor_Apply_pushButton.setEnabled(False)
        self.Motor_MoveToCenter_pushButton.setEnabled(False)
        
        params.motor_goto_position = 0
        proc.motor_move(motor=self.motor)
        
        self.motor_messagebox_string = ('Align sample start to the marker. Carefully tighten the test tube holder screw.')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(self.motor_messagebox_string)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        
        params.motor_goto_position = params.PB_marker_isocenter_distance
        proc.motor_move(motor=self.motor)
        
        params.motor_actual_position = params.motor_goto_position
        
        if params.motor_actual_position != params.PB_isocenter_position:
        
            self.motor_messagebox_string = ('Loosen the test tube holder screw.')
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(self.motor_messagebox_string)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
            
            params.motor_goto_position = params.PB_isocenter_position
            proc.motor_move(motor=self.motor)
            
            params.motor_actual_position = params.motor_goto_position
            
            self.motor_messagebox_string = ('Carefully tighten the test tube holder screw.')
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(self.motor_messagebox_string)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
        
        self.Motor_Position_lineEdit.setText(str(params.motor_actual_position))

        params.motor_goto_position = self.Motor_MoveTo_doubleSpinBox.value()
        
        self.new_move_value(box='to')
        self.Motor_MoveBy_doubleSpinBox.setMaximum(params.motor_axis_limit_positive - params.motor_actual_position)
        self.Motor_MoveBy_doubleSpinBox.setMinimum(params.motor_axis_limit_negative - params.motor_actual_position)
        
        self.Motor_Home_pushButton.setEnabled(True)
        self.Motor_Apply_pushButton.setEnabled(True)
        self.Motor_MoveToCenter_pushButton.setEnabled(True)


class ConnectionDialog(Conn_Dialog_Base, Conn_Dialog_Form):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ConnectionDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.ui = loadUi('ui/connDialog.ui')
        screen = QDesktopWidget().availableGeometry()
        self.setGeometry(int((screen.width() - 500) / 2), int((screen.height() - 150) / 2), 500, 150)
        self.ui.closeEvent = self.closeEvent
        self.conn_help = QPixmap('ui/connection_help.png')
        self.help.setVisible(False)

        self.conn_btn.clicked.connect(self.connect_event)
        self.addIP_btn.clicked.connect(self.add_IP)
        self.rmIP_btn.clicked.connect(self.remove_IP)
        self.offmod_btn.clicked.connect(self.offlinemode)
        self.status_label.setVisible(False)

        IPvalidator = QRegExp(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)''{3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
        self.ip_box.setValidator(QRegExpValidator(IPvalidator, self))
        for item in params.hosts: self.ip_box.addItem(item)
        
        self.setStyleSheet(self.styleSheet() + "\n* { font-family: 'Piboto Condensed', 'Arial Narrow'; font-size: 16px;}")
        self.ip_box.setStyleSheet("font-family: 'Piboto Condensed', 'Arial Narrow'; font-size: 16px;")

        self.mainwindow = parent

    def connect_event(self):
        params.ip = self.ip_box.currentText()
        print('Console IP: ' + params.ip)

        connection = seq.conn_client()

        if connection:
            params.connectionmode = True
            params.saveFileParameter()
            self.status_label.setText('Connected')
            self.connected.emit()
            self.mainwindow.show()
            self.mainwindow.Acquire_pushButton.setEnabled(params.connectionmode)
            if params.agriMRI_mode == 1: self.mainwindow.AgriMRI_Metadata_pushButton.show()
            else: self.mainwindow.AgriMRI_Metadata_pushButton.hide()
            self.close()

        elif not connection:
            params.connectionmode = False
            params.saveFileParameter()
            self.status_label.setText('Not connected')
            self.conn_btn.setText('Retry')
            self.help.setPixmap(self.conn_help)
            self.help.setVisible(True)
            screen = QDesktopWidget().availableGeometry()
            self.setGeometry(int((screen.width() - 500) / 2), int((screen.height() - 150) / 2), 500, 350)

        else:
            params.connectionmode = False
            params.saveFileParameter()
            self.status_label.setText('Not connected with status: ' + str(connection))
            self.conn_btn.setText('Retry')
            self.help.setPixmap(self.conn_help)
            self.help.setVisible(True)
            self.setGeometry(10, 40, 500, 350)

        self.status_label.setVisible(True)

    def add_IP(self):
        print('Add ip address')
        ip = self.ip_box.currentText()

        if not ip in params.hosts:
            self.ip_box.addItem(ip)
        else:
            return

        params.hosts = [self.ip_box.itemText(i) for i in range(self.ip_box.count())]
        print(params.hosts)

    def remove_IP(self):
        idx = self.ip_box.currentIndex()
        try:
            del params.hosts[idx]
            self.ip_box.removeItem(idx)
        except:
            pass
        print(params.hosts)

    def offlinemode(self):
        params.connectionmode = False
        params.saveFileParameter()
        self.mainwindow.show()
        self.mainwindow.Acquire_pushButton.setEnabled(params.connectionmode)
        if params.agriMRI_mode == 1: self.mainwindow.AgriMRI_Metadata_pushButton.show()
        else: self.mainwindow.AgriMRI_Metadata_pushButton.hide()
        self.close()
        
class View3DLayersDialog(View3D_Dialog_Form, View3D_Dialog_Base):
    def __init__(self, parent=None):
        super(View3DLayersDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.ui = loadUi('ui/view_3D.ui')
        self.setWindowTitle('3D Layers Plot')
        self.setGeometry(420, 40, 1160, 950)
        
        if params.agriMRI_mode == 1:
            self.datapath_temp = ''
            self.datapath_temp = params.datapath
            self.agriMRI_folder_structure_temp = ''
            self.agriMRI_folder_structure_temp = params.agriMRI_folder_structure
            params.agriMRI_folder_structure = params.agriMRI_folder_structure + 'AgriMRI_rawdata/'
            params.datapath = params.agriMRI_folder_structure + params.datapath
        
        if params.headerfileformat == 0:
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_Header.txt') == True:
                    f = open(params.datapath + '/Image_Stitching_Header.txt', 'r+')
                    headerlines = f.readlines()
                    f.close()
                else: print('No .txt header file!!')
            elif os.path.isdir(params.datapath) == False:
                if os.path.isfile(params.datapath + '_Header.txt') == True:
                    f = open(params.datapath + '_Header.txt', 'r+')
                    headerlines = f.readlines()
                    f.close()
                else: print('No .txt header file!!')
            else: print('No directory or .txt header file!!')
            
            self.headerline_string_split = headerlines[2].split(': ')
            self.GUImode = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[3].split(': ')
            self.sequence = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[30].split(': ')
            self.imageorientation = self.headerline_string_split[1]
            self.headerline_string_split = self.imageorientation.split('\n')
            self.imageorientation = self.headerline_string_split[0]
            self.headerline_string_split = headerlines[32].split(': ')
            self.nPE = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[70].split(': ')
            self.FOV = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[71].split(': ')
            self.slicethickness = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[90].split(': ')
            self.motor_movement_step = float(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[54].split(': ')
            self.SPEsteps = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[91].split(': ')
            self.motor_image_count = int(self.headerline_string_split[1])
            self.headerline_string_split = headerlines[89].split(': ')
            self.motor_total_image_length = float(self.headerline_string_split[1])
                     
        else:
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_Header.json') == True:
                    with open(params.datapath + '/Image_Stitching_Header.json', 'r', encoding='utf-8') as j:
                        jsonparams = json.loads(j.read())
                else: print('No .json header file!!')
            elif os.path.isdir(params.datapath) == False:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    with open(params.datapath + '_Header.json', 'r', encoding='utf-8') as j:
                        jsonparams = json.loads(j.read())
                else: print('No .json header file!!')
            else: print('No directory or .json header file!!')
                    
            self.GUImode = int(jsonparams['GUI mode'])
            self.sequence = int(jsonparams['Sequence'])
            self.imageorientation = jsonparams['Image orientation']
            self.nPE = int(jsonparams['Image resolution [pixel]'])
            self.FOV = jsonparams['FOV [mm]']
            self.slicethickness = jsonparams['Slice/Slab thickness [mm]']
            self.motor_movement_step = jsonparams['Motor movement step [mm]']
            self.SPEsteps = int(jsonparams['3D phase steps'])
            self.motor_image_count = int(jsonparams['Motor image count'])
            self.motor_total_image_length = jsonparams['Motor total image length [mm]']
            
            
        if params.agriMRI_mode == 1:
            params.datapath = self.datapath_temp
            params.agriMRI_folder_structure = self.agriMRI_folder_structure_temp

        if self.GUImode == 5 and (self.sequence == 0 or self.sequence == 1 or self.sequence == 2 or self.sequence == 3 \
                                  or self.sequence == 4 or self.sequence == 5 or self.sequence == 6 or self.sequence == 7 \
                                  or self.sequence == 8 or self.sequence == 9): self.SPEsteps = 1

        self.aspect = np.zeros(3)
        self.aspect[0] = 1.0
        
        self.mode2D = False
        
        if self.imageorientation == 'XY':
            self.view3D_RO_PE_SPE_lineEdit.setText('X, Y, Z')
            self.ro_switched = False
            self.XY = 0
            self.ZX = 1
            self.YZ = 2
        if self.imageorientation == 'YZ':
            self.view3D_RO_PE_SPE_lineEdit.setText('Y, Z, X')
            self.ro_switched = False
            self.XY = 1
            self.ZX = 2
            self.YZ = 0
        if self.imageorientation == 'ZX':
            self.view3D_RO_PE_SPE_lineEdit.setText('Z, X, Y')
            self.ro_switched = False
            self.XY = 2
            self.ZX = 0
            self.YZ = 1
        if self.imageorientation == 'YX':
            self.view3D_RO_PE_SPE_lineEdit.setText('Y, X, Z')
            self.ro_switched = True
            self.XY = 0  
            self.ZX = 1
            self.YZ = 2
        if self.imageorientation == 'ZY':
            self.view3D_RO_PE_SPE_lineEdit.setText('Z, Y, X')
            self.ro_switched = True
            self.XY = 1
            self.ZX = 2
            self.YZ = 0
        if self.imageorientation == 'XZ':
            self.view3D_RO_PE_SPE_lineEdit.setText('X, Z, Y')
            self.ro_switched = True
            self.XY = 2  
            self.ZX = 0
            self.YZ = 1
        
        if self.GUImode == 1:
            self.image = params.img_mag
            self.phase = params.img_pha
            
            self.imagelength = self.slicethickness
            
        elif self.GUImode == 5 and (self.sequence == 0 or self.sequence == 1 or self.sequence == 2 or self.sequence == 3 \
                                    or self.sequence == 4 or self.sequence == 5 or self.sequence == 6 or self.sequence == 7 \
                                    or self.sequence == 8 or self.sequence == 9):
            self.mode2D = True             
            
            datapathtemp = params.datapath
            
            if self.slicethickness >= self.motor_movement_step:
                self.image = np.array(np.zeros((self.motor_image_count, self.nPE, self.nPE)))
                self.phase = np.array(np.zeros((self.motor_image_count, self.nPE, self.nPE)))
                        
                for n in range(0, self.motor_image_count):
                    self.image[n, :, :] = params.img_st_mag[:, n*self.nPE:(n+1)*self.nPE]
                    self.phase[n, :, :] = params.img_st_pha[:, n*self.nPE:(n+1)*self.nPE]
                    
                self.imagelength = self.motor_total_image_length + self.motor_movement_step
            else:
                self.factor2D = 4
                precision = 0.01
                self.image = np.array(np.zeros((self.motor_image_count*self.factor2D - 2, self.nPE, self.nPE)))
                self.phase = np.array(np.zeros((self.motor_image_count*self.factor2D - 2, self.nPE, self.nPE)))
                self.movement_positions = np.array(np.zeros(self.motor_image_count*self.factor2D - 2))
                self.image_positions = np.linspace(0, self.nPE, self.nPE)
                
                for n in range(0, self.motor_image_count):
                    self.image[n*self.factor2D, :, :] = params.img_st_mag[:, n*self.nPE:(n+1)*self.nPE]
                    self.phase[n*self.factor2D, :, :] = params.img_st_pha[:, n*self.nPE:(n+1)*self.nPE]
                    self.movement_positions[n*self.factor2D] = n * self.motor_movement_step + precision
                    
                    self.image[n*self.factor2D+1, :, :] = params.img_st_mag[:, n*self.nPE:(n+1)*self.nPE]
                    self.phase[n*self.factor2D+1, :, :] = params.img_st_pha[:, n*self.nPE:(n+1)*self.nPE]
                    self.movement_positions[n*self.factor2D+1] = n * self.motor_movement_step + self.slicethickness - precision
                    
                    if n != self.motor_image_count - 1:
                        self.movement_positions[n*self.factor2D+2] = n * self.motor_movement_step + self.slicethickness + precision
                        self.movement_positions[n*self.factor2D+3] = (n+1) * self.motor_movement_step - precision                   
                    
                self.imagelength = np.max(self.movement_positions) + precision
            
            self.mirrored = False
        else:
            self.image = np.flip(params.img_st_mag, axis=0)
            self.phase = np.flip(params.img_st_pha, axis=0)
            
            self.motor_movement_step = np.abs(self.motor_movement_step)
            if self.motor_movement_step <= self.FOV:
                self.imagelength = self.motor_total_image_length + self.motor_movement_step
            else:
                self.imagelength = self.motor_total_image_length + self.FOV
                
        if self.ZX == 0:
            if self.mode2D and (self.slicethickness >= self.motor_movement_step):
                self.aspect[1] = (self.motor_movement_step/self.SPEsteps) / (self.FOV/self.nPE)
                self.aspect[2] = (self.FOV/self.nPE) / (self.motor_movement_step/self.SPEsteps)
                self.mode2D = False
            else:
                self.aspect[1] = (self.slicethickness/self.SPEsteps) / (self.FOV/self.nPE)
                self.aspect[2] = (self.FOV/self.nPE) / (self.slicethickness/self.SPEsteps)
        elif self.XY == 0:
            self.aspect[1] = (self.FOV/self.nPE) / (self.slicethickness/self.SPEsteps)
            self.aspect[2] = (self.FOV/self.nPE) / (self.slicethickness/self.SPEsteps)
        else:
            self.aspect[1] = (self.slicethickness/self.SPEsteps) / (self.FOV/self.nPE)
            self.aspect[2] = (self.slicethickness/self.SPEsteps) / (self.FOV/self.nPE)
                
        if self.ro_switched:
            temp_image = self.image
            temp_phase = self.phase
            
            self.image = np.flip(np.rot90(temp_image, axes = (2, 1)), axis = 1)
            self.phase = np.flip(np.rot90(temp_phase, axes = (2, 1)), axis = 1)
        
        self.mirrored = False

        self.showPhase = False
        self.phase_min=np.min(self.phase)
        self.phase_max=np.max(self.phase)
        self.image_min=np.min(self.image)
        self.image_max=np.max(self.image)
        
        layout = QVBoxLayout(self.view3D_figure_widget)
        fig = Figure()
        fig.patch.set_alpha(0.0)
        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)
        gs = GridSpec(2, 2, width_ratios=[self.FOV, self.imagelength], height_ratios=[self.FOV, self.imagelength])
        
        self.current_slice_ZX = 1
        self.slice_count_ZX = self.image.shape[self.ZX]
        self.view3D_ZX_slider.setMinimum(1)
        if self.mode2D:
            self.view3D_ZX_slider.setMaximum(int(round(self.slice_count_ZX / 2)))
        else:
            self.view3D_ZX_slider.setMaximum(self.slice_count_ZX)
        self.view3D_ZX_slider.setSingleStep(1)
        self.view3D_ZX_slider.setPageStep(1)
        self.view3D_ZX_slider.setSliderPosition(int(math.ceil(self.view3D_ZX_slider.maximum() / 2)))
        self.view3D_ZX_slider.valueChanged.connect(lambda value: self.update_image(value, self.current_slice_XY, self.current_slice_YZ))
        self.ax_ZX = fig.add_subplot(gs[0, 0])
        self.img_handle_ZX = self.ax_ZX.imshow(self.get_slice_data(self.image, self.ZX, 0))
        self.line_handle_ZX_Z = self.ax_ZX.axhline(0, color='w', dashes = (1,5), linewidth=2.0)
        self.line_handle_ZX_X = self.ax_ZX.axvline(0, color='w', dashes = (1,5), linewidth=2.0)
        self.ax_ZX.grid(False)
        self.ax_ZX.axis('off')
        self.ax_ZX.set_title('ZX', color='w')
        self.ax_ZX.set_aspect(self.aspect[self.ZX])
        
        self.current_slice_XY = 1
        self.slice_count_XY = self.image.shape[self.XY]
        self.view3D_XY_slider.setMinimum(1)
        self.view3D_XY_slider.setMaximum(self.slice_count_XY)
        self.view3D_XY_slider.setSingleStep(1)
        self.view3D_XY_slider.setPageStep(1)
        self.view3D_XY_slider.setSliderPosition(int(round(self.view3D_XY_slider.maximum()/2)))
        self.view3D_XY_slider.valueChanged.connect(lambda value: self.update_image(self.current_slice_ZX, value, self.current_slice_YZ))
        self.ax_XY = fig.add_subplot(gs[0, 1])
        if self.mode2D:
            self.img_handle_XY = NonUniformImage(self.ax_XY, cmap=params.imagecolormap, extent = (0, self.imagelength, 0, self.nPE))
            self.img_handle_XY.set_data(self.movement_positions, self.image_positions, self.get_slice_data(self.image, self.XY, 0))
            self.ax_XY.add_image(self.img_handle_XY)
            self.ax_XY.set_xlim(0, self.imagelength)
            self.ax_XY.set_ylim(0, self.nPE)
        else:
            self.img_handle_XY = self.ax_XY.imshow(self.get_slice_data(self.image, self.XY, 0))
        self.line_handle_XY_X = self.ax_XY.axhline(0, color='w', dashes = (1,5), linewidth=2.0)
        self.line_handle_XY_Y = self.ax_XY.axvline(0, color='w', dashes = (1,5), linewidth=2.0)
        self.ax_XY.grid(False)
        self.ax_XY.axis('off')
        self.ax_XY.set_title('XY (viewed as YX)', color='w')
        if not self.mode2D: self.ax_XY.set_aspect(self.aspect[self.XY])
        #else:
            #print(self.FOV)
            #print(self.imagelength)
            #print(self.ax_XY.get_aspect())
            #self.ax_XY.set_aspect(self.FOV/self.imagelength)
        
        self.current_slice_YZ = 1
        self.slice_count_YZ = self.image.shape[self.YZ]
        self.view3D_YZ_slider.setMinimum(1)
        self.view3D_YZ_slider.setMaximum(self.slice_count_YZ)
        self.view3D_YZ_slider.setSingleStep(1)
        self.view3D_YZ_slider.setPageStep(1)
        self.view3D_YZ_slider.setSliderPosition(int(round(self.view3D_YZ_slider.maximum()/2)))
        self.view3D_YZ_slider.valueChanged.connect(lambda value: self.update_image(self.current_slice_ZX, self.current_slice_XY, value))
        self.ax_YZ = fig.add_subplot(gs[1, 0])
        if self.mode2D:
            self.img_handle_YZ = NonUniformImage(self.ax_YZ, cmap=params.imagecolormap, extent = (0, self.nPE, 0, self.imagelength))
            self.img_handle_YZ.set_data(self.image_positions, self.movement_positions, self.get_slice_data(self.image, self.YZ, 0))
            self.ax_YZ.add_image(self.img_handle_YZ)
            self.ax_YZ.set_xlim(0, self.nPE)
            self.ax_YZ.set_ylim(0, self.imagelength)
        else:
            self.img_handle_YZ = self.ax_YZ.imshow(self.get_slice_data(self.image, self.YZ, 0))        
        self.line_handle_YZ_Y = self.ax_YZ.axhline(0, color='w', dashes = (1,5), linewidth = 2.0)
        self.line_handle_YZ_Z = self.ax_YZ.axvline(0, color='w', dashes = (1,5), linewidth = 2.0)
        self.ax_YZ.grid(False)
        self.ax_YZ.axis('off')
        self.ax_YZ.set_title('YZ (viewed as ZY)', color='w')
        if not self.mode2D: self.ax_YZ.set_aspect(self.aspect[self.YZ])
        #else:
            #self.ax_YZ.set_aspect(self.imagelength/self.FOV)
        
        fig.tight_layout()
        
        self.img_handles = np.empty(3, dtype=object)
        self.img_handles[self.ZX] = self.img_handle_ZX
        self.img_handles[self.XY] = self.img_handle_XY
        self.img_handles[self.YZ] = self.img_handle_YZ
        
        self.f_line_handles = np.empty(3, dtype=object)
        self.f_line_handles[self.ZX] = self.line_handle_XY_Y
        self.f_line_handles[self.XY] = self.line_handle_ZX_X
        self.f_line_handles[self.YZ] = self.line_handle_XY_X
        
        self.s_line_handles = np.empty(3, dtype=object)
        self.s_line_handles[self.ZX] = self.line_handle_YZ_Y
        self.s_line_handles[self.XY] = self.line_handle_YZ_Z
        self.s_line_handles[self.YZ] = self.line_handle_ZX_Z
        
        self.f_line_counts = np.empty(3, dtype=object)
        self.f_line_counts[self.ZX] = self.image.shape[self.XY]
        self.f_line_counts[self.XY] = self.image.shape[self.ZX]
        self.f_line_counts[self.YZ] = self.image.shape[self.YZ]
        
        self.s_line_counts = np.empty(3, dtype=object)
        self.s_line_counts[self.ZX] = self.image.shape[self.YZ]
        self.s_line_counts[self.XY] = self.image.shape[self.XY]
        self.s_line_counts[self.YZ] = self.image.shape[self.ZX]
        
        #self.update_image(1, 1, 1, reset = True)
        self.update_image(int(math.ceil(self.view3D_ZX_slider.maximum()/2)), int(round(self.view3D_XY_slider.maximum()/2)),int(round(self.view3D_YZ_slider.maximum()/2)), reset=True)
        
        self.view3D_FOV_lineEdit.setText(str(self.FOV))
        self.view3D_Image_Length_lineEdit.setText(str(self.imagelength))
        
        self.view3D_switch_pushButton.clicked.connect(lambda: self.switchButton())
        
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

    def on_scroll(self, event):
        if event.inaxes == self.ax_ZX:
            self.view3D_ZX_slider.setValue(int(self.view3D_ZX_slider.value() + event.step))
        elif event.inaxes == self.ax_XY:
            self.view3D_XY_slider.setValue(int(self.view3D_XY_slider.value() + event.step))
        elif event.inaxes == self.ax_YZ:
            self.view3D_YZ_slider.setValue(int(self.view3D_YZ_slider.value() + event.step))
        
    def resizeEvent(self, event):        
        self.view3D_horizontalWidget.setGeometry(self.rect())
        
        formRect = QRect(self.width() - self.view3D_form_widget.width() - 25, self.height() - self.view3D_form_widget.height() - 25, self.view3D_form_widget.width() , self.view3D_form_widget.height())
        self.view3D_form_widget.setGeometry(formRect)
            
    def switchButton(self):
        if self.showPhase:
            self.showPhase = False
            self.view3D_switch_pushButton.setText('Phase Data')
        else:
            self.showPhase = True
            self.view3D_switch_pushButton.setText('Magnitude Data')
            
        self.update_image(self.current_slice_ZX, self.current_slice_XY, self.current_slice_YZ, reset = True)
            
    
    def update_image(self, new_slice_ZX, new_slice_XY, new_slice_YZ, reset=False):        
        if self.current_slice_ZX != new_slice_ZX or reset:
            self.current_slice_ZX = new_slice_ZX
            if self.slicethickness >= self.motor_movement_step: self.view3D_ZX_Slice_lineEdit.setText(str(self.current_slice_ZX) + ' / ' + str(int(self.slice_count_ZX)))
            else: self.view3D_ZX_Slice_lineEdit.setText(str(self.current_slice_ZX) + ' / ' + str(int(round(self.slice_count_ZX / 2))))
            
            self.update_single_image(slice = self.current_slice_ZX, count = self.slice_count_ZX, index = self.ZX)
            
        if self.current_slice_XY != new_slice_XY or reset:
            self.current_slice_XY = new_slice_XY
            self.view3D_XY_Slice_lineEdit.setText(str(self.current_slice_XY) + ' / ' + str(self.slice_count_XY))
            
            self.update_single_image(slice = self.current_slice_XY, count = self.slice_count_XY, index = self.XY)
            
        if self.current_slice_YZ != new_slice_YZ or reset:
            self.current_slice_YZ = new_slice_YZ
            self.view3D_YZ_Slice_lineEdit.setText(str(self.current_slice_YZ) + ' / ' + str(self.slice_count_YZ))
            
            self.update_single_image(slice = self.current_slice_YZ, count = self.slice_count_YZ, index = self.YZ)
            
        self.canvas.draw()
        
    def update_single_image(self, slice=None, count=None, index=None):
        if index == self.ZX and self.mode2D:
            slice = slice*2
        
        if self.mirrored:
            alt_slice = slice
            slice = count - slice
        else:
            alt_slice = count - slice
            slice = slice - 1
            
        if self.mode2D:
            if index == self.ZX:
                position = (self.movement_positions[slice] + self.movement_positions[slice - 1]) / 2
                self.f_line_handles[index].set_data([position, position], [0, self.f_line_counts[index]])
                self.s_line_handles[index].set_data([0, self.s_line_counts[index]], [position, position])
            if index == self.YZ:
                self.f_line_handles[index].set_data([0, self.f_line_counts[index]], [slice, slice])
                self.s_line_handles[index].set_data([0, self.s_line_counts[index]], [alt_slice, alt_slice])
            if index == self.XY:
                self.f_line_handles[index].set_data([alt_slice, alt_slice], [0, self.f_line_counts[index]])
                self.s_line_handles[index].set_data([alt_slice, alt_slice], [0, self.s_line_counts[index]])
        else:
            if index == self.ZX:
                self.f_line_handles[index].set_data([slice, slice], [0, self.f_line_counts[index]])
                self.s_line_handles[index].set_data([0, self.s_line_counts[index]], [alt_slice, alt_slice])
            if index == self.YZ:
                self.f_line_handles[index].set_data([0, self.f_line_counts[index]], [slice, slice])
                self.s_line_handles[index].set_data([0, self.s_line_counts[index]], [slice, slice])
            if index == self.XY:
                self.f_line_handles[index].set_data([alt_slice, alt_slice], [0, self.f_line_counts[index]])
                self.s_line_handles[index].set_data([alt_slice, alt_slice], [0, self.s_line_counts[index]])
        
        handle = self.img_handles[index]
            
        if self.showPhase:
            data = self.phase
            handle.set_clim(vmin=self.phase_min, vmax=self.phase_max)
            handle.set_cmap('gray')
            if params.imagefilter == 1:
                handle.set_interpolation('gaussian')
            else:
                handle.set_interpolation('none')
        else:
            data = self.image
            handle.set_clim(vmin=self.image_min, vmax=self.image_max)
            if not self.mode2D:
                handle.set_cmap(params.imagecolormap)
            if params.imagefilter == 1:
                if self.mode2D:
                    handle.set_interpolation('bilinear')
                else:
                    handle.set_interpolation('gaussian')
            else:
                if self.mode2D:
                    handle.set_interpolation('nearest')
                else:
                    handle.set_interpolation('none')
        
        if (self.ZX == index and self.XY == 0) or (self.XY == index and self.ZX == 0) or (self.YZ == index and self.XY == 0):
            if self.mode2D:
                handle.set_data(self.movement_positions, self.image_positions, self.get_slice_data(data, index, alt_slice))
            else:
                handle.set_data(self.get_slice_data(data, index, alt_slice))
        else:
            if self.mode2D and self.ZX is not index:
                handle.set_data(self.image_positions, self.movement_positions, self.get_slice_data(data, index, alt_slice))
            else:
                handle.set_data(self.get_slice_data(data, index, slice))

    def get_slice_data(self, data, handler_index, slice_index):
        if handler_index == self.ZX:
            if handler_index == 0:
                return data[slice_index, :, :]
            elif handler_index == 1:
                return np.flip(np.rot90(data[:, slice_index, :]), axis = 1)
            elif handler_index == 2:
                # TODO
                return np.flip(data[:, :, slice_index], axis = 1)
        elif handler_index == self.XY:
            if handler_index == 0:
                return np.rot90(np.flip(data[slice_index, :, :], axis = 1), k = -1)
            elif handler_index == 1:
                # TODO
               return data[:, slice_index, :]
            elif handler_index == 2:
                if self.mode2D:
                    return np.flip(np.transpose(data[:, :, slice_index]), axis = 0)
                else:
                    return np.transpose(data[:, :, slice_index])
        elif handler_index == self.YZ:
            if handler_index == 0:
                # TODO
                return np.flip(np.rot90(data[slice_index, :, :]), axis = 1)
            elif handler_index == 1:
                return np.flip(data[:, slice_index, :], axis=0)
            elif handler_index == 2:
                return np.flip(np.rot90(data[:, :, slice_index]))
                
def run():
    app = QApplication(sys.argv)
    gui = MainWindow()

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()