################################################################################
#
#Author: Marcus Prier
#Date: 2024
#
################################################################################

import sys
import csv
import numpy as np
import os
import math
import time
import shutil

import serial
import serial.tools.list_ports
import asyncio
import zlib
import struct
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QSize, QRect
from enum import Enum

import json

from datetime import datetime

# import PyQt5 packages
from PyQt5 import QtWidgets
from PyQt5.QtSerialPort import QSerialPortInfo, QSerialPort
from PyQt5.QtWidgets import QMessageBox, QApplication, QFileDialog, QDesktopWidget, QFrame, QTableWidget, QTableWidgetItem
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QRegExp, pyqtSignal, QStandardPaths, QIODevice, QObject, QTimer
from PyQt5.QtGui import QRegExpValidator, QPixmap

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.image import NonUniformImage

from parameter_handler import params
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

        self.ui = loadUi('ui/mainwindow.ui')
        self.setWindowTitle('Relax 2.0')
        params.load_GUItheme()
        self.setStyleSheet(params.stylesheet)
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

        self.motor = None
        self.motor_reader = None
        
        if params.motor_enable:
            self.motor_connect()

        if params.GSamplitude == 0:
            params.GSposttime = 0
        else:
            params.GSposttime = int((200 * params.GSamplitude + 4 * params.flippulselength * params.GSamplitude) / 2 - 200 * params.GSamplitude / 2) / (params.GSamplitude / 2)
        
        self.establish_conn()

        self.Mode_Spectroscopy_pushButton.clicked.connect(lambda: self.switch_GUImode(0))
        self.Mode_Imaging_pushButton.clicked.connect(lambda: self.switch_GUImode(1))
        self.Mode_T1_Measurement_pushButton.clicked.connect(lambda: self.switch_GUImode(2))
        self.Mode_T2_Measurement_pushButton.clicked.connect(lambda: self.switch_GUImode(3))
        self.Mode_Projections_pushButton.clicked.connect(lambda: self.switch_GUImode(4))
        self.Mode_Image_Stitching_pushButton.clicked.connect(lambda: self.switch_GUImode(5))
        self.Tools_pushButton.clicked.connect(lambda: self.tools())
        self.Protocol_pushButton.clicked.connect(lambda: self.protocol())

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

        print('GUImode:\t', params.GUImode)

        if params.GUImode == 0:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Free Induction Decay', 'Spin Echo', 'Inversion Recovery (FID)' \
                                            , 'Inversion Recovery (SE)', 'Saturation Inversion Recovery (FID)', 'Saturation Inversion Recovery (SE)' \
                                            , 'Echo Planar Spectrum (FID, 4 Echos)', 'Echo Planar Spectrum (SE, 4 Echos)', 'Turbo Spin Echo (4 Echos)' \
                                            , 'Free Induction Decay (Slice)', 'Spin Echo (Slice)', 'Inversion Recovery (FID, Slice)' \
                                            , 'Inversion Recovery (SE, Slice)', 'Saturation Inversion Recovery (FID, Slice)', 'Saturation Inversion Recovery (SE, Slice)' \
                                            , 'Echo Planar Spectrum (FID, 4 Echos, Slice)', 'Echo Planar Spectrum (SE, 4 Echos, Slice)', 'Turbo Spin Echo (4 Echos, Slice)' \
                                            , 'RF Loopback Test Sequence (Rect, Flip)', 'RF Loopback Test Sequence (Rect, 180°)', 'RF Loopback Test Sequence (Sinc, Flip)' \
                                            , 'RF Loopback Test Sequence (Sinc, 180°)', 'Gradient Test Sequence', 'RF SAR Calibration Test Sequence'])
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
                                            , '2D Radial (Slice, GRE, Full)', '2D Radial (Slice, SE, Full)', '2D Radial (Slice, GRE, Half)' \
                                            , '2D Radial (Slice, SE, Half)', '2D Gradient Echo (Slice)', '2D Spin Echo (Slice)' \
                                            , '2D Spin Echo (Slice, InOut)', '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)' \
                                            , 'WIP 2D Saturation Inversion Recovery (Slice, GRE)', 'WIP 2D Saturation Inversion Recovery (Slice, SE)', '2D Turbo Spin Echo (Slice, 4 Echos)' \
                                            , 'WIP 2D Echo Planar Imaging (Slice, GRE, 4 Echos)', 'WIP 2D Echo Planar Imaging (Slice, SE, 4 Echos)', '2D Diffusion (Slice, SE)' \
                                            , 'WIP 2D Flow Compensation (Slice, GRE)', 'WIP 2D Flow Compensation (Slice, SE)', 'WIP 3D FFT Gradient Echo (Slab)' \
                                            , '3D FFT Spin Echo (Slab)', '3D FFT Turbo Spin Echo (Slab)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/Image_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 2:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Inversion Recovery (FID)', 'Inversion Recovery (SE)', 'Inversion Recovery (Slice, FID)' \
                                            , 'Inversion Recovery (Slice, SE)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/T1_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 3:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Spin Echo', 'Saturation Inversion Recovery (FID)', 'Spin Echo (Slice)' \
                                            , 'Saturation Inversion Recovery (Slice, FID)', '2D Spin Echo', '2D Saturation Inversion Recovery (GRE)' \
                                            , '2D Spin Echo (Slice)', '2D Saturation Inversion Recovery (Slice, GRE)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/T2_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 4:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['Gradient Echo (On Axis)', 'Spin Echo (On Axis)', 'Gradient Echo (On Angle)' \
                                            , 'Spin Echo (On Angle)', 'Gradient Echo (Slice, On Axis)', 'Spin Echo (Slice, On Axis)' \
                                            , 'Gradient Echo (Slice, On Angle)', 'Spin Echo (Slice, On Angle)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/Projection_rawdata')
            params.datapath = self.Datapath_lineEdit.text()
        elif params.GUImode == 5:
            self.Sequence_comboBox.clear()
            self.Sequence_comboBox.addItems(['2D Gradient Echo', '2D Inversion Recovery (GRE)', '2D Spin Echo' \
                                            , '2D Inversion Recovery (SE)', '2D Turbo Spin Echo (4 Echos)', '2D Gradient Echo (Slice)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Spin Echo (Slice)', '2D Inversion Recovery (Slice, SE)' \
                                            , '2D Turbo Spin Echo (Slice, 4 Echos)', '3D FFT Spin Echo (Slab)'])
            self.Sequence_comboBox.setCurrentIndex(0)
            self.Datapath_lineEdit.setText('rawdata/Image_Stitching_rawdata')
            params.datapath = self.Datapath_lineEdit.text()

    def set_sequence(self, idx):
        params.sequence = idx
        if params.sequence != -1: print('Sequence:\t', params.sequence)

        params.saveFileParameter()

    def acquire(self):
        self.Acquire_pushButton.setEnabled(False)
        if params.autodataprocess == 1: self.Data_Process_pushButton.setEnabled(False)
        self.repaint()

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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_config != None:
                        self.dialog_config.load_params()
                        self.dialog_config.repaint()
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
                    seq.sequence_upload()
            else:
                seq.sequence_upload()
        else:
            seq.sequence_upload()
            
        params.saveFileParameter()
        params.saveFileData()
        
        if params.GUImode == 5:
            self.datapathtemp = ''
            self.datapathtemp = params.datapath
            params.datapath = params.datapath + '/Image_Stitching'
            
            if params.headerfileformat == 0:
                params.save_header_file_txt()
            else:
                params.save_header_file_json()
                
            params.datapath = self.datapathtemp
            
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

    def set_Datapath(self):
        params.datapath = self.Datapath_lineEdit.text()
        print('Datapath:', params.datapath)

    def dataprocess(self):
        self.Data_Process_pushButton.setEnabled(False)
        self.repaint()
        
        if self.dialog_plot != None:
            if self.dialog_plot.dialog_3D_layers != None:
                self.dialog_plot.dialog_3D_layers.hide()

        if params.GUImode == 0:
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.spectrum_process()
                proc.spectrum_analytics()
                if params.single_plot == 1:
                    if self.dialog_plot != None:
                        self.dialog_plot.hide()
                        if self.dialog_plot.fig_canvas != None: self.dialog_plot.fig_canvas.hide()
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else:
                print('No file!!')
        elif params.GUImode == 1 and (params.sequence == 34 or params.sequence == 35 or params.sequence == 36):
            if os.path.isfile(params.datapath + '.txt') == True:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    proc.image_3D_json_process()
                    proc.image_3D_analytics()
                    if params.single_plot == 1:
                        if self.dialog_plot != None:
                            self.dialog_plot.hide()
                            if self.dialog_plot.all_canvas != None: self.dialog_plot.all_canvas.hide()
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                        else:
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                elif os.path.isfile(params.datapath + '_Header.txt') == True:
                    proc.image_3D_txt_process()
                    # proc.image_3D_analytics()
                    # self.dialog_plot = PlotWindow(self)
                    # self.dialog_plot.show()
                else:
                    print('No 3D header file!!')
            else:
                print('No 3D File!!')
        elif params.GUImode == 1 and (params.sequence == 14 or params.sequence == 31):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.image_diff_process()
                # proc.image_analytics()
                if params.single_plot == 1:
                    if self.dialog_plot != None:
                        self.dialog_plot.hide()
                        if self.dialog_plot.IComb_canvas != None: self.dialog_plot.IComb_canvas.hide()
                        if self.dialog_plot.IDiff_canvas != None: self.dialog_plot.IDiff_canvas.hide()
                        if self.dialog_plot.IMag_canvas != None: self.dialog_plot.IMag_canvas.hide()
                        if self.dialog_plot.IPha_canvas != None: self.dialog_plot.IPha_canvas.hide()
                        if self.dialog_plot.kMag_canvas != None: self.dialog_plot.kMag_canvas.hide()
                        if self.dialog_plot.kPha_canvas != None: self.dialog_plot.kPha_canvas.hide()
                        if self.dialog_plot.all_canvas != None: self.dialog_plot.all_canvas.hide()
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else:
                print('No file!!')
        elif params.GUImode == 1 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 \
                                      or params.sequence == 3 or params.sequence == 17 or params.sequence == 18 \
                                      or params.sequence == 19 or params.sequence == 20):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.radial_process()
                proc.image_analytics()
                if params.single_plot == 1:
                    if self.dialog_plot != None:
                        self.dialog_plot.hide()
                        if self.dialog_plot.IMag_canvas != None: self.dialog_plot.IMag_canvas.hide()
                        if self.dialog_plot.IPha_canvas != None: self.dialog_plot.IPha_canvas.hide()
                        if self.dialog_plot.kMag_canvas != None: self.dialog_plot.kMag_canvas.hide()
                        if self.dialog_plot.kPha_canvas != None: self.dialog_plot.kPha_canvas.hide()
                        if self.dialog_plot.all_canvas != None: self.dialog_plot.all_canvas.hide()
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else:
                print('No file!!')
        elif params.GUImode == 1 and (params.sequence != 34 or params.sequence != 35 or params.sequence != 36 \
                                      or params.sequence != 14 or params.sequence != 31 or params.sequence != 0 \
                                      or params.sequence != 1 or params.sequence != 2 or params.sequence != 3 \
                                      or params.sequence != 17 or params.sequence != 18 or params.sequence != 19 \
                                      or params.sequence != 20):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.image_process()
                proc.image_analytics()
                if params.single_plot == 1:
                    if self.dialog_plot != None:
                        self.dialog_plot.hide()
                        if self.dialog_plot.IMag_canvas != None: self.dialog_plot.IMag_canvas.hide()
                        if self.dialog_plot.IPha_canvas != None: self.dialog_plot.IPha_canvas.hide()
                        if self.dialog_plot.kMag_canvas != None: self.dialog_plot.kMag_canvas.hide()
                        if self.dialog_plot.kPha_canvas != None: self.dialog_plot.kPha_canvas.hide()
                        if self.dialog_plot.all_canvas != None: self.dialog_plot.all_canvas.hide()
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()

        elif params.GUImode == 2 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.T1process()
                if params.single_plot == 1:
                    if self.dialog_plot != None:
                        self.dialog_plot.hide()
                        if self.dialog_plot.fig_canvas1 != None: self.dialog_plot.fig_canvas1.hide()
                        if self.dialog_plot.fig_canvas2 != None: self.dialog_plot.fig_canvas2.hide()
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else:
                print('No file!!')
        elif params.GUImode == 2 and (params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7):
            if os.path.isfile(params.datapath + '_Image_TI_steps.txt') == True:
                if os.path.isfile(params.datapath + '_Image_Magnitude.txt') == True:
                    proc.T1imageprocess()
                    if params.single_plot == 1:
                        if self.dialog_plot != None:
                            self.dialog_plot.hide()
                            if self.dialog_plot.IComb_canvas != None: self.dialog_plot.IComb_canvas.hide()
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                        else:
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    print('No file!!')
            else:
                print('No file!!')

        elif params.GUImode == 3 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3):
            if os.path.isfile(params.datapath + '.txt') == True:
                proc.T2process()
                if params.single_plot == 1:
                    if self.dialog_plot != None:
                        self.dialog_plot.hide()
                        if self.dialog_plot.fig_canvas != None: self.dialog_plot.fig_canvas.hide()
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else:
                print('No file!!')
        elif params.GUImode == 3 and (params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7):
            if os.path.isfile(params.datapath + '_Image_TE_steps.txt') == True:
                if os.path.isfile(params.datapath + '_Image_Magnitude.txt') == True:
                    proc.T2imageprocess()
                    if params.single_plot == 1:
                        if self.dialog_plot != None:
                            self.dialog_plot.hide()
                            if self.dialog_plot.IComb_canvas != None: self.dialog_plot.IComb_canvas.hide()
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                        else:
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
            else:
                print('No file!!')

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
                else:
                    print('No file!!')
            params.datapath = self.datapathtemp
            if params.single_plot == 1:
                if self.dialog_plot != None:
                    self.dialog_plot.hide()
                    if self.dialog_plot.fig_canvas != None: self.dialog_plot.fig_canvas.hide()
                    if self.dialog_plot.IMag_canvas != None: self.dialog_plot.IMag_canvas.hide()
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else:
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()
        elif params.GUImode == 4 and (params.sequence == 2 or params.sequence == 3 or params.sequence == 6 or params.sequence == 7):
            proc.spectrum_process()
            if params.single_plot == 1:
                if self.dialog_plot != None:
                    self.dialog_plot.hide()
                    if self.dialog_plot.fig_canvas != None: self.dialog_plot.fig_canvas.hide()
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
                else:
                    self.dialog_plot = PlotWindow(self)
                    self.dialog_plot.show()
            else:
                self.dialog_plot = PlotWindow(self)
                self.dialog_plot.show()

        elif params.GUImode == 5 and (params.sequence == 0 or params.sequence == 1 or params.sequence == 2 or params.sequence == 3 \
                                      or params.sequence == 4 or params.sequence == 5 or params.sequence == 6 or params.sequence == 7 \
                                      or params.sequence == 8 or params.sequence == 9):
            
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_1.txt') == True:
                    if os.path.isfile(params.datapath + '/Image_Stitching_Header.json') == True:
                        proc.image_stitching_2D_json_process()
                    elif os.path.isfile(params.datapath + '/Image_Stitching_Header.txt') == True:
                        proc.image_stitching_2D_txt_process()
                    else:
                        print('No header file!!')
                    proc.image_analytics()
                    if params.single_plot == 1:
                        if self.dialog_plot != None:
                            self.dialog_plot.hide()
                            if self.dialog_plot.IMag_canvas != None: self.dialog_plot.IMag_canvas.hide()
                            if self.dialog_plot.IPha_canvas != None: self.dialog_plot.IPha_canvas.hide()
                            if self.dialog_plot.all_canvas != None: self.dialog_plot.all_canvas.hide()
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                        else:
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    print('No file!!')
            else:
                print('No directory!!')
                
        elif params.GUImode == 5 and params.sequence == 10:
            if os.path.isdir(params.datapath) == True:
                if os.path.isfile(params.datapath + '/Image_Stitching_1.txt') == True:
                    if os.path.isfile(params.datapath + '/Image_Stitching_Header.json') == True:
                        proc.image_stitching_3D_json_process()
                    elif os.path.isfile(params.datapath + '/Image_Stitching_Header.txt') == True:
                        proc.image_stitching_3D_txt_process()
                    else:
                        print('No header file!!')
                    # proc.image_analytics()
                    if params.single_plot == 1:
                        if self.dialog_plot != None:
                            self.dialog_plot.hide()
                            if self.dialog_plot.all_canvas != None: self.dialog_plot.all_canvas.hide()
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                        else:
                            self.dialog_plot = PlotWindow(self)
                            self.dialog_plot.show()
                    else:
                        self.dialog_plot = PlotWindow(self)
                        self.dialog_plot.show()
                else:
                    print('No file!!')
            else:
                print('No directory!!')

        params.saveFileData()

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
        choice = QMessageBox.question(self, 'Close Relax 2.0', 'Are you sure that you want to quit Relax 2.0?', \
                                      QMessageBox.Cancel | QMessageBox.Close, QMessageBox.Cancel)

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
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        params.motor_movement_step = params.motor_total_image_length / (params.motor_image_count - 1)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
        if params.motor_AC_position_center == 1:
            params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
            self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

        params.saveFileParameter()

    def update_motor_end_Position(self):
        params.motor_end_position = self.Motor_End_Position_doubleSpinBox.value()

        params.motor_total_image_length = round(params.motor_end_position - params.motor_start_position, 1)
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        params.motor_movement_step = params.motor_total_image_length / (params.motor_image_count - 1)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)
        params.motor_start_position = params.motor_end_position - params.motor_total_image_length
        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)
        if params.motor_AC_position_center == 1:
            params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
            self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

        params.saveFileParameter()

    def update_motor_total_image_length(self):
        params.motor_total_image_length = self.Motor_Total_Image_Length_doubleSpinBox.value()
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
        params.motor_movement_step = params.motor_total_image_length / (params.motor_image_count - 1)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)
        if params.motor_AC_position_center == 1:
            params.motor_AC_position = round(10*((params.motor_start_position + params.motor_end_position)/2))/10
            self.Motor_AC_Position_doubleSpinBox.setValue(params.motor_AC_position)

        params.saveFileParameter()

    def update_motor_movement_step(self):
        params.motor_movement_step = self.Motor_Movement_Step_doubleSpinBox.value()
        params.motor_total_image_length = (params.motor_image_count - 1) * params.motor_movement_step
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)

        params.saveFileParameter()

    def update_motor_image_count(self):
        params.motor_image_count = self.Motor_Image_Count_spinBox.value()
        params.motor_movement_step = params.motor_total_image_length / (params.motor_image_count - 1)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)

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

        if params.projaxis[0] == 1: self.Projection_X_radioButton.setChecked(True)
        if params.projaxis[1] == 1: self.Projection_Y_radioButton.setChecked(True)
        if params.projaxis[2] == 1: self.Projection_Z_radioButton.setChecked(True)

        self.Projection_Angle_spinBox.setValue(params.projectionangle)
        
        if params.average == 1: self.Average_radioButton.setChecked(True)
        self.Average_spinBox.setValue(params.averagecount)

        self.GROamplitude_spinBox.setValue(params.GROamplitude)
        if round(params.GROamplitude) < 300: self.GROamplitude_spinBox.setStyleSheet('color: yellow;')
        elif round(2*params.GROamplitude) > 8500: self.GROamplitude_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.GROamplitude_spinBox.setStyleSheet('color: #31363B;')
            else: self.GROamplitude_spinBox.setStyleSheet('color: #eff0f1;')
        
        self.GPEstep_spinBox.setValue(params.GPEstep)
        if round(params.GPEstep * params.nPE/2) > 8500: self.GPEstep_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.GPEstep_spinBox.setStyleSheet('color: #31363B;')
            else: self.GPEstep_spinBox.setStyleSheet('color: #eff0f1;')
        
        self.GSamplitude_spinBox.setValue(params.GSamplitude)
        if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B;')
            else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1;')

        self.Flipangle_Time_spinBox.setValue(params.flipangletime)
        self.Flipangle_Amplitude_spinBox.setValue(params.flipangleamplitude)

        self.GSPEstep_spinBox.setValue(params.GSPEstep)
        self.SPEsteps_spinBox.setValue(params.SPEsteps)
        if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B;')
            else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1;')

        self.GDiffamplitude_spinBox.setValue(params.Gdiffamplitude)
        if round(params.Gdiffamplitude) > 8500: self.GDiffamplitude_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.GDiffamplitude_spinBox.setStyleSheet('color: #31363B;')
            else: self.GDiffamplitude_spinBox.setStyleSheet('color: #eff0f1;')

        self.Crusher_Amplitude_spinBox.setValue(params.crusheramplitude)
        if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B;')
            else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1;')
        
        self.Spoiler_Amplitude_spinBox.setValue(params.spoileramplitude)
        if round(params.spoileramplitude) > 8500: self.GSpoiler_Amplitude_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #31363B;')
            else: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #eff0f1;')

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
        if params.GSamplitude == 0:
            params.GSposttime = 0
        else:
            params.GSposttime = int((200 * params.GSamplitude + 4 * params.flippulselength * params.GSamplitude) / 2 - 200 * params.GSamplitude / 2) / (params.GSamplitude / 2)

        if params.autograd == 1:
            self.Deltaf = 1 / (params.flippulselength) * 1000000

            self.Gz = (2 * np.pi * self.Deltaf) / (2 * np.pi * 42.57 * (params.slicethickness))
            params.GSamplitude = int(self.Gz / self.Gzsens * 1000)
            
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1;')

            if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1;')

            if round(params.spoileramplitude) > 8500: self.GSpoiler_Amplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #eff0f1;')

            self.Gz3D = (2 * np.pi / params.slicethickness) / (2 * np.pi * 42.57 * (self.GPEtime / 1000000))
            params.GSPEstep = int(self.Gz3D / self.Gzsens * 1000)
            if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B;')
                else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1;')

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
        
        params.saveFileParameter()

    def update_params(self):
        params.flippulselength = int(params.RFpulselength / 90 * params.flipangletime)

        if params.GSamplitude == 0:
            params.GSposttime = 0
        else:
            params.GSposttime = int((200 * params.GSamplitude + 4 * params.flippulselength * params.GSamplitude) / 2 - 200 * params.GSamplitude / 2) / (params.GSamplitude / 2)

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

        if self.Projection_X_radioButton.isChecked():
            params.projaxis[0] = 1
        else:
            params.projaxis[0] = 0
        if self.Projection_Y_radioButton.isChecked():
            params.projaxis[1] = 1
        else:
            params.projaxis[1] = 0
        if self.Projection_Z_radioButton.isChecked():
            params.projaxis[2] = 1
        else:
            params.projaxis[2] = 0

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
        if round(params.Gdiffamplitude) > 8500: self.GDiffamplitude_spinBox.setStyleSheet('color: red;')
        else:
            if params.GUItheme == 0: self.GDiffamplitude_spinBox.setStyleSheet('color: #31363B;')
            else: self.GDiffamplitude_spinBox.setStyleSheet('color: #eff0f1;')

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
            if round(params.GROamplitude) < 300: self.GROamplitude_spinBox.setStyleSheet('color: yellow;')
            elif round(2*params.GROamplitude) > 8500: self.GROamplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GROamplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.GROamplitude_spinBox.setStyleSheet('color: #eff0f1;')

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
            if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1;')
            
            params.spoileramplitude = self.Spoiler_Amplitude_spinBox.value()
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1;')
            
            params.GSamplitude = self.GSamplitude_spinBox.value()
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1;')
            
            params.GSPEstep = self.GSPEstep_spinBox.value()
            if round(params.GPEstep * params.nPE/2) > 8500: self.GPEstep_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GPEstep_spinBox.setStyleSheet('color: #31363B;')
                else: self.GPEstep_spinBox.setStyleSheet('color: #eff0f1;')
                
            if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B;')
                else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1;')

            params.saveFileParameter()

        elif params.autograd == 1:
            self.GROamplitude_spinBox.setValue(params.GROamplitude)
            if round(params.GROamplitude) < 300: self.GROamplitude_spinBox.setStyleSheet('color: yellow;')
            elif round(2*params.GROamplitude) > 8500: self.GROamplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GROamplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.GROamplitude_spinBox.setStyleSheet('color: #eff0f1;')
                
            self.GPEstep_spinBox.setValue(params.GPEstep)
            if round(params.GPEstep * params.nPE/2) > 8500: self.GPEstep_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GPEstep_spinBox.setStyleSheet('color: #31363B;')
                else: self.GPEstep_spinBox.setStyleSheet('color: #eff0f1;')
                
            self.Crusher_Amplitude_spinBox.setValue(params.crusheramplitude)
            if round(params.crusheramplitude) > 8500: self.Crusher_Amplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.Crusher_Amplitude_spinBox.setStyleSheet('color: #eff0f1;')
            
            self.Spoiler_Amplitude_spinBox.setValue(params.spoileramplitude)
            if round(params.spoileramplitude) > 8500: self.GSpoiler_Amplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.Spoiler_Amplitude_spinBox.setStyleSheet('color: #eff0f1;')
            
            self.GSamplitude_spinBox.setValue(params.GSamplitude)
            if round(params.GSamplitude) > 8500: self.GSamplitude_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GSamplitude_spinBox.setStyleSheet('color: #31363B;')
                else: self.GSamplitude_spinBox.setStyleSheet('color: #eff0f1;')
            
            self.GSPEstep_spinBox.setValue(params.GSPEstep)
            if round(params.GSPEstep * params.SPEsteps/2) > 8500: self.GSPEstep_spinBox.setStyleSheet('color: red;')
            else:
                if params.GUItheme == 0: self.GSPEstep_spinBox.setStyleSheet('color: #31363B;')
                else: self.GSPEstep_spinBox.setStyleSheet('color: #eff0f1;')
            

class ConfigWindow(Config_Window_Form, Config_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ConfigWindow, self).__init__(parent)
        self.setupUi(self)

        self.load_params()

        self.ui = loadUi('ui/config.ui')
        self.setWindowTitle('Config')
        self.setGeometry(420, 40, 760, 820)

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
        
        self.Image_Colormap_comboBox.clear()
        self.Image_Colormap_comboBox.addItems(['viridis', 'jet', 'gray', 'bone', 'inferno', 'plasma'])
        if params.imagecolormap == 'viridis': self.Image_Colormap_comboBox.setCurrentIndex(0)
        elif params.imagecolormap == 'jet': self.Image_Colormap_comboBox.setCurrentIndex(1)
        elif params.imagecolormap == 'gray': self.Image_Colormap_comboBox.setCurrentIndex(2)
        elif params.imagecolormap == 'bone': self.Image_Colormap_comboBox.setCurrentIndex(3)
        elif params.imagecolormap == 'inferno': self.Image_Colormap_comboBox.setCurrentIndex(4)
        elif params.imagecolormap == 'plasma': self.Image_Colormap_comboBox.setCurrentIndex(5)
        self.Image_Colormap_comboBox.currentIndexChanged.connect(self.update_params)

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
        
        if params.imagecolormap == 'viridis': self.Image_Colormap_comboBox.setCurrentIndex(0)
        elif params.imagecolormap == 'jet': self.Image_Colormap_comboBox.setCurrentIndex(1)
        elif params.imagecolormap == 'gray': self.Image_Colormap_comboBox.setCurrentIndex(2)
        elif params.imagecolormap == 'bone': self.Image_Colormap_comboBox.setCurrentIndex(3)
        elif params.imagecolormap == 'inferno': self.Image_Colormap_comboBox.setCurrentIndex(4)
        elif params.imagecolormap == 'plasma': self.Image_Colormap_comboBox.setCurrentIndex(5)

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
        
        if self.Image_Colormap_comboBox.currentIndex() == 0: params.imagecolormap = 'viridis'
        elif self.Image_Colormap_comboBox.currentIndex() == 1: params.imagecolormap = 'jet'
        elif self.Image_Colormap_comboBox.currentIndex() == 2: params.imagecolormap = 'gray'
        elif self.Image_Colormap_comboBox.currentIndex() == 3: params.imagecolormap = 'bone'
        elif self.Image_Colormap_comboBox.currentIndex() == 4: params.imagecolormap = 'inferno'
        elif self.Image_Colormap_comboBox.currentIndex() == 5: params.imagecolormap = 'plasma'
        
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
            self.update_params()

    def update_undersampling_methode2(self):
        if self.Undersampling_Methode_2_radioButton.isChecked():
            params.usmethode = 2
            self.Undersampling_Methode_1_radioButton.setChecked(False)
            self.update_params()


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
        self.setGeometry(420, 40, 760, 790)

        self.Autocenter_pushButton.setEnabled(params.connectionmode)
        self.Flipangle_pushButton.setEnabled(params.connectionmode)
        self.Tool_Shim_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B0_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B0_Slice_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B1_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_B1_Slice_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_Gradient_pushButton.setEnabled(params.connectionmode)
        self.Field_Map_Gradient_Slice_pushButton.setEnabled(params.connectionmode)

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
        
        self.ErnstAngleCalculator_T1_spinBox.valueChanged.connect(self.update_ernstanglecalc)
        self.ErnstAngleCalculator_TR_spinBox.valueChanged.connect(self.update_ernstanglecalc)
        self.update_ernstanglecalc()

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
        
        if params.GUImode == 0:
            self.flippulselengthtemp = params.flippulselength
            params.flippulselength = params.RFpulselength

            proc.Autocentertool()
            
            if params.single_plot == 1:
                if self.fig_canvas != None: self.fig_canvas.hide()
                if self.IMag_canvas != None: self.IMag_canvas.hide()
                if self.IPha_canvas != None: self.IPha_canvas.hide()
                if self.FMB0_canvas != None: self.FMB0_canvas.hide()
                if self.FMB1_canvas != None: self.FMB1_canvas.hide()

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax = self.fig.add_subplot(111);
            self.ax.plot(np.transpose(params.ACvalues[0, :]), np.transpose(params.ACvalues[1, :]), 'o', color='#000000')
            self.ax.set_xlabel('Frequency [MHz]')
            self.ax.set_ylabel('Signal')
            self.ax.set_title('Autocenter Signals')
            self.major_ticks = (params.ACstart, params.Reffrequency, params.ACstop)
            self.minor_ticks = np.linspace(params.ACstart, params.ACstop, round(abs((params.ACstop * 1.0e6 - params.ACstart * 1.0e6)) / (params.ACstepwidth)) + 1)
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

            params.flippulselength = self.flippulselengthtemp

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
        
        if params.GUImode == 0:
            self.flippulselengthtemp = params.flippulselength
            params.flippulselength = params.RFpulselength

            proc.Flipangletool()
            
            if params.single_plot == 1:
                if self.fig_canvas != None: self.fig_canvas.hide()
                if self.IMag_canvas != None: self.IMag_canvas.hide()
                if self.IPha_canvas != None: self.IPha_canvas.hide()
                if self.FMB0_canvas != None: self.FMB0_canvas.hide()
                if self.FMB1_canvas != None: self.FMB1_canvas.hide()

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax = self.fig.add_subplot(111);
            self.ax.plot(np.transpose(params.FAvalues[0, :]), np.transpose(params.FAvalues[1, :]), 'o-', color='#000000')
            self.ax.set_xlabel('Attenuation [dB]')
            self.ax.set_ylabel('Signal')
            self.ax.set_title('Flipangle Signals')
            if params.FAstop >= params.FAstart:
                self.major_ticks = np.linspace(math.floor(params.FAstart), math.ceil(params.FAstop), (math.ceil(params.FAstop) - math.floor(params.FAstart)) + 1)
                self.minor_ticks = np.linspace(math.floor(params.FAstart), math.ceil(params.FAstop), ((math.ceil(params.FAstop) - math.floor(params.FAstart))) * 4 + 1)
            else:
                self.major_ticks = np.linspace(math.floor(params.FAstop), math.ceil(params.FAstart), (math.ceil(params.FAstart) - math.floor(params.FAstop)) + 1)
                self.minor_ticks = np.linspace(math.floor(params.FAstop), math.ceil(params.FAstart), ((math.ceil(params.FAstart) - math.floor(params.FAstop))) * 4 + 1)
            self.ax.set_xticks(self.major_ticks)
            self.ax.set_xticks(self.minor_ticks, minor=True)
            self.ax.grid(which='major', color='#888888', linestyle='-')
            self.ax.grid(which='minor', color='#888888', linestyle=':')
            self.ax.grid(which='both', visible=True)
            self.ax.set_xlim((math.floor(params.FAstart), math.ceil(params.FAstop)))
            self.ax.set_ylim((0, 1.1 * np.max(np.transpose(params.FAvalues[1, :]))))
            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(420, 40, 1160, 950)
            self.fig_canvas.show()
            
            self.font = self.FA_RefRFattenuation_lineEdit.font()
            self.font.setPointSize(12)
            self.FA_RefRFattenuation_lineEdit.setFont(self.font)
            self.FA_RefRFattenuation_lineEdit.setText(str(params.RefRFattenuation))

            params.flippulselength = self.flippulselengthtemp

            self.Flipangle_pushButton.setEnabled(True)
            self.repaint()
            
        else:
            self.font = self.FA_RefRFattenuation_lineEdit.font()
            self.font.setPointSize(10)
            self.FA_RefRFattenuation_lineEdit.setFont(self.font)
            self.FA_RefRFattenuation_lineEdit.setText('Select spectroscopy!')
            
            self.Flipangle_pushButton.setEnabled(True)
            self.repaint()

    def Shimtool(self):
        self.Tool_Shim_pushButton.setEnabled(False)
        self.Tool_Shim_X_Ref_lineEdit.setText('')
        self.Tool_Shim_Y_Ref_lineEdit.setText('')
        self.Tool_Shim_Z_Ref_lineEdit.setText('')
        self.Tool_Shim_Z2_Ref_lineEdit.setText('')
        self.repaint()
        
        if params.ToolShimChannel != [0, 0, 0, 0]:
            if params.GUImode == 0:
                
                params.STgrad[0] = 0

                proc.Shimtool()
                
                if params.single_plot == 1:
                    if self.fig_canvas != None: self.fig_canvas.hide()
                    if self.IMag_canvas != None: self.IMag_canvas.hide()
                    if self.IPha_canvas != None: self.IPha_canvas.hide()
                    if self.FMB0_canvas != None: self.FMB0_canvas.hide()
                    if self.FMB1_canvas != None: self.FMB1_canvas.hide()

                self.fig = Figure()
                self.fig.set_facecolor('None')
                self.fig_canvas = FigureCanvas(self.fig)

                self.ax = self.fig.add_subplot(111);
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[1, :]), 'o-', color='#0072BD')
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[2, :]), 'o-', color='#D95319')
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[3, :]), 'o-', color='#EDB120')
                self.ax.plot(np.transpose(params.STvalues[0, :]), np.transpose(params.STvalues[4, :]), 'o-', color='#7E2F8E')
                self.ax.set_xlabel('Shim [mA]')
                self.ax.set_ylabel('Signal')
                self.ax.legend(['X', 'Y', 'Z', 'Z²'])
                self.ax.set_title('Shim Signals')
                if params.ToolShimStart <= params.ToolShimStop: self.major_ticks = np.linspace(math.floor(params.ToolShimStart / 10) * 10, math.ceil(params.ToolShimStop / 10) * 10, (math.ceil(params.ToolShimStop / 10) - math.floor(params.ToolShimStart / 10)) + 1)
                else: self.major_ticks = np.linspace(math.floor(params.ToolShimStop / 10) * 10, math.ceil(params.ToolShimStart / 10) * 10, (math.ceil(params.ToolShimStart / 10) - math.floor(params.ToolShimStop / 10)) + 1)

                self.ax.set_xticks(self.major_ticks)
                self.ax.grid(which='major', color='#888888', linestyle='-')
                self.ax.grid(which='major', visible=True)

                self.ax.set_xlim((math.floor(params.ToolShimStart / 10) * 10, math.ceil(params.ToolShimStop / 10) * 10))
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
        
        if params.GUImode == 0:
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
                params.ToolShimStart = int(self.grad_temp[1] - 60)
                params.ToolShimStop = int(self.grad_temp[1] + 60)
                params.ToolShimChannel = [0, 1, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[2, :] = params.STvalues[0, :]
                params.AutoSTvalues[3, :] = params.STvalues[2, :]
                
                params.STgrad[2] = int(params.STvalues[0, np.argmax(params.STvalues[2, :])])
                params.grad[1] = params.STgrad[2]
                params.ToolShimStart = int(self.grad_temp[2] - 60)
                params.ToolShimStop = int(self.grad_temp[2] + 60)
                params.ToolShimChannel = [0, 0, 1, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[4, :] = params.STvalues[0, :]
                params.AutoSTvalues[5, :] = params.STvalues[3, :]
                
                params.STgrad[3] = int(params.STvalues[0, np.argmax(params.STvalues[3, :])])
                params.grad[2] = params.STgrad[3]
                params.ToolShimStart = int(self.grad_temp[3] - 60)
                params.ToolShimStop = int(self.grad_temp[3] + 60)
                params.ToolShimChannel = [0, 0, 0, 1]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[6, :] = params.STvalues[0, :]
                params.AutoSTvalues[7, :] = params.STvalues[4, :]
                
                params.STgrad[4] = int(params.STvalues[0, np.argmax(params.STvalues[4, :])])
                params.grad[3] = params.STgrad[4]
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
                params.ToolShimSteps = 40
                params.AutoSTvalues = np.matrix(np.zeros((8, params.ToolShimSteps)))
        
                params.ToolShimChannel = [1, 0, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[0, :] = params.STvalues[0, :]
                params.AutoSTvalues[1, :] = params.STvalues[1, :]
                
                params.STgrad[1] = int(params.STvalues[0, np.argmax(params.STvalues[1, :])])
                params.grad[0] = params.STgrad[1]
                params.ToolShimChannel = [0, 1, 0, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[2, :] = params.STvalues[0, :]
                params.AutoSTvalues[3, :] = params.STvalues[2, :]
                
                params.STgrad[2] = int(params.STvalues[0, np.argmax(params.STvalues[2, :])])
                params.grad[1] = params.STgrad[2]
                params.ToolShimChannel = [0, 0, 1, 0]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[4, :] = params.STvalues[0, :]
                params.AutoSTvalues[5, :] = params.STvalues[3, :]
                
                params.STgrad[3] = int(params.STvalues[0, np.argmax(params.STvalues[3, :])])
                params.grad[2] = params.STgrad[3]
                params.ToolShimChannel = [0, 0, 0, 1]
                params.saveFileParameter()
                
                proc.Shimtool()
                
                params.AutoSTvalues[6, :] = params.STvalues[0, :]
                params.AutoSTvalues[7, :] = params.STvalues[4, :]
                
                params.STgrad[4] = int(params.STvalues[0, np.argmax(params.STvalues[4, :])])
                params.grad[3] = params.STgrad[4]
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
                        
            np.savetxt('tooldata/Auto_Shim_Tool_Data.txt', np.transpose(params.AutoSTvalues))
            
            if params.single_plot == 1:
                if self.fig_canvas != None: self.fig_canvas.hide()
                if self.IMag_canvas != None: self.IMag_canvas.hide()
                if self.IPha_canvas != None: self.IPha_canvas.hide()
                if self.FMB0_canvas != None: self.FMB0_canvas.hide()
                if self.FMB1_canvas != None: self.FMB1_canvas.hide()

            self.fig = Figure()
            self.fig.set_facecolor('None')
            self.fig_canvas = FigureCanvas(self.fig)

            self.ax = self.fig.add_subplot(111);
            self.ax.plot(np.transpose(params.AutoSTvalues[0, :]), np.transpose(params.AutoSTvalues[1, :]), 'o-', color='#0072BD')
            self.ax.plot(np.transpose(params.AutoSTvalues[2, :]), np.transpose(params.AutoSTvalues[3, :]), 'o-', color='#D95319')
            self.ax.plot(np.transpose(params.AutoSTvalues[4, :]), np.transpose(params.AutoSTvalues[5, :]), 'o-', color='#EDB120')
            self.ax.plot(np.transpose(params.AutoSTvalues[6, :]), np.transpose(params.AutoSTvalues[7, :]), 'o-', color='#7E2F8E')
            self.ax.set_xlabel('Shim [mA]')
            self.ax.set_ylabel('Signal')
            self.ax.legend(['X', 'Y', 'Z', 'Z²'])
            self.ax.set_title('Shim Signals')
            if params.ToolAutoShimMode == 1: self.major_ticks = np.linspace(math.floor((np.min(params.grad)-60) / 10) * 10, math.ceil((np.max(params.grad)+60) / 10) * 10, math.ceil((np.max(params.grad)+60) / 10) - math.floor((np.min(params.grad)-60) / 10) + 1)
            else: self.major_ticks = np.linspace(-400, 400, 41)
            self.ax.set_xticks(self.major_ticks)
            self.ax.grid(which='major', color='#888888', linestyle='-')
            self.ax.grid(which='major', visible=True)
            if params.ToolAutoShimMode == 1: self.ax.set_xlim((math.floor((np.min(params.grad)-60) / 10) * 10, math.ceil((np.max(params.grad)+60) / 10) * 10))
            else: self.ax.set_xlim((-400, 400))
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
            if self.fig_canvas != None: self.fig_canvas.hide()
            if self.IMag_canvas != None: self.IMag_canvas.hide()
            if self.IPha_canvas != None: self.IPha_canvas.hide()
            if self.FMB0_canvas != None: self.FMB0_canvas.hide()
            if self.FMB1_canvas != None: self.FMB1_canvas.hide()

        # self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor('None')
        # self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
        # self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap); self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
        # self.IMag_ax.set_title('Magnitude Image')
        # self.IMag_canvas.draw()
        # self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        # self.IMag_canvas.setGeometry(820, 40, 400, 355)
        # self.IMag_canvas.show()

        self.IPha_fig = Figure();
        self.IPha_canvas = FigureCanvas(self.IPha_fig);
        self.IPha_fig.set_facecolor('None')
        self.IPha_ax = self.IPha_fig.add_subplot(111);
        self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
        self.IPha_ax.imshow(params.img_pha, cmap='gray');
        self.IPha_ax.axis('off');
        self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
        self.IPha_ax.set_title('Phase Image')
        self.IPha_canvas.draw()
        self.IPha_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IPha_canvas.setGeometry(420, 40, 575, 455)
        self.IPha_canvas.show()

        self.FMB0_fig = Figure();
        self.FMB0_canvas = FigureCanvas(self.FMB0_fig);
        self.FMB0_fig.set_facecolor('None')
        self.FMB0_ax = self.FMB0_fig.add_subplot(111);
        self.FMB0_ax.grid(False);  # self.FMB0_ax.axis(frameon=False)
        self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet');
        self.FMB0_ax.axis('off');
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
            if self.fig_canvas != None: self.fig_canvas.hide()
            if self.IMag_canvas != None: self.IMag_canvas.hide()
            if self.IPha_canvas != None: self.IPha_canvas.hide()
            if self.FMB0_canvas != None: self.FMB0_canvas.hide()
            if self.FMB1_canvas != None: self.FMB1_canvas.hide()

        # self.IMag_fig = Figure(); self.IMag_canvas = FigureCanvas(self.IMag_fig); self.IMag_fig.set_facecolor('None')
        # self.IMag_ax = self.IMag_fig.add_subplot(111); self.IMag_ax.grid(False); self.IMag_ax.axis(frameon=False)
        # self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap); self.IMag_ax.axis('off'); self.IMag_ax.set_aspect(1.0/self.IMag_ax.get_data_ratio())
        # self.IMag_ax.set_title('Magnitude Image')
        # self.IMag_canvas.draw()
        # self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        # self.IMag_canvas.setGeometry(820, 40, 400, 355)
        # self.IMag_canvas.show()

        self.IPha_fig = Figure();
        self.IPha_canvas = FigureCanvas(self.IPha_fig);
        self.IPha_fig.set_facecolor('None')
        self.IPha_ax = self.IPha_fig.add_subplot(111);
        self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
        self.IPha_ax.imshow(params.img_pha, cmap='gray');
        self.IPha_ax.axis('off');
        self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
        self.IPha_ax.set_title('Phase Image')
        self.IPha_canvas.draw()
        self.IPha_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IPha_canvas.setGeometry(420, 40, 575, 455)
        self.IPha_canvas.show()

        self.FMB0_fig = Figure();
        self.FMB0_canvas = FigureCanvas(self.FMB0_fig);
        self.FMB0_fig.set_facecolor('None')
        self.FMB0_ax = self.FMB0_fig.add_subplot(111);
        self.FMB0_ax.grid(False);  # self.FMB0_ax.axis(frameon=False)
        self.FMB0_ax.imshow(params.B0DeltaB0mapmasked, cmap='jet');
        self.FMB0_ax.axis('off');
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
            if self.fig_canvas != None: self.fig_canvas.hide()
            if self.IMag_canvas != None: self.IMag_canvas.hide()
            if self.IPha_canvas != None: self.IPha_canvas.hide()
            if self.FMB0_canvas != None: self.FMB0_canvas.hide()
            if self.FMB1_canvas != None: self.FMB1_canvas.hide()

        self.IMag_fig = Figure();
        self.IMag_canvas = FigureCanvas(self.IMag_fig);
        self.IMag_fig.set_facecolor('None');
        self.IMag_ax = self.IMag_fig.add_subplot(111);
        self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
        if params.imagefilter == 1:
            self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap)
        else:
            self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap)
        self.IMag_ax.axis('off');
        self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
        self.IMag_ax.set_title('Magnitude Image')
        self.IMag_canvas.draw()
        self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IMag_canvas.setGeometry(420, 40, 575, 455)
        self.IMag_canvas.show()

        self.FMB1_fig = Figure();
        self.FMB1_canvas = FigureCanvas(self.FMB1_fig);
        self.FMB1_fig.set_facecolor('None');
        self.FMB1_ax = self.FMB1_fig.add_subplot(111);
        self.FMB1_ax.grid(False);  # self.FMB1_ax.axis(frameon=False)
        self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet');
        self.FMB1_ax.axis('off');
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
            if self.fig_canvas != None: self.fig_canvas.hide()
            if self.IMag_canvas != None: self.IMag_canvas.hide()
            if self.IPha_canvas != None: self.IPha_canvas.hide()
            if self.FMB0_canvas != None: self.FMB0_canvas.hide()
            if self.FMB1_canvas != None: self.FMB1_canvas.hide()

        self.IMag_fig = Figure();
        self.IMag_canvas = FigureCanvas(self.IMag_fig);
        self.IMag_fig.set_facecolor('None')
        self.IMag_ax = self.IMag_fig.add_subplot(111);
        self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
        if params.imagefilter == 1:
            self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap)
        else:
            self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap)
        self.IMag_ax.axis('off');
        self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
        self.IMag_ax.set_title('Magnitude Image')
        self.IMag_canvas.draw()
        self.IMag_canvas.setWindowTitle('Tool Plot - ' + params.datapath + '.txt')
        self.IMag_canvas.setGeometry(420, 40, 575, 455)
        self.IMag_canvas.show()

        self.FMB1_fig = Figure();
        self.FMB1_canvas = FigureCanvas(self.FMB1_fig);
        self.FMB1_fig.set_facecolor('None')
        self.FMB1_ax = self.FMB1_fig.add_subplot(111);
        self.FMB1_ax.grid(False);  # self.FMB1_ax.axis(frameon=False)
        self.FMB1_ax.imshow(params.B1alphamapmasked, cmap='jet');
        self.FMB1_ax.axis('off');
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

        print('\033[1m' + 'WIP Field_Map_Gradient' + '\033[0m')

        proc.FieldMapGradient()
        
        if params.single_plot == 1:
            if self.fig_canvas != None: self.fig_canvas.hide()
            if self.IMag_canvas != None: self.IMag_canvas.hide()
            if self.IPha_canvas != None: self.IPha_canvas.hide()
            if self.FMB0_canvas != None: self.FMB0_canvas.hide()
            if self.FMB1_canvas != None: self.FMB1_canvas.hide()

        self.IMag_fig = Figure()
        self.IMag_canvas = FigureCanvas(self.IMag_fig)
        self.IMag_fig.set_facecolor('None')
        self.IMag_ax = self.IMag_fig.add_subplot(111)
        if params.imagefilter == 1:
            self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
        else:
            self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
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

        self.Field_Map_Gradient_pushButton.setEnabled(True)
        self.repaint()

    def Field_Map_Gradient_Slice(self):
        self.Field_Map_Gradient_Slice_pushButton.setEnabled(False)
        self.repaint()

        print('\033[1m' + 'WIP Field_Map_Gradient_Slice' + '\033[0m')

        proc.FieldMapGradientSlice()
        
        if params.single_plot == 1:
            if self.fig_canvas != None: self.fig_canvas.hide()
            if self.IMag_canvas != None: self.IMag_canvas.hide()
            if self.IPha_canvas != None: self.IPha_canvas.hide()
            if self.FMB0_canvas != None: self.FMB0_canvas.hide()
            if self.FMB1_canvas != None: self.FMB1_canvas.hide()

        self.IMag_fig = Figure()
        self.IMag_canvas = FigureCanvas(self.IMag_fig)
        self.IMag_fig.set_facecolor('None')
        self.IMag_ax = self.IMag_fig.add_subplot(111)
        if params.imagefilter == 1:
            self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
        else:
            self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, extent=[(-params.FOV / 2), (params.FOV / 2), (-params.FOV / 2), (params.FOV / 2)])
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

        self.Field_Map_Gradient_Slice_pushButton.setEnabled(True)
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
                                            , 'RF Loopback Test Sequence (Sinc, 180°)', 'Gradient Test Sequence', 'RF SAR Calibration Test Sequence')
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
                self.protocoltemp = np.genfromtxt(self.prot_datapath + '/Protocol.txt')
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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
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
                    print('Autorecenter to: ', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if params.measurement_time_dialog == 1:
                        msg_box = QMessageBox()
                        msg_box.setText('Autorecenter to: ' + str(params.frequency) + 'MHz')
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).animateClick(params.TR-100)
                        msg_box.button(QMessageBox.Ok).hide()
                        msg_box.exec()
                    else: time.sleep((params.TR-100)/1000)
                    time.sleep(0.1)
                    seq.sequence_upload()
            else:
                seq.sequence_upload()
        elif params.GUImode == 6:
            msg_box = QMessageBox()
            msg_box.setText('Pause: ' + str(params.TR) + 's')
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).animateClick(int(params.TR*1000))
            msg_box.button(QMessageBox.Ok).hide()
            msg_box.exec()
        elif params.GUImode == 7:
            self.protocol_messagebox_string = ('Change Sample!', 'Move Sample!', 'Rotate Sample!')
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

        if params.GUImode == 0:
            if params.sequence == 18 or params.sequence == 19 or params.sequence == 20 or params.sequence == 21:
                self.rf_loopback_test_spectrum_plot_init()
            else:
                self.spectrum_plot_init()
            self.Save_Spectrum_Data_pushButton.setEnabled(True)
            
        elif params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36:
                self.imaging_3D_plot_init()
                self.Save_Image_Data_pushButton.setEnabled(True)
                self.Save_Mag_Image_Data_pushButton.setEnabled(True)
                self.Save_Pha_Image_Data_pushButton.setEnabled(True)
                self.View_3D_Data_pushButton.setEnabled(True)
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
                self.imaging_stitching_plot_init()
                
                with open(params.datapath + '/Image_Stitching_Header.json', 'r') as j:
                    jsonparams = json.loads(j.read())

                imageorientation = jsonparams['Image orientation']
                if imageorientation == 'ZX' or imageorientation == 'XZ':
                    self.View_3D_Data_pushButton.setEnabled(True)
                
                self.Save_Image_Data_pushButton.setEnabled(True)
                self.Save_Mag_Image_Data_pushButton.setEnabled(True)
                self.Save_Pha_Image_Data_pushButton.setEnabled(True)
                    
            elif params.sequence == 10:
                self.imaging_stitching_3D_plot_init()
                self.Save_Image_Data_pushButton.setEnabled(True)
                self.Save_Mag_Image_Data_pushButton.setEnabled(True)
                self.Save_Pha_Image_Data_pushButton.setEnabled(True)
                self.View_3D_Data_pushButton.setEnabled(True)

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
        
        self.Image_Minimum_doubleSpinBox.setKeyboardTracking(False)
        self.Image_Minimum_doubleSpinBox.valueChanged.connect(self.update_params)
        self.Image_Maximum_doubleSpinBox.setKeyboardTracking(False)
        self.Image_Maximum_doubleSpinBox.valueChanged.connect(self.update_params)

    def load_params(self):
        if params.GUImode == 0:
            self.Frequncyaxisrange_spinBox.setEnabled(True)
            self.Frequncyaxisrange_spinBox.setValue(params.frequencyplotrange)
            self.Center_Frequency_lineEdit.setText(str(params.centerfrequency))
            self.FWHM_lineEdit.setText(str(params.FWHM))
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Image_Minimum_doubleSpinBox.setEnabled(False)
            self.Image_Minimum_doubleSpinBox.setValue(0.0)
            self.Image_Maximum_doubleSpinBox.setEnabled(False)
            self.Image_Maximum_doubleSpinBox.setValue(0.0)
            self.Inhomogeneity_lineEdit.setText(str(params.inhomogeneity))
            self.Animation_Step_spinBox.setValue(params.animationstep)
        elif params.GUImode == 1:
            self.Frequncyaxisrange_spinBox.setEnabled(False)
            self.Frequncyaxisrange_spinBox.setValue(250000)
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Image_Minimum_doubleSpinBox.setEnabled(True)
            self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
            self.Image_Maximum_doubleSpinBox.setEnabled(True)
            self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
            self.Animation_Step_spinBox.setValue(params.animationstep)
        elif params.GUImode == 5:
            self.Frequncyaxisrange_spinBox.setEnabled(False)
            self.Frequncyaxisrange_spinBox.setValue(250000)
            self.Peak_lineEdit.setText(str(params.peakvalue))
            self.Noise_lineEdit.setText(str(params.noise))
            self.SNR_lineEdit.setText(str(params.SNR))
            self.Image_Minimum_doubleSpinBox.setEnabled(False)
            self.Image_Minimum_doubleSpinBox.setValue(0.0)
            self.Image_Maximum_doubleSpinBox.setEnabled(False)
            self.Image_Maximum_doubleSpinBox.setValue(0.0)
            self.Animation_Step_spinBox.setValue(params.animationstep)

    def update_params(self):
        params.frequencyplotrange = self.Frequncyaxisrange_spinBox.value()
        params.imageminimum = self.Image_Minimum_doubleSpinBox.value()
        params.imagemaximum = self.Image_Maximum_doubleSpinBox.value()
        params.animationstep = self.Animation_Step_spinBox.value()

        params.saveFileParameter()

        if params.GUImode == 0:
            if params.sequence == 18 or params.sequence == 19 or params.sequence == 20 or params.sequence == 21:
                self.rf_loopback_test_spectrum_plot_init()
            else:
                self.spectrum_plot_init()
            self.Save_Spectrum_Data_pushButton.setEnabled(True)
        elif params.GUImode == 1 and params.sequence != 34 and params.sequence != 35 and params.sequence != 36 and params.sequence != 14 and params.sequence != 31:
            if self.IMag_canvas != None: self.IMag_canvas.hide()
            if self.IPha_canvas != None: self.IPha_canvas.hide()
            if self.kMag_canvas != None: self.kMag_canvas.hide()
            if self.kPha_canvas != None: self.kPha_canvas.hide()
            if self.all_canvas != None: self.all_canvas.hide()
            self.imaging_plot_init()
        elif params.GUImode == 4:
            self.fig_canvas.hide()
            self.projection_plot_init()

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
        self.ax1.set_xlabel('$\Delta$ Frequency [Hz]')
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
        self.ax2.set_xlabel('time [ms]')
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
        self.ax1.set_xlabel('$\Delta$ Frequency [Hz]')
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
        self.ax2.set_xlabel('time [µs]')
        self.major_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int((int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]))/10) + 1)
        self.minor_ticks = np.linspace(0, int(math.ceil(params.timeaxis[int(params.timeaxis.shape[0] - 1)])), int((int(params.timeaxis[int(params.timeaxis.shape[0] - 1)]) * 5)/10) + 1)
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
            self.ax1.set_xlabel('$\Delta$ Frequency [Hz]')
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
            self.ax3.set_xlabel('$\Delta$ Frequency [Hz]')
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
            self.ax5.set_xlabel('$\Delta$ Frequency [Hz]')
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

            self.IMag_ax = self.IMag_fig.add_subplot(111);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            if params.imagefilter == 1:
                self.IMag_ax.imshow(self.projzx[int(self.projzx.shape[0] / 2 - params.nPE / 2):int(self.projzx.shape[0] / 2 + params.nPE / 2), int(self.projzx.shape[1] / 2 - params.nPE / 2):int(self.projzx.shape[1] / 2 + params.nPE / 2)], interpolation='gaussian', cmap=params.imagecolormap)
            else:
                self.IMag_ax.imshow(self.projzx[int(self.projzx.shape[0] / 2 - params.nPE / 2):int(self.projzx.shape[0] / 2 + params.nPE / 2), int(self.projzx.shape[1] / 2 - params.nPE / 2):int(self.projzx.shape[1] / 2 + params.nPE / 2)], cmap=params.imagecolormap)
            self.IMag_ax.axis('off');
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')

            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(1030, 40, 550, 550)
            self.IMag_canvas.show()

    def T1_plot_init(self):
        self.fig1 = Figure()
        self.fig1.set_facecolor('None')
        self.fig_canvas1 = FigureCanvas(self.fig1)

        self.ax = self.fig1.add_subplot(111);

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
        self.ax.set_ylim(0, 1.1 * np.max(params.T1yvalues1))
        self.ax.legend(loc='lower right')
        self.ax.set_title('T1 = ' + str(params.T1) + 'ms, r = ' + str(round(params.T1linregres.rvalue, 2)))

        self.fig_canvas1.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas1.setGeometry(420, 40, 575, 455)
        self.fig_canvas1.show()

        self.fig2 = Figure()
        self.fig2.set_facecolor('None')
        self.fig_canvas2 = FigureCanvas(self.fig2)

        self.ax = self.fig2.add_subplot(111);

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
        self.IComb_fig = Figure();
        self.IComb_canvas = FigureCanvas(self.IComb_fig);
        self.IComb_fig.set_facecolor('None');
        self.IComb_ax = self.IComb_fig.add_subplot(111);
        self.IComb_ax.grid(False);  # self.IComb_ax.axis(frameon=False)
        if params.imagefilter == 1:
            self.IComb_ax.imshow(params.T1img_mag[params.T1img_mag.shape[0] - 1, :, :], interpolation='gaussian', cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T1imgvalues, interpolation='gaussian', cmap='jet', alpha=0.5)
        else:
            self.IComb_ax.imshow(params.T1img_mag[params.T1img_mag.shape[0] - 1, :, :], cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T1imgvalues, cmap='jet', alpha=0.5)
        self.IComb_ax.axis('off');
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

        self.ax = self.fig.add_subplot(111);

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
        self.ax.set_ylim(0, 1.1 * np.max(params.T2yvalues))
        self.ax.legend()
        self.ax.set_title('T2 = ' + str(params.T2) + 'ms, r = ' + str(round(params.T2linregres.rvalue, 2)))

        self.fig_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.fig_canvas.setGeometry(420, 40, 575, 455)
        self.fig_canvas.show()

    def T2_imaging_plot_init(self):
        self.IComb_fig = Figure();
        self.IComb_canvas = FigureCanvas(self.IComb_fig);
        self.IComb_fig.set_facecolor('None');
        self.IComb_ax = self.IComb_fig.add_subplot(111);
        self.IComb_ax.grid(False);  # self.IComb_ax.axis(frameon=False)
        if params.imagefilter == 1:
            self.IComb_ax.imshow(params.T2img_mag[0, :, :], interpolation='gaussian', cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T2imgvalues, interpolation='gaussian', cmap='jet', alpha=0.5)
        else:
            self.IComb_ax.imshow(params.T2img_mag[0, :, :], cmap='gray')
            self.cb = self.IComb_ax.imshow(params.T2imgvalues, cmap='jet', alpha=0.5)
        self.IComb_ax.axis('off');
        self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
        self.IComb_ax.set_title('T2')
        self.IComb_fig.colorbar(self.cb, label='T2 in ms')
        self.IComb_canvas.draw()
        self.IComb_canvas.setWindowTitle('Plot - ' + params.datapath + '_Image_Magnitude.txt')
        self.IComb_canvas.setGeometry(420, 40, 800, 750)
        self.IComb_canvas.show()

    def imaging_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure();
            self.IMag_canvas = FigureCanvas(self.IMag_fig);
            self.IMag_fig.set_facecolor('None');
            self.IPha_fig = Figure();
            self.IPha_canvas = FigureCanvas(self.IPha_fig);
            self.IPha_fig.set_facecolor('None');
            self.kMag_fig = Figure();
            self.kMag_canvas = FigureCanvas(self.kMag_fig);
            self.kMag_fig.set_facecolor('None');
            self.kPha_fig = Figure();
            self.kPha_canvas = FigureCanvas(self.kPha_fig);
            self.kPha_fig.set_facecolor('None');

            self.IMag_ax = self.IMag_fig.add_subplot(111);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.IPha_fig.add_subplot(111);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.kMag_fig.add_subplot(111);
            self.kMag_ax.grid(False);  # self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.kPha_fig.add_subplot(111);
            self.kPha_ax.grid(False);  # self.kPha_ax.axis(frameon=False)
            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum)
            else:
                self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum)
            self.IMag_ax.axis('off');
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_pha, cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno');
            self.kPha_ax.axis('off');
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
            
            params.plot_status = 1

        else:
            self.all_fig = Figure();
            self.all_canvas = FigureCanvas(self.all_fig);
            self.all_fig.set_facecolor('None');

            gs = GridSpec(2, 2, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(gs[0, 0]);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[0, 1]);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.all_fig.add_subplot(gs[1, 0]);
            self.kMag_ax.grid(False);  # self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.all_fig.add_subplot(gs[1, 1]);
            self.kPha_ax.grid(False);  # self.kPha_ax.axis(frameon=False)
            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum)
            else:
                self.IMag_ax.imshow(params.img_mag, cmap=params.imagecolormap, vmin=params.imageminimum, vmax=params.imagemaximum)
            self.IMag_ax.axis('off');
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_pha, cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno');
            self.kPha_ax.axis('off');
            self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1160, 950)
            self.all_canvas.show()

    def imaging_stitching_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure();
            self.IMag_canvas = FigureCanvas(self.IMag_fig);
            self.IMag_fig.set_facecolor('None');
            self.IPha_fig = Figure();
            self.IPha_canvas = FigureCanvas(self.IPha_fig);
            self.IPha_fig.set_facecolor('None');

            self.IMag_ax = self.IMag_fig.add_subplot(111);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.IPha_fig.add_subplot(111);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)

            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap)
            else:
                self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap)
            self.IMag_ax.axis('off');
            self.IMag_ax.axis('equal')
            self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.axis('equal')
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
            self.all_fig = Figure();
            self.all_canvas = FigureCanvas(self.all_fig);
            self.all_fig.set_facecolor('None');

            gs = GridSpec(1, 2, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(gs[0, 0]);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[0, 1]);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)

            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_st_mag[:, :], interpolation='gaussian', cmap=params.imagecolormap)
            else:
                self.IMag_ax.imshow(params.img_st_mag[:, :], cmap=params.imagecolormap)
            self.IMag_ax.axis('off');
            self.IMag_ax.axis('equal')
            self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_st_pha[:, :], interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.axis('equal')
            self.IPha_ax.set_title('Phase Image')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1160, 950)
            self.all_canvas.show()

    def imaging_3D_plot_init(self):
        self.all_fig = Figure();
        self.all_canvas = FigureCanvas(self.all_fig);
        self.all_fig.set_facecolor('None');

        gs = GridSpec(4, params.img_mag.shape[0], figure=self.all_fig)
        
        for n in range(params.img_mag.shape[0]):
            self.IMag_ax = self.all_fig.add_subplot(gs[0, n]);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[1, n]);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.all_fig.add_subplot(gs[2, n]);
            self.kMag_ax.grid(False);  # self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.all_fig.add_subplot(gs[3, n]);
            self.kPha_ax.grid(False);  # self.kPha_ax.axis(frameon=False)

            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap)
            else:
                self.IMag_ax.imshow(params.img_mag[n, :, :], cmap=params.imagecolormap)
            self.IMag_ax.axis('off');
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            # self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_pha[n, :, :], interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_pha[n, :, :], cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
            # self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp[n, :, :]), cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
            else:
                self.kMag_ax.imshow(params.k_amp[n, :, :], cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
            # self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha[n, :, :], cmap='inferno');
            self.kPha_ax.axis('off');
            self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
        # self.kPha_ax.set_title('k-Space Phase')

        self.all_canvas.draw()
        self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.all_canvas.setGeometry(420, 40, 1160, 950)
        self.all_canvas.show()

    def imaging_stitching_3D_plot_init(self):
        self.all_fig = Figure();
        self.all_canvas = FigureCanvas(self.all_fig);
        self.all_fig.set_facecolor('None');
        gs = GridSpec(params.img_st_mag.shape[0], 2, figure=self.all_fig)

        for n in range(params.img_st_mag.shape[0]):
            self.IMag_ax = self.all_fig.add_subplot(gs[n, 0]);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[n, 1]);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_st_mag[n, :, :], interpolation='gaussian', cmap=params.imagecolormap)
            else:
                self.IMag_ax.imshow(params.img_st_mag[n, :, :], cmap=params.imagecolormap)
            self.IMag_ax.axis('off');
            self.IMag_ax.axis('equal')
            if n == 0: self.IMag_ax.set_title('Magnitude Image')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_st_pha[n, :, :], interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.axis('equal')
            if n == 0: self.IPha_ax.set_title('Phase Image')

        self.all_canvas.draw()
        self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.all_canvas.setGeometry(420, 40, 1160, 950)
        self.all_canvas.show()

    def imaging_diff_plot_init(self):
        if params.imagplots == 1:
            self.IMag_fig = Figure();
            self.IMag_canvas = FigureCanvas(self.IMag_fig);
            self.IMag_fig.set_facecolor('None');
            self.IDiff_fig = Figure();
            self.IDiff_canvas = FigureCanvas(self.IDiff_fig);
            self.IDiff_fig.set_facecolor('None');
            self.IComb_fig = Figure();
            self.IComb_canvas = FigureCanvas(self.IComb_fig);
            self.IComb_fig.set_facecolor('None');
            self.IPha_fig = Figure();
            self.IPha_canvas = FigureCanvas(self.IPha_fig);
            self.IPha_fig.set_facecolor('None');
            self.kMag_fig = Figure();
            self.kMag_canvas = FigureCanvas(self.kMag_fig);
            self.kMag_fig.set_facecolor('None');
            self.kPha_fig = Figure();
            self.kPha_canvas = FigureCanvas(self.kPha_fig);
            self.kPha_fig.set_facecolor('None');

            self.IMag_ax = self.IMag_fig.add_subplot(111);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IDiff_ax = self.IDiff_fig.add_subplot(111);
            self.IDiff_ax.grid(False);  # self.IDiff_ax.axis(frameon=False)
            self.IComb_ax = self.IComb_fig.add_subplot(111);
            self.IComb_ax.grid(False);  # self.IComb_ax.axis(frameon=False)
            self.IPha_ax = self.IPha_fig.add_subplot(111);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.kMag_fig.add_subplot(111);
            self.kMag_ax.grid(False);  # self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.kPha_fig.add_subplot(111);
            self.kPha_ax.grid(False);  # self.kPha_ax.axis(frameon=False)

            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
            else:
                self.IMag_ax.imshow(params.img_mag, cmap='gray')
            self.IMag_ax.axis('off');
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IDiff_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap)
            self.IDiff_ax.axis('off');
            self.IDiff_ax.set_aspect(1.0 / self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            self.IComb_ax.axis('off');
            self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_pha, cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno');
            self.kPha_ax.axis('off');
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
            self.all_fig = Figure();
            self.all_canvas = FigureCanvas(self.all_fig);
            self.all_fig.set_facecolor('None');

            gs = GridSpec(2, 3, figure=self.all_fig)
            self.IMag_ax = self.all_fig.add_subplot(gs[0, 0]);
            self.IMag_ax.grid(False);  # self.IMag_ax.axis(frameon=False)
            self.IDiff_ax = self.all_fig.add_subplot(gs[0, 1]);
            self.IDiff_ax.grid(False);  # self.IDiff_ax.axis(frameon=False)
            self.IComb_ax = self.all_fig.add_subplot(gs[0, 2]);
            self.IComb_ax.grid(False);  # self.IComb_ax.axis(frameon=False)
            self.IPha_ax = self.all_fig.add_subplot(gs[1, 0]);
            self.IPha_ax.grid(False);  # self.IPha_ax.axis(frameon=False)
            self.kMag_ax = self.all_fig.add_subplot(gs[1, 1]);
            self.kMag_ax.grid(False);  # self.kMag_ax.axis(frameon=False)
            self.kPha_ax = self.all_fig.add_subplot(gs[1, 2]);
            self.kPha_ax.grid(False);  # self.kPha_ax.axis(frameon=False)

            if params.imagefilter == 1:
                self.IMag_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
            else:
                self.IMag_ax.imshow(params.img_mag, cmap='gray')
            self.IMag_ax.axis('off');
            self.IMag_ax.set_aspect(1.0 / self.IMag_ax.get_data_ratio())
            self.IMag_ax.set_title('Magnitude Image')
            self.IDiff_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap)
            self.IDiff_ax.axis('off');
            self.IDiff_ax.set_aspect(1.0 / self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap=params.imagecolormap, alpha=0.5)
            self.IComb_ax.axis('off');
            self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
            if params.imagefilter == 1:
                self.IPha_ax.imshow(params.img_pha, interpolation='gaussian', cmap='gray');
            else:
                self.IPha_ax.imshow(params.img_pha, cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.set_aspect(1.0 / self.IPha_ax.get_data_ratio())
            self.IPha_ax.set_title('Phase Image')
            if params.lnkspacemag == 1:
                self.kMag_ax.imshow(np.log(params.k_amp), cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('ln(k-Space Magnitude)')
            else:
                self.kMag_ax.imshow(params.k_amp, cmap='inferno');
                self.kMag_ax.axis('off');
                self.kMag_ax.set_aspect(1.0 / self.kMag_ax.get_data_ratio())
                self.kMag_ax.set_title('k-Space Magnitude')
            self.kPha_ax.imshow(params.k_pha, cmap='inferno');
            self.kPha_ax.axis('off');
            self.kPha_ax.set_aspect(1.0 / self.kPha_ax.get_data_ratio())
            self.kPha_ax.set_title('k-Space Phase')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 1300, 750)
            self.all_canvas.show()
            
    def save_spectrum_data(self):
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 0:
            self.datatxt = np.matrix(np.zeros((params.freqencyaxis.shape[0], 2)))
            self.datatxt[:, 0] = params.freqencyaxis.reshape(params.freqencyaxis.shape[0], 1)
            self.datatxt[:, 1] = params.spectrumfft
            np.savetxt('spectrumdata/' + params.dataTimestamp + '_Spectrum_Data.txt', self.datatxt)
            print('Spectrum data saved!')
        elif params.GUImode == 2:
            self.datatxt = np.matrix(np.zeros((params.T1xvalues.shape[0], 3)))
            self.datatxt[:, 0] = params.T1xvalues.reshape(params.T1xvalues.shape[0], 1)
            self.datatxt[:, 1] = params.T1yvalues1.reshape(params.T1yvalues1.shape[0], 1)
            self.datatxt[:, 2] = params.T1regyvalues1.reshape(params.T1regyvalues1.shape[0], 1)
            np.savetxt('Tdata/' + params.dataTimestamp + '_T1_Data.txt', self.datatxt)
            print('T1 data saved!')
        elif params.GUImode == 3:
            self.datatxt = np.matrix(np.zeros((params.T2xvalues.shape[0], 3)))
            self.datatxt[:, 0] = params.T2xvalues.reshape(params.T2xvalues.shape[0], 1)
            self.datatxt[:, 1] = params.T2yvalues.reshape(params.T2yvalues.shape[0], 1)
            self.datatxt[:, 2] = params.T2regyvalues.reshape(params.T2regyvalues.shape[0], 1)
            np.savetxt('Tdata/' + params.dataTimestamp + '_T2_Data.txt', self.datatxt)
            print('T2 data saved!')

    def save_mag_image_data(self):
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 1:
            if params.sequence == 32 or params.sequence == 33 or params.sequence == 34:
                self.datatxt = np.matrix(np.zeros((params.img_mag.shape[1], params.img_mag.shape[0] * params.img_mag.shape[2])))
                for m in range(params.img_mag.shape[0]):
                    self.datatxt[:, m * params.img_mag.shape[2]:m * params.img_mag.shape[2] + params.img_mag.shape[2]] = params.img_mag[m, :, :]
                np.savetxt('imagedata/' + params.dataTimestamp + '_3D_' + str(params.img_mag.shape[0]) + '_Magnitude_Image_Data.txt', self.datatxt)
                print('Magnitude 3D image data saved!')
            elif params.sequence == 13 or params.sequence == 29:
                print('WIP!')
            elif params.sequence == 35:
                os.makedirs(os.path.join('imagedata', params.dataTimestamp + '_Magnitude_Image_3D_Data'))
                for n in range(params.img_mag.shape[0]):
                    np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_3D_Data' + '/' + params.dataTimestamp + '_Magnitude_Image_Data_' + str(n) + '.txt', params.img_mag[n, :, :])
                print('Magnitude image data saved!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Data.txt', params.img_mag)
                print('Magnitude image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 10:
                print('WIP!')
                os.makedirs(os.path.join('imagedata', params.dataTimestamp + '_Magnitude_Image_Stitching_3D_Data'))
                for n in range(params.img_st_mag.shape[0]):
                    np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Stitching_3D_Data' + '/' + params.dataTimestamp + '_Magnitude_Image_Stitching_Data_' + str(n) + '.txt', params.img_st_mag[n, :, :])
                print('Magnitude image data saved!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Stitching_Data.txt', params.img_st_mag)
                print('Magnitude image data saved!')

    def save_pha_image_data(self):
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 1:
            if params.sequence == 32 or params.sequence == 33 or params.sequence == 34:
                self.datatxt = np.matrix(np.zeros((params.img_pha.shape[1], params.img_pha.shape[0] * params.img_pha.shape[2])))
                for m in range(params.img_pha.shape[0]):
                    self.datatxt[:, m * params.img_pha.shape[2]:m * params.img_pha.shape[2] + params.img_pha.shape[2]] = params.img_pha[m, :, :]
                np.savetxt('imagedata/' + params.dataTimestamp + '_3D_' + str(params.img_pha.shape[0]) + '_Phase_Image_Data.txt', self.datatxt)
                print('Magnitude 3D image data saved!')
            elif params.sequence == 13 or params.sequence == 29:
                print('WIP!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Phase_Image_Data.txt', params.img_pha)
                print('Phase image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 4:
                print('WIP!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Phase_Image_Stitching_Data.txt', params.img_st_pha)
                print('Magnitude image data saved!')

    def save_image_data(self):
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 1:
            if params.sequence == 32 or params.sequence == 33 or params.sequence == 34:
                self.datatxt = np.matrix(np.zeros((params.img.shape[1], params.img.shape[0] * params.img.shape[2]), dtype=np.complex64))
                for m in range(params.img.shape[0]):
                    self.datatxt[:, m * params.img.shape[2]:m * params.img.shape[2] + params.img.shape[2]] = params.img[m, :, :]
                np.savetxt('imagedata/' + params.dataTimestamp + '_3D_' + str(params.img.shape[0]) + '_Image_Data.txt', self.datatxt)
                print('Magnitude 3D image data saved!')
            elif params.sequence == 13 or params.sequence == 29:
                print('WIP!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Image_Data.txt', params.img)
                print('Image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 4:
                print('WIP!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Image_Stitching_Data.txt', params.img_st)
                print('Magnitude image data saved!')
    
    def view_3D_layers(self):
        if self.dialog_3D_layers == None:
            self.dialog_3D_layers = View3DLayersDialog(parent = self)
            self.dialog_3D_layers.show()
        else:
            self.dialog_3D_layers.hide()
            self.dialog_3D_layers.show()
    
    def animate(self):
        with open(params.datapath + '_Header.json', 'r') as j:
            jsonparams = json.loads(j.read())
            
        self.GUImodetemp = 0
        self.GUImodetemp = params.GUImode
        params.GUImode = jsonparams['GUI mode']
        self.sequencetemp = 0
        self.sequencetemp = params.sequence
        params.sequence = jsonparams['Sequence']
        
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
        
        params.GUImode = self.GUImodetemp
        params.sequence = self.sequencetemp
        
        
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
        self.time = datetime.now().strftime('%d-%m-%Y')
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
            params.GUImode = 0
            params.sequence = 20
            params.saveFileParameter()
                    
            self.data_array.clear()
            
            self.write_message('raw')
            seq.sequence_upload()  
            
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
            self.time = datetime.now().strftime('%H-%M-%S')
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
        self.time = datetime.now().strftime('%d-%m-%Y')
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
        self.time = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
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
                        self.time = datetime.now().strftime('%H-%M-%S')
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
                #if data == 'err:stop' :
                    #self.write_message('stop')
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
        label.setStyleSheet('color: white; font-size: 24px;')
        
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
            self.Motor_MoveBy_doubleSpinBox.setValue(
                self.Motor_MoveTo_doubleSpinBox.value() - float(self.Motor_Position_lineEdit.text()))
        elif box == 'by':
            self.Motor_MoveTo_doubleSpinBox.setValue(
                self.Motor_MoveBy_doubleSpinBox.value() + float(self.Motor_Position_lineEdit.text()))
        self.Motor_MoveBy_doubleSpinBox.blockSignals(False)
        self.Motor_MoveTo_doubleSpinBox.blockSignals(False)

        params.motor_goto_position = self.Motor_MoveTo_doubleSpinBox.value()
        
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
        
        params.motor_goto_position = 120
        proc.motor_move(motor=self.motor)
        
        params.motor_actual_position = params.motor_goto_position
        
        self.motor_messagebox_string = ('Loosen the test tube holder screw.')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(self.motor_messagebox_string)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        
        params.motor_goto_position = 0
        proc.motor_move(motor=self.motor)
        
        params.motor_actual_position = params.motor_goto_position
        
        self.motor_messagebox_string = ('Carefully tighten the test tube holder screw.')
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(self.motor_messagebox_string)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        
        self.Motor_Home_pushButton.setEnabled(True)
        self.Motor_Apply_pushButton.setEnabled(True)
        self.Motor_MoveToCenter_pushButton.setEnabled(True)

class ConnectionDialog(Conn_Dialog_Base, Conn_Dialog_Form):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ConnectionDialog, self).__init__(parent)
        self.setupUi(self)

        self.ui = loadUi('ui/connDialog.ui')
        self.setGeometry(10, 40, 500, 150)
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
            params.connectionmode = True
            params.saveFileParameter()
            self.status_label.setText('Connected')
            self.connected.emit()
            self.mainwindow.show()
            self.mainwindow.Acquire_pushButton.setEnabled(params.connectionmode)
            self.close()


        elif not connection:
            params.connectionmode = False
            params.saveFileParameter()
            self.status_label.setText('Not connected')
            self.conn_btn.setText('Retry')
            self.help.setPixmap(self.conn_help)
            self.help.setVisible(True)
            self.setGeometry(10, 40, 500, 350)

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
        self.close()
        
class View3DLayersDialog(View3D_Dialog_Form, View3D_Dialog_Base):
    def __init__(self, parent=None):
        super(View3DLayersDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.ui = loadUi('ui/view_3D.ui')
        self.setWindowTitle('3D Layers Plot')
        self.setGeometry(420, 40, 1160, 950)
        
        with open(params.datapath + '/Image_Stitching_Header.json', 'r') as j:
            jsonparams = json.loads(j.read())

        self.imageorientation = jsonparams['Image orientation']
        self.nPE = int(jsonparams['Image resolution [pixel]'])
        self.FOV = jsonparams['FOV [mm]']
        
        self.SPEsteps = int(jsonparams['3D phase steps'])
        if params.GUImode == 5 and params.sequence != 10:
            self.SPEsteps = 1
            
        self.slicethickness = jsonparams['Slice/Slab thickness [mm]']

        self.motor_movement_step = jsonparams['Motor movement step [mm]']
        
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
        
        if params.GUImode == 1:
            self.image = params.img_mag
            self.phase = params.img_pha
            
            self.imagelength = self.slicethickness
            
        elif params.GUImode == 5 and params.sequence != 10:
            self.mode2D = True
            self.motor_image_count = int(jsonparams['Motor image count'])
            
            datapathtemp = params.datapath
            
            if self.slicethickness >= self.motor_movement_step:
                self.image = np.array(np.zeros((self.motor_image_count, self.nPE, self.nPE)))
                self.phase = np.array(np.zeros((self.motor_image_count, self.nPE, self.nPE)))
                
                for n in range(0, self.motor_image_count):
                    self.image[n, :, :] = params.img_st_mag[:, n * self.nPE:int(n * self.nPE + self.nPE)]
                    self.phase[n, :, :] = params.img_st_pha[:, n * self.nPE:int(n * self.nPE + self.nPE)]
                    
                self.imagelength = jsonparams['Motor total image length [mm]'] + self.motor_movement_step
            else:
                    self.factor2D = 4
                    precision = 0.01
                    self.image = np.array(np.zeros((self.motor_image_count*self.factor2D - 2, self.nPE, self.nPE)))
                    self.phase = np.array(np.zeros((self.motor_image_count*self.factor2D - 2, self.nPE, self.nPE)))
                    self.movement_positions = np.array(np.zeros(self.motor_image_count*self.factor2D - 2))
                    self.image_positions = np.linspace(0, self.nPE, self.nPE)
                    
                    for n in range(0, self.motor_image_count):
                            self.image[n*self.factor2D, :, :] = params.img_st_mag[:, int(n * self.nPE):int(n * self.nPE + self.nPE)]
                            self.phase[n*self.factor2D, :, :] = params.img_st_pha[:, int(n * self.nPE):int(n * self.nPE + self.nPE)]
                            self.movement_positions[n*self.factor2D] = n * self.motor_movement_step + precision
                            
                            self.image[n*self.factor2D+1, :, :] = params.img_st_mag[:, int(n * self.nPE):int(n * self.nPE + self.nPE)]
                            self.phase[n*self.factor2D+1, :, :] = params.img_st_pha[:, int(n * self.nPE):int(n * self.nPE + self.nPE)]
                            self.movement_positions[n*self.factor2D+1] = n * self.motor_movement_step + self.slicethickness - precision
                            
                            if n != self.motor_image_count - 1:
                                self.movement_positions[n*self.factor2D+2] = n * self.motor_movement_step + self.slicethickness + precision
                                self.movement_positions[n*self.factor2D+3] = (n+1) * self.motor_movement_step - precision                   
                            
                    self.imagelength = np.max(self.movement_positions) + precision
            
            self.mirrored = False
        else:
            self.image = np.flip(params.img_st_mag, axis=0)
            self.phase = np.flip(params.img_st_pha, axis=0)
            
            self.motor_movement_step = np.abs(jsonparams['Motor movement step [mm]'])
            if self.motor_movement_step <= self.FOV:
                self.imagelength = jsonparams['Motor total image length [mm]'] + self.motor_movement_step
            else:
                self.imagelength = jsonparams['Motor total image length [mm]'] + self.FOV
                
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
            self.view3D_ZX_slider.setMaximum(int(self.slice_count_ZX / 2))
        else:
            self.view3D_ZX_slider.setMaximum(self.slice_count_ZX)
        self.view3D_ZX_slider.setSingleStep(1)
        self.view3D_ZX_slider.setPageStep(1)
        self.view3D_ZX_slider.setSliderPosition(int(round(self.view3D_ZX_slider.maximum()/2)))
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
        self.update_image(int(round(self.view3D_ZX_slider.maximum()/2)), int(round(self.view3D_XY_slider.maximum()/2)),int(round(self.view3D_YZ_slider.maximum()/2)), reset=True)
        
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
            self.view3D_ZX_Slice_lineEdit.setText(str(self.current_slice_ZX) + ' / ' + str(self.slice_count_ZX))
            
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
    print('________________________________________________________')
    print('Relax 2.0')
    print('Programmed by Marcus Prier, Magdeburg, 2024')
    print('________________________________________________________\n')

    app = QApplication(sys.argv)
    gui = MainWindow()

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
