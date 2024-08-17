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

#beginSAR
import serial
import serial.tools.list_ports
import asyncio
import zlib
import struct
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QSize
#endSAR


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
        params.SAR_status = 1
        params.motor_available = 0
        params.motor_actual_position = 0
        params.motor_goto_position = 0

        # self.motor_connect()

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
        self.motor = None
        if not (params.motor_port != [] and self.check_motor_port(motor_port=params.motor_port)):
            ports = QSerialPortInfo.availablePorts()
            port_available = False

            while len(ports) > 0 and not port_available:
                if self.check_motor_port(ports[0].portName()):
                    port_available = True
                    params.motor_available = 1
                    params.motor_port = ports[0].portName()
                else:
                    ports.remove(ports[0])

        self.Motor_Tools_pushButton.setEnabled(True)

    def check_motor_port(self, motor_port=None):
        motor = QSerialPort()
        motor.setPortName(motor_port)
        print('Motor Search: checking port: ' + motor_port)

        if motor.open(QIODevice.ReadWrite):
            motor.setBaudRate(QSerialPort.BaudRate.Baud115200)
            motor.setDataBits(QSerialPort.DataBits.Data8)
            motor.setParity(QSerialPort.Parity.NoParity)
            motor.setStopBits(QSerialPort.StopBits.OneStop)
            motor.setFlowControl(QSerialPort.FlowControl.NoFlowControl)
            motor.setDataTerminalReady(True)

            motor.waitForReadyRead(100)

            time.sleep(2)

            cmd_info_s = 'M115\n'
            motor.write(cmd_info_s.encode('utf-8'))
            motor.waitForBytesWritten()

            motor_search_start_time = time.perf_counter()
            motor_search_timeout = False
            motor_timeout_time = 0.5

            ident_byte_array = motor.readAll()
            while '\n' not in ident_byte_array.data().decode() and not motor_search_timeout:
                motor.waitForReadyRead(10)
                ident_byte_array.append(motor.readAll())
                if time.perf_counter() > (motor_search_start_time + motor_timeout_time):
                    motor_search_timeout = True
                    print('Motor Search: Timeout, no connection to ' + motor_port + ' possible.')

            if not motor_search_timeout and 'MRI-Patient-Motor-Control' in ident_byte_array.data().decode('utf8', errors='ignore'):
                params.motor_port = motor_port
                motor.clear()
                print('Motor Search: Successful at port: ' + motor_port)

                time.sleep(0.1)

                cmd_axis_length_s = 'M203 ' + str(params.motor_axis_limit_negative) + ' ' + str(
                    params.motor_axis_limit_positive) + '\n'
                motor.write(cmd_axis_length_s.encode('utf-8'))
                motor.waitForBytesWritten()

                time.sleep(0.1)

                cmd_response_s = 'M118 R0: limit set finished\n'
                motor.write(cmd_response_s.encode('utf-8'))
                motor.waitForBytesWritten()
                motor.flush()

                response_byte_array = motor.readAll()
                while 'R0: limit set finished' not in response_byte_array.data().decode('utf8', errors='ignore'):
                    motor.waitForReadyRead(10)
                    response_byte_array.append(motor.readAll())
                motor.clear()

                self.motor = motor
                self.motor.errorOccurred.connect(lambda error_code: self.motor_error(error_code))
                self.motor.readyRead.connect(self.motor_read)

                time.sleep(0.1)

                cmd_home_s = 'G28\n'
                motor.write(cmd_home_s.encode('utf-8'))
                motor.waitForBytesWritten()

                time.sleep(0.1)

                cmd_response_s = 'M118 R0: homing finished\n'
                motor.write(cmd_response_s.encode('utf-8'))
                motor.flush()

                print('Motor Control: Homing Message send to device')

                params.motor_available = False

                return True
            else:
                motor.close()
                return False
        else:
            print('Motor Search: Port ' + motor_port + ' unavailable or already in use.')
            return False

    def motor_read(self):
        if self.motor.canReadLine():
            msg = bytes(self.motor.readLine()).decode('utf-8', errors='ignore')
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
        self.motor.blockSignals(True)

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

            print(
                'Motor Control: Error detected, Control will be unavailable until at least the next restart of relax2, Error Number: ' + str(
                    error) + ', Message: ' + error_message)
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
                                            , 'RF Loopback Test Sequence', 'Gradient Test Sequence', 'RF SAR Calibration Test Sequence'])
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
                                            , 'WIP 2D Echo Planar Imaging (Slice, GRE, 4 Echos)', 'WIP 2D Echo Planar Imaging (Slice, SE, 4 Echos)', 'WIP 2D Diffusion (Slice, SE)' \
                                            , 'WIP 2D Flow Compensation (Slice, GRE)', 'WIP 2D Flow Compensation (Slice, SE)', 'WIP 3D FFT Spin Echo' \
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
            if params.motor_available:
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
            else:
                print('Motor Control: Motor not available, maybe it is still homing?')
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
                    print('Autorecenter to:', params.frequency)
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_params != None:
                        self.dialog_params.load_params()
                        self.dialog_params.repaint()
                    time.sleep(params.TR / 1000)
                    
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
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_params != None:
                        self.dialog_params.load_params()
                        self.dialog_params.repaint()
                    time.sleep(params.TR / 1000)
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
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_params != None:
                        self.dialog_params.load_params()
                        self.dialog_params.repaint()
                    time.sleep(params.TR / 1000)
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
                    params.frequencyoffset = self.frequencyoffsettemp
                    if self.dialog_params != None:
                        self.dialog_params.load_params()
                        self.dialog_params.repaint()
                    time.sleep(params.TR / 1000)
                    seq.sequence_upload()
            else:
                seq.sequence_upload()
        else:
            seq.sequence_upload()
        if params.headerfileformat == 0:
            params.save_header_file_txt()
        else:
            params.save_header_file_json()

        if self.dialog_params != None:
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
                    # proc.image_3D_analytics()
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
            if os.path.isfile(params.datapath + '_1.txt') == True:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    proc.image_stitching_2D_json_process()
                elif os.path.isfile(params.datapath + '_Header.txt') == True:
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
        elif params.GUImode == 5 and params.sequence == 10:
            if os.path.isfile(params.datapath + '_1.txt') == True:
                if os.path.isfile(params.datapath + '_Header.json') == True:
                    proc.image_stitching_3D_json_process()
                elif os.path.isfile(params.datapath + '_Header.txt') == True:
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
            self.dialog_prot = ProtocolWindow(self)
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
        self.setGeometry(420, 40, 1150, 770)

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

        self.Motor_Start_Position_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        self.Motor_Start_Position_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)
        self.Motor_End_Position_doubleSpinBox.setMinimum(params.motor_axis_limit_negative)
        self.Motor_End_Position_doubleSpinBox.setMaximum(params.motor_axis_limit_positive)

    def update_motor_start_position(self):
        params.motor_start_position = self.Motor_Start_Position_doubleSpinBox.value()

        self.Motor_Total_Image_Length_doubleSpinBox.setMaximum(
            params.motor_axis_limit_positive - params.motor_start_position)
        self.Motor_Total_Image_Length_doubleSpinBox.setMinimum(
            params.motor_axis_limit_negative - params.motor_start_position)

        params.motor_total_image_length = round(params.motor_end_position - params.motor_start_position, 1)
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        params.motor_movement_step = params.motor_total_image_length / (params.motor_image_count - 1)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)

        params.saveFileParameter()

    def update_motor_end_Position(self):
        params.motor_end_position = self.Motor_End_Position_doubleSpinBox.value()

        params.motor_total_image_length = round(params.motor_end_position - params.motor_start_position, 1)
        self.Motor_Total_Image_Length_doubleSpinBox.setValue(params.motor_total_image_length)
        params.motor_movement_step = params.motor_total_image_length / (params.motor_image_count - 1)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)
        params.motor_start_position = params.motor_end_position - params.motor_total_image_length
        self.Motor_Start_Position_doubleSpinBox.setValue(params.motor_start_position)

        params.saveFileParameter()

    def update_motor_total_image_length(self):
        params.motor_total_image_length = self.Motor_Total_Image_Length_doubleSpinBox.value()
        params.motor_end_position = params.motor_start_position + params.motor_total_image_length
        self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)
        params.motor_movement_step = params.motor_total_image_length / (params.motor_image_count - 1)
        self.Motor_Movement_Step_doubleSpinBox.setValue(params.motor_movement_step)

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

            params.saveFileParameter()

    def motor_end_here(self):
        if params.motor_actual_position != params.motor_start_position:
            params.motor_end_position = params.motor_actual_position
            self.Motor_End_Position_doubleSpinBox.setValue(params.motor_end_position)

            params.saveFileParameter()

    def load_params(self):
        self.TE_doubleSpinBox.setValue(params.TE)
        self.TI_doubleSpinBox.setValue(params.TI)
        self.TR_spinBox.setValue(params.TR)

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
            self.Frequency_Offset_spinBox.setValue(-1 * params.frequencyoffset)

        self.Phase_Offset_spinBox.setValue(params.phaseoffset)
        self.Radial_Angle_Step_spinBox.setValue(params.radialanglestep)
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

            self.Gz3D = (2 * np.pi / params.slicethickness) / (2 * np.pi * 42.57 * (self.GPEtime / 1000000))
            params.GSPEstep = int(self.Gz3D / self.Gzsens * 1000)
            print('Auto 3D SlPE max:', params.GSPEstep * params.SPEsteps / 2)

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
            self.Gxsens = params.gradsens[0]
            self.Gysens = params.gradsens[2]
            self.Gzsens = params.gradsens[1]
        elif params.imageorientation == 5:
            self.Gxsens = params.gradsens[2]
            self.Gysens = params.gradsens[1]
            self.Gzsens = params.gradsens[0]
      

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
        print('Auto 3D SlPE max:', params.GSPEstep * params.SPEsteps / 2)

        self.update_gradients()
        print('Auto GPE max: ', params.GPEstep * params.nPE / 2)
        
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

        if self.Average_radioButton.isChecked():
            params.average = 1
        else:
            params.average = 0
        params.averagecount = self.Average_spinBox.value()

        params.imageorientation = self.Image_Orientation_comboBox.currentIndex()

        params.FOV = self.FOV_doubleSpinBox.value()
        params.slicethickness = self.Slice_Thickness_doubleSpinBox.value()
        params.SPEsteps = self.SPEsteps_spinBox.value()

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
                self.Gxsens = params.gradsens[0]
                self.Gysens = params.gradsens[2]
                self.Gzsens = params.gradsens[1]
            elif params.imageorientation == 5:
                self.Gxsens = params.gradsens[2]
                self.Gysens = params.gradsens[1]
                self.Gzsens = params.gradsens[0]            

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
            print('Auto 3D SlPE max:', params.GSPEstep * params.SPEsteps / 2)

            self.update_gradients()
            print('Auto GPE max: ', params.GPEstep * params.nPE / 2)

        else:
            self.Gz = 0

        params.Gdiffamplitude = self.GDiffamplitude_spinBox.value()

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
            print('Manual GPE max: ', params.GPEstep * params.nPE / 2)

            params.saveFileParameter()

        elif params.autograd == 1:
            self.GROamplitude_spinBox.setValue(params.GROamplitude)
            self.GPEstep_spinBox.setValue(params.GPEstep)
            self.Crusher_Amplitude_spinBox.setValue(params.crusheramplitude)
            self.Spoiler_Amplitude_spinBox.setValue(params.spoileramplitude)
            self.GSamplitude_spinBox.setValue(params.GSamplitude)
            self.GSPEstep_spinBox.setValue(params.GSPEstep)


class ConfigWindow(Config_Window_Form, Config_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ConfigWindow, self).__init__(parent)
        self.setupUi(self)

        self.load_params()

        self.ui = loadUi('ui/config.ui')
        self.setWindowTitle('Config')
        self.setGeometry(420, 40, 790, 800)

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

        if params.cutcirc == 1: self.kspace_cut_circ_radioButton.setChecked(True)
        if params.cutrec == 1: self.kspace_cut_rec_radioButton.setChecked(True)

        if params.cutcenter == 1: self.kSpace_Cut_Center_radioButton.setChecked(True)
        if params.cutoutside == 1: self.kSpace_Cut_Outside_radioButton.setChecked(True)
        self.kSpace_Cut_Center_spinBox.setValue(params.cutcentervalue)
        self.kSpace_Cut_Outside_spinBox.setValue(params.cutoutsidevalue)

        if params.ustime == 1: self.Undersampling_Time_radioButton.setChecked(True)
        if params.usphase == 1: self.Undersampling_Phase_radioButton.setChecked(True)

        self.GRO_Length_Scaler_doubleSpinBox.setValue(params.GROpretimescaler)

        if params.lnkspacemag == 1: self.ln_kSpace_Magnitude_radioButton.setChecked(True)

        if params.rx1 == 1: self.RX1_radioButton.setChecked(True)
        if params.rx2 == 1: self.RX2_radioButton.setChecked(True)

        self.SignalMask_doubleSpinBox.setValue(params.signalmask)

        if params.GUItheme == 0: self.GUI_Light_radioButton.setChecked(True)
        if params.GUItheme == 1: self.GUI_Dark_radioButton.setChecked(True)
        
        if params.autodataprocess == 1: self.Auto_Data_Process_radioButton.setChecked(True)
        if params.single_plot == 1: self.Single_Plot_radioButton.setChecked(True)
        
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

        if self.Undersampling_Time_comboBox.currentIndex() == 0: params.ustimeidx = 2
        elif self.Undersampling_Time_comboBox.currentIndex() == 1: params.ustimeidx = 5
        elif self.Undersampling_Time_comboBox.currentIndex() == 2: params.ustimeidx = 10
        elif self.Undersampling_Time_comboBox.currentIndex() == 3: params.ustimeidx = 50
        else: params.ustimeidx = 2

        if self.Undersampling_Phase_comboBox.currentIndex() == 0: params.usphaseidx = 2
        elif self.Undersampling_Phase_comboBox.currentIndex() == 1: params.usphaseidx = 4
        elif self.Undersampling_Phase_comboBox.currentIndex() == 2: params.usphaseidx = 8
        else: params.usphaseidx = 2

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

        params.saveFileParameter()

    def update_dark(self):
        if self.GUI_Dark_radioButton.isChecked():
            params.GUItheme = 1
            self.GUI_Light_radioButton.setChecked(False)

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
        if os.path.isfile('imagedata/Shim_Tool_Data.txt') == True:
            if params.ToolShimChannel[0] == 1:
                if np.max(params.STvalues[1, :]) != 0:
                    self.Shim_X_spinBox.setValue(int(params.STvalues[0, np.argmax(params.STvalues[1, :])]))
                    print('Tool reference X shim applied')
                else: print('No reference X shim value')
            if params.ToolShimChannel[1] == 1:
                if np.max(params.STvalues[2, :]) != 0:
                    self.Shim_Y_spinBox.setValue(int(params.STvalues[0, np.argmax(params.STvalues[2, :])]))
                    print('Tool reference Y shim applied')
                else: print('No reference Y shim value')
            if params.ToolShimChannel[2] == 1:
                if np.max(params.STvalues[3, :]) != 0:
                    self.Shim_Z_spinBox.setValue(int(params.STvalues[0, np.argmax(params.STvalues[3, :])]))
                    print('Tool reference Z shim applied')
                else: print('No reference Z shim value')
            if params.ToolShimChannel[3] == 1:
                if np.max(params.STvalues[4, :]) != 0:
                    self.Shim_Z2_spinBox.setValue(int(params.STvalues[0, np.argmax(params.STvalues[4, :])]))
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
        self.setGeometry(420, 40, 800, 850)

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

        if self.Tool_Shim_X_radioButton.isChecked():
            params.ToolShimChannel[0] = 1
        else:
            params.ToolShimChannel[0] = 0
        if self.Tool_Shim_Y_radioButton.isChecked():
            params.ToolShimChannel[1] = 1
        else:
            params.ToolShimChannel[1] = 0
        if self.Tool_Shim_Z_radioButton.isChecked():
            params.ToolShimChannel[2] = 1
        else:
            params.ToolShimChannel[2] = 0
        if self.Tool_Shim_Z2_radioButton.isChecked():
            params.ToolShimChannel[3] = 1
        else:
            params.ToolShimChannel[3] = 0

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
        print(params.ernstanglecalc_TR)
        print(params.ernstanglecalc_T1)
        
        params.ernstanglecalc_EA = math.degrees(np.arccos(math.exp(-(params.ernstanglecalc_TR/params.ernstanglecalc_T1))))
        print(params.ernstanglecalc_EA)
        params.ernstanglecalc_EA = round(math.degrees(np.arccos(math.exp(-(params.ernstanglecalc_TR/params.ernstanglecalc_T1)))))
        print(params.ernstanglecalc_EA)
        self.ErnstAngleCalculator_ErnstAngle_lineEdit.setText(str(params.ernstanglecalc_EA))
        
        params.saveFileParameter()

    def Autocentertool(self):
        self.Autocenter_pushButton.setEnabled(False)
        self.repaint()

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
        self.minor_ticks = np.linspace(params.ACstart, params.ACstop, round(
            abs((params.ACstop * 1.0e6 - params.ACstart * 1.0e6)) / (params.ACstepwidth)) + 1)
        self.ax.set_xticks(self.major_ticks)
        self.ax.set_xticks(self.minor_ticks, minor=True)
        self.ax.grid(which='major', color='#888888', linestyle='-')
        self.ax.grid(which='minor', color='#888888', linestyle=':')
        self.ax.grid(which='both', visible=True)
        self.ax.set_xlim((params.ACstart, params.ACstop))
        self.ax.set_ylim((0, 1.1 * np.max(np.transpose(params.ACvalues[1, :]))))
        self.fig_canvas.draw()
        self.fig_canvas.setWindowTitle('Tool Plot')
        self.fig_canvas.setGeometry(420, 40, 800, 750)
        self.fig_canvas.show()
        self.AC_Reffrequency_lineEdit.setText(str(params.Reffrequency))

        params.flippulselength = self.flippulselengthtemp

        self.Autocenter_pushButton.setEnabled(True)
        self.repaint()

    def Flipangletool(self):
        self.Flipangle_pushButton.setEnabled(False)
        self.repaint()

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
        self.fig_canvas.setGeometry(420, 40, 800, 750)
        self.fig_canvas.show()
        self.FA_RefRFattenuation_lineEdit.setText(str(params.RefRFattenuation))

        params.flippulselength = self.flippulselengthtemp

        self.Flipangle_pushButton.setEnabled(True)
        self.repaint()

    def Shimtool(self):
        self.Tool_Shim_pushButton.setEnabled(False)
        self.repaint()

        if params.ToolShimChannel != [0, 0, 0, 0]:

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
            if params.ToolShimStart <= params.ToolShimStop:
                self.major_ticks = np.linspace(math.floor(params.ToolShimStart / 10) * 10, math.ceil(params.ToolShimStop / 10) * 10, (math.ceil(params.ToolShimStop / 10) - math.floor(params.ToolShimStart / 10)) + 1)
            else:
                self.major_ticks = np.linspace(math.floor(params.ToolShimStop / 10) * 10, math.ceil(params.ToolShimStart / 10) * 10, (math.ceil(params.ToolShimStart / 10) - math.floor(params.ToolShimStop / 10)) + 1)

            self.ax.set_xticks(self.major_ticks)
            self.ax.grid(which='major', color='#888888', linestyle='-')
            self.ax.grid(which='major', visible=True)

            self.ax.set_xlim((math.floor(params.ToolShimStart / 10) * 10, math.ceil(params.ToolShimStop / 10) * 10))
            self.ax.set_ylim((0, 1.1 * np.max(np.transpose(params.STvalues[1:, :]))))
            self.fig_canvas.draw()
            self.fig_canvas.setWindowTitle('Tool Plot')
            self.fig_canvas.setGeometry(420, 40, 800, 750)
            self.fig_canvas.show()

            if params.ToolShimChannel[0] == 1:
                self.Tool_Shim_X_Ref_lineEdit.setText(str(params.STvalues[0, np.argmax(params.STvalues[1, :])]))
            else:
                self.Tool_Shim_X_Ref_lineEdit.setText(' ')
            if params.ToolShimChannel[1] == 1:
                self.Tool_Shim_Y_Ref_lineEdit.setText(str(params.STvalues[0, np.argmax(params.STvalues[2, :])]))
            else:
                self.Tool_Shim_Y_Ref_lineEdit.setText(' ')
            if params.ToolShimChannel[2] == 1:
                self.Tool_Shim_Z_Ref_lineEdit.setText(str(params.STvalues[0, np.argmax(params.STvalues[3, :])]))
            else:
                self.Tool_Shim_Z_Ref_lineEdit.setText(' ')
            if params.ToolShimChannel[3] == 1:
                self.Tool_Shim_Z2_Ref_lineEdit.setText(str(params.STvalues[0, np.argmax(params.STvalues[4, :])]))
            else:
                self.Tool_Shim_Z2_Ref_lineEdit.setText(' ')

        else:
            print('Please select gradient channel')

        self.Tool_Shim_pushButton.setEnabled(True)
        self.repaint()

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
        self.IPha_canvas.setGeometry(420, 40, 400, 355)
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
        self.FMB0_canvas.setGeometry(830, 40, 400, 355)
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
        self.IPha_canvas.setGeometry(420, 40, 400, 355)
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
        self.FMB0_canvas.setGeometry(830, 40, 400, 355)
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
        self.IMag_canvas.setGeometry(420, 40, 400, 355)
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
        self.FMB1_canvas.setGeometry(830, 40, 400, 355)
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
        self.IMag_canvas.setGeometry(420, 40, 400, 355)
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
        self.FMB1_canvas.setGeometry(830, 40, 400, 355)
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
        self.IMag_canvas.setGeometry(420, 40, 800, 750)
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
        self.IMag_canvas.setGeometry(420, 40, 800, 750)
        self.IMag_canvas.show()

        self.Field_Map_Gradient_Slice_pushButton.setEnabled(True)
        self.repaint()


class ProtocolWindow(Protocol_Window_Form, Protocol_Window_Base):
    connected = pyqtSignal()

    def __init__(self, parent=None):
        super(ProtocolWindow, self).__init__(parent)
        self.setupUi(self)

        # self.load_params()
        self.prot_datapath = 'protocol/Protocol_01'

        self.ui = loadUi('ui/protocol.ui')
        self.setWindowTitle('Protocol')
        self.setGeometry(420, 40, 800, 850)

        self.Protocol_Execute_Protocol_pushButton.setEnabled(params.connectionmode)

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
        # print('Protocol datapath:', self.prot_datapath)

    def protocol_add(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0], :] = self.protocol[:, :]
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 0] = params.GUImode
        self.protocoltemp[self.protocoltemp.shape[0] - 2, 1] = params.sequence
        self.protocol = self.protocoltemp

        try:
            shutil.copyfile('parameters.pkl',
                            self.prot_datapath + '_' + str(self.protocol.shape[0] - 1) + '_parameters.pkl')
            time.sleep(0.001)
        except:
            print('No parameter file.')

        self.protocol_plot_table()

    def protocol_delete_last(self):
        self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] - 1, self.protocol.shape[1])))
        self.protocoltemp[0:self.protocol.shape[0] - 1, :] = self.protocol[0:self.protocol.shape[0] - 1, :]
        self.protocol = self.protocoltemp

        try:
            os.remove(self.prot_datapath + '_' + str(self.protocol.shape[0]) + '_parameters.pkl')
            time.sleep(0.001)
        except:
            print('No parameter file.')

        self.protocol_plot_table()

    def protocol_insert(self):
        if self.Protocol_Number_spinBox.value() - 1 <= self.protocoltemp.shape[0] - 1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0] + 1, self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value() - 1, :] = self.protocol[0:self.Protocol_Number_spinBox.value() - 1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 0] = params.GUImode
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1, 1] = params.sequence
            self.protocoltemp[self.Protocol_Number_spinBox.value():self.protocoltemp.shape[0] - 1, :] = self.protocol[self.Protocol_Number_spinBox.value() - 1:self.protocol.shape[0] - 1, :]
            self.protocol = self.protocoltemp

            for n in range(self.Protocol_Number_spinBox.value(), self.protocol.shape[0] - 1):
                try:
                    shutil.copyfile(self.prot_datapath + '_' + str(n) + '_parameters.pkl',
                                    self.prot_datapath + '_' + str(n) + '_parameters_temp.pkl')
                    time.sleep(0.001)
                except:
                    print('No parameter file.')
            shutil.copyfile('parameters.pkl', self.prot_datapath + '_' + str(self.Protocol_Number_spinBox.value()) + '_parameters.pkl')
            time.sleep(0.001)
            for n in range(self.Protocol_Number_spinBox.value() + 1, self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '_' + str(n - 1) + '_parameters_temp.pkl', self.prot_datapath + '_' + str(n) + '_parameters.pkl')
                    time.sleep(0.001)
                    os.remove(self.prot_datapath + '_' + str(n - 1) + '_parameters_temp.pkl')
                    time.sleep(0.001)
                except:
                    print('No parameter file.')

        else:
            print('Index to high!')

        self.protocol_plot_table()

    def protocol_delete(self):
        if self.Protocol_Number_spinBox.value() <= self.protocoltemp.shape[0] - 1:
            self.protocoltemp = np.matrix(np.zeros((self.protocol.shape[0], self.protocol.shape[1])))
            self.protocoltemp[0:self.Protocol_Number_spinBox.value() - 1, :] = self.protocol[0:self.Protocol_Number_spinBox.value() - 1,:]
            self.protocoltemp[self.Protocol_Number_spinBox.value() - 1:self.protocoltemp.shape[0] - 2,
            :] = self.protocol[self.Protocol_Number_spinBox.value():self.protocol.shape[0] - 1, :]
            self.protocol = np.matrix(np.zeros((self.protocoltemp.shape[0] - 1, self.protocoltemp.shape[1])))
            self.protocol = self.protocoltemp[0:self.protocoltemp.shape[0] - 1, :]

            for n in range(self.Protocol_Number_spinBox.value(), self.protocol.shape[0]):
                try:
                    shutil.copyfile(self.prot_datapath + '_' + str(n + 1) + '_parameters.pkl', self.prot_datapath + '_' + str(n) + '_parameters.pkl')
                    time.sleep(0.001)
                except:
                    print('No parameter file.')
            try:
                os.remove(self.prot_datapath + '_' + str(self.protocol.shape[0]) + '_parameters.pkl')
                time.sleep(0.001)
            except:
                print('No parameter file.')

        else:
            print('Index to high!')

        self.protocol_plot_table()

    def protocol_overwrite(self):
        if self.Protocol_Number_spinBox.value() - 1 <= self.protocoltemp.shape[0] - 2:
            self.protocol[self.Protocol_Number_spinBox.value() - 1, 0] = params.GUImode
            self.protocol[self.Protocol_Number_spinBox.value() - 1, 1] = params.sequence

            try:
                shutil.copyfile('parameters.pkl', self.prot_datapath + '_' + str(self.Protocol_Number_spinBox.value()) + '_parameters.pkl')
                time.sleep(0.001)
            except:
                print('No parameter file.')

        else:
            print('Index to high!')

        self.protocol_plot_table()

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
                                            , 'RF Testsequence', 'Gradient Testsequence')
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
                                            , 'WIP 2D Echo Planar Imaging (Slice, GRE, 4 Echos)', 'WIP 2D Echo Planar Imaging (Slice, SE, 4 Echos)', 'WIP 2D Diffusion (Slice, SE)' \
                                            , 'WIP 2D Flow Compensation (Slice, GRE)', 'WIP 2D Flow Compensation (Slice, SE)', 'WIP 3D FFT Spin Echo' \
                                            , '3D FFT Spin Echo (Slab)', '3D FFT Turbo Spin Echo (Slab)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(
                    self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 2:
                self.Prot_Table_GUImode = 'T1 Measurement'
                self.Prot_Table_sequence = ('Inversion Recovery (FID)', 'Inversion Recovery (SE)', 'Inversion Recovery (Slice, FID)' \
                                            , 'Inversion Recovery (Slice, SE)', '2D Inversion Recovery (GRE)', '2D Inversion Recovery (SE)' \
                                            , '2D Inversion Recovery (Slice, GRE)', '2D Inversion Recovery (Slice, SE)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(
                    self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 3:
                self.Prot_Table_GUImode = 'T2 Measurement'
                self.Prot_Table_sequence = ('Spin Echo', 'Saturation Inversion Recovery (FID)', 'Spin Echo (Slice)' \
                                            , 'Saturation Inversion Recovery (Slice, FID)', '2D Spin Echo', '2D Saturation Inversion Recovery (GRE)' \
                                            , '2D Spin Echo (Slice)', '2D Saturation Inversion Recovery (Slice, GRE)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(
                    self.Prot_Table_sequence[int(self.protocol[n, 1])]))
            elif self.protocol[n, 0] == 4:
                self.Prot_Table_GUImode = 'Projections'
                self.Prot_Table_sequence = ('Gradient Echo (On Axis)', 'Spin Echo (On Axis)', 'Gradient Echo (On Angle)' \
                                            , 'Spin Echo (On Angle)', 'Gradient Echo (Slice, On Axis)', 'Spin Echo (Slice, On Axis)' \
                                            , 'Gradient Echo (Slice, On Angle)', 'Spin Echo (Slice, On Angle)')
                self.Protocol_Table_tableWidget.setItem(n, 0, QTableWidgetItem(self.Prot_Table_GUImode))
                self.Protocol_Table_tableWidget.setItem(n, 1, QTableWidgetItem(
                    self.Prot_Table_sequence[int(self.protocol[n, 1])]))

        self.Protocol_Table_tableWidget.resizeColumnToContents(0)
        self.Protocol_Table_tableWidget.resizeColumnToContents(1)

        self.Protocol_Table_tableWidget.show()

    def protocol_save_protocol(self):
        np.savetxt(self.prot_datapath + '.txt', self.protocol[0:self.protocol.shape[0] - 1, :])
        print('Protocol saved!')

    def protocol_new_protocol(self):
        self.protocol = np.matrix([0, 0])

        self.protocol_plot_table()

    def protocol_load_protocol(self):
        if os.path.isfile(self.prot_datapath + '.txt') == True:
            self.protocoltemp = np.genfromtxt(self.prot_datapath + '.txt')
            self.protocol = np.matrix(np.zeros((self.protocoltemp.shape[0] + 1, self.protocoltemp.shape[1])))
            self.protocol[0:self.protocoltemp.shape[0], :] = self.protocoltemp[:, :]
            print(self.protocol)
            print(self.protocol.shape)
            self.protocol_plot_table()
        else:
            print('No protocol file!!')

    def protocol_execute_protocol(self):
        print('WIP')

        self.Protocol_Execute_Protocol_pushButton.setEnabled(False)
        self.repaint()

        try:
            shutil.copyfile('parameters.pkl', self.prot_datapath + '_parameters_temp.pkl')
            time.sleep(0.001)
        except:
            print('No parameter file.')

        self.datapathtemp = ''
        self.datapathtemp = params.datapath

        for n in range(self.protocol.shape[0] - 1):
            print('Protocol task: ', n)
            try:
                shutil.copyfile(self.prot_datapath + '_' + str(n + 1) + '_parameters.pkl', 'parameters.pkl')
                time.sleep(0.001)
            except:
                print('No parameter file!!')

            params.loadParam()

            params.datapath = self.prot_datapath + '_' + str(n + 1) + '_rawdata'

            self.protocol_acquire()

            time.sleep(params.TR / 1000)

        params.datapath = self.datapathtemp

        try:
            shutil.copyfile(self.prot_datapath + '_parameters_temp.pkl', 'parameters.pkl')
            time.sleep(0.001)
        except:
            print('No parameter file.')

        params.loadParam()

        self.Protocol_Execute_Protocol_pushButton.setEnabled(True)
        self.repaint()

    def protocol_acquire(self):
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
                    print('Autorecenter to:', params.frequency)
                    time.sleep(params.TR / 1000)
                    params.frequencyoffset = self.frequencyoffsettemp
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
                    time.sleep(params.TR / 1000)
                    params.frequencyoffset = self.frequencyoffsettemp
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
                    time.sleep(params.TR / 1000)
                    params.frequencyoffset = self.frequencyoffsettemp
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
                    time.sleep(params.TR / 1000)
                    params.frequencyoffset = self.frequencyoffsettemp
                    seq.sequence_upload()
            else:
                seq.sequence_upload()
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

        if params.GUImode == 0:
            self.spectrum_plot_init()
        elif params.GUImode == 1:
            if params.sequence == 34 or params.sequence == 35 or params.sequence == 36:
                self.imaging_3D_plot_init()
            elif params.sequence == 14 or params.sequence == 31:
                self.imaging_diff_plot_init()
            else:
                params.imageminimum = np.min(params.img_mag)
                self.Image_Minimum_doubleSpinBox.setValue(params.imageminimum)
                params.imagemaximum = np.max(params.img_mag)
                self.Image_Maximum_doubleSpinBox.setValue(params.imagemaximum)
                self.imaging_plot_init()
                self.Animate_pushButton.setEnabled(True)

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
            elif params.sequence == 10:
                self.imaging_stitching_3D_plot_init()

        self.Frequncyaxisrange_spinBox.setKeyboardTracking(False)
        self.Frequncyaxisrange_spinBox.valueChanged.connect(self.update_params)

        self.Save_Mag_Image_Data_pushButton.clicked.connect(lambda: self.save_mag_image_data())
        self.Save_Pha_Image_Data_pushButton.clicked.connect(lambda: self.save_pha_image_data())
        self.Save_Image_Data_pushButton.clicked.connect(lambda: self.save_image_data())

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
            self.fig_canvas.hide()
            self.spectrum_plot_init()
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
        self.fig_canvas.setGeometry(420, 40, 800, 750)
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
            self.IMag_canvas.setGeometry(1030, 40, 400, 355)
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
        self.fig_canvas1.setGeometry(420, 40, 400, 355)
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
        self.fig_canvas2.setGeometry(830, 40, 400, 355)
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
        self.fig_canvas.setGeometry(420, 40, 400, 355)
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
            self.all_canvas.setGeometry(420, 40, 800, 750)
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
            self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.axis('equal')
            self.IPha_ax.set_title('Phase Image')

            self.IMag_canvas.draw()
            self.IMag_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IMag_canvas.setGeometry(420, 40, 400, 355)
            self.IPha_canvas.draw()
            self.IPha_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.IPha_canvas.setGeometry(830, 40, 400, 355)

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
            self.IPha_ax.imshow(params.img_st_pha[:, :], cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.axis('equal')
            self.IPha_ax.set_title('Phase Image')

            self.all_canvas.draw()
            self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
            self.all_canvas.setGeometry(420, 40, 800, 750)
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
        self.all_canvas.setGeometry(420, 40, 800, 750)
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
            self.IPha_ax.imshow(params.img_st_pha[n, :, :], cmap='gray');
            self.IPha_ax.axis('off');
            self.IPha_ax.axis('equal')
            if n == 0: self.IPha_ax.set_title('Phase Image')

        self.all_canvas.draw()
        self.all_canvas.setWindowTitle('Plot - ' + params.datapath + '.txt')
        self.all_canvas.setGeometry(420, 40, 800, 750)
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
            if params.imagefilter == 1:
                self.IDiff_aximshow(params.img_mag_diff, interpolation='gaussian', cmap='jet')
            else:
                self.IDiff_ax.imshow(params.img_mag_diff, cmap='jet')
            self.IDiff_ax.axis('off');
            self.IDiff_ax.set_aspect(1.0 / self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, interpolation='gaussian', cmap='jet', alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap='jet', alpha=0.5)
            self.IComb_ax.axis('off');
            self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
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
            if params.imagefilter == 1:
                self.IDiff_aximshow(params.img_mag_diff, interpolation='gaussian', cmap='jet')
            else:
                self.IDiff_ax.imshow(params.img_mag_diff, cmap='jet')
            self.IDiff_ax.axis('off');
            self.IDiff_ax.set_aspect(1.0 / self.IDiff_ax.get_data_ratio())
            self.IDiff_ax.set_title('Diffusion')
            if params.imagefilter == 1:
                self.IComb_ax.imshow(params.img_mag, interpolation='gaussian', cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, interpolation='gaussian', cmap='jet', alpha=0.5)
            else:
                self.IComb_ax.imshow(params.img_mag, cmap='gray')
                self.IComb_ax.imshow(params.img_mag_diff, cmap='jet', alpha=0.5)
            self.IComb_ax.axis('off');
            self.IComb_ax.set_aspect(1.0 / self.IComb_ax.get_data_ratio())
            self.IComb_ax.set_title('Combination')
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

    def save_mag_image_data(self):
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 0:
            self.datatxt = np.matrix(np.zeros((params.freqencyaxis.shape[0], 2)))
            self.datatxt[:, 0] = params.freqencyaxis.reshape(params.freqencyaxis.shape[0], 1)
            self.datatxt[:, 1] = params.spectrumfft
            np.savetxt('imagedata/' + params.dataTimestamp + '_Spectrum_Image_Data.txt', self.datatxt)
            print('Spectrum image data saved!')
        elif params.GUImode == 1:
            if params.sequence == 32 or params.sequence == 33 or params.sequence == 34:
                self.datatxt = np.matrix(np.zeros((params.img_mag.shape[1], params.img_mag.shape[0] * params.img_mag.shape[2])))
                for m in range(params.img_mag.shape[0]):
                    self.datatxt[:, m * params.img_mag.shape[2]:m * params.img_mag.shape[2] + params.img_mag.shape[2]] = params.img_mag[m, :, :]
                np.savetxt('imagedata/' + params.dataTimestamp + '_3D_' + str(params.img_mag.shape[0]) + '_Magnitude_Image_Data.txt', self.datatxt)
                print('Magnitude 3D image data saved!')
            elif params.sequence == 13 or params.sequence == 29:
                print('WIP!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Data.txt', params.img_mag)
                print('Magnitude image data saved!')
        elif params.GUImode == 2:
            self.datatxt = np.matrix(np.zeros((params.T1xvalues.shape[0], 3)))
            self.datatxt[:, 0] = params.T1xvalues.reshape(params.T1xvalues.shape[0], 1)
            self.datatxt[:, 1] = params.T1yvalues1.reshape(params.T1yvalues1.shape[0], 1)
            self.datatxt[:, 2] = params.T1regyvalues1.reshape(params.T1regyvalues1.shape[0], 1)
            np.savetxt('imagedata/' + params.dataTimestamp + '_T1_Image_Data.txt', self.datatxt)
            print('T1 image data saved!')
        elif params.GUImode == 3:
            self.datatxt = np.matrix(np.zeros((params.T2xvalues.shape[0], 3)))
            self.datatxt[:, 0] = params.T2xvalues.reshape(params.T2xvalues.shape[0], 1)
            self.datatxt[:, 1] = params.T2yvalues.reshape(params.T2yvalues.shape[0], 1)
            self.datatxt[:, 2] = params.T2regyvalues.reshape(params.T2regyvalues.shape[0], 1)
            np.savetxt('imagedata/' + params.dataTimestamp + '_T2_Image_Data.txt', self.datatxt)
            print('T2 image data saved!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 10:
                print('WIP!')
                os.makedirs(os.path.join('imagedata', params.dataTimestamp + '_Magnitude_Image_Stitching_3D_Data'))
                for n in range(params.img_st_mag.shape[0]):
                    np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Stitching_3D_Data' + '/' + params.dataTimestamp + '_Magnitude_Image_Stitching_Data_' + str(n) + '.txt', params.img_st_mag[n, :, :])
                    #np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Stitching_Data.txt', params.img_st_mag)
                print('Magnitude image data saved!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Magnitude_Image_Stitching_Data.txt', params.img_st_mag)
                print('Magnitude image data saved!')

    def save_pha_image_data(self):
        timestamp = datetime.now()
        params.dataTimestamp = timestamp.strftime('%Y%m%d_%H%M%S')
        if params.GUImode == 0:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 1:
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
        elif params.GUImode == 2:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 3:
            print('Please use Save Mag Image Data button!')
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
        if params.GUImode == 0:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 1:
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
        elif params.GUImode == 2:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 3:
            print('Please use Save Mag Image Data button!')
        elif params.GUImode == 4:
            print('WIP!')
        elif params.GUImode == 5:
            if params.sequence == 4:
                print('WIP!')
            else:
                np.savetxt('imagedata/' + params.dataTimestamp + '_Image_Stitching_Data.txt', params.img_st)
                print('Magnitude image data saved!')

    def animate(self):
        proc.animation_image_process()

        import matplotlib.animation as animation

        fig = plt.figure()

        im = plt.imshow(params.animationimage[params.kspace.shape[0] - 1, :, :], cmap='gray', animated=True)
        plt.axis('off')

        def updatefig(i):
            im.set_array(params.animationimage[i, :, :])
            return im,

        ani = animation.FuncAnimation(fig, updatefig, frames=params.kspace.shape[0], interval=params.animationstep, blit=True)
        plt.show()
        
class SerialReader(QObject):
    data_received =pyqtSignal(str)
    
    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial)
        self.timer.start(100)
        
    def read_serial(self):
        if self.serial_port.inWaiting() > 0:
            data = self.decode_data(self.my_readline())
            self.serial_port.flushOutput()
            #time.sleep(0.1)
            self.data_received.emit(data)
            
    def decode_data(self,byte_data):
        #print(byte_data)
        byte_data = byte_data[:-2]#byte_data.strip(b'\r\n')
        
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
        self.buffer = bytearray();
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
        '''
        if list==type(params.SAR_cal_raw):
            print('list')
        else:
            print('no list')
        '''
        self.ui = loadUi('ui/sar.ui')
        self.setWindowTitle('SAR Monitor')
        self.setGeometry(420, 40, 550, 460)
        
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
#         self.serial = serial.Serial('/dev/ttyUSB0', 112500, timeout=30, rtscts=False, xonxoff=False)#112500 19200
#         self.serial.setRTS(False)
#         self.serial_reader=SerialReader(self.serial)
#         self.serial_reader.data_received.connect(self.on_serial_data_received)
        
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
        
        #QTimer.singleShot(1,self.post_init)
    
    def post_init(self):
        self.trigger_no_sar.emit()
        self.SAR_Cal_pushButton.setEnabled(False)
        self.SAR_Send_Lookup_pushButton.setEnabled(False)
        self.SAR_New_Pat_pushButton.setEnabled(False)
        self.SAR_Error_Clear_pushButton.setEnabled(False)
        self.SAR_Log_Data_pushButton.setEnabled(False)
        self.SAR_Stop_pushButton.setEnabled(False)
        #self.close()
        
    def serial_init(self):       
        ports = list(serial.tools.list_ports.comports())        
        for port in ports:
            try:
                self.serial = serial.Serial(port.device, 112500, timeout=0.5, rtscts=False, xonxoff=False)#112500 19200
                self.serial.setRTS(False)
                mes = b'ident\x04\x4e\x78\xb2\r\n\t'# + '\r\n\t'.encode('utf-8')
                if self.serial.inWaiting()==0:
                    self.serial.write(mes)
                    response= self.serial.readline()
                    if response[0:6] == b'sar2.0':
                        self.serial.setRTS(False)
                        self.serial_reader=SerialReader(self.serial)
                        self.serial_reader.data_received.connect(self.on_serial_data_received)
                        print(f'SAR-Monitor connected to port: {port}')
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
        
        params.SAR_limit=round(self.dBm_to_mW(params.SAR_limit),1)
        self.SAR_Limit_doubleSpinBox.setValue(params.SAR_limit)
        
        params.SAR_6mlimit=round(self.dBm_to_mW(params.SAR_6mlimit),1)
        self.SAR_6mLimit_doubleSpinBox.setValue(params.SAR_6mlimit)
        
        params.SAR_peak_limit=round(self.dBm_to_mW(params.SAR_peak_limit),1)
        self.SAR_Tran_doubleSpinBox.setValue(params.SAR_peak_limit)
        
        params.SAR_max_power = round(self.dBm_to_mW(params.SAR_max_power),1)
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
        
        params.SAR_limit=round(self.mW_to_dBm(params.SAR_limit),1)
        self.SAR_Limit_doubleSpinBox.setValue(params.SAR_limit)
        
        params.SAR_6mlimit=round(self.mW_to_dBm(params.SAR_6mlimit),1)
        self.SAR_6mLimit_doubleSpinBox.setValue(params.SAR_6mlimit)
        
        params.SAR_peak_limit=round(self.mW_to_dBm(params.SAR_peak_limit),1)
        self.SAR_Tran_doubleSpinBox.setValue(params.SAR_peak_limit)
        
        params.SAR_max_power = round(self.mW_to_dBm(params.SAR_max_power),1)
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
        msg_box  = QMessageBox()
        msg_box.setWindowTitle('Send Lookup Table')
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
            #slope=(y[1]-y[0])/(x[1]-x[0])
            #return y[0]+slope*(x_new-x[0])
            return 0
        elif x_new > x[-1]:
            slope=(y[-1]-y[-2])/(x[-1]-x[-2])
            return y[-1]+slope*(x_new-x[-1])
        else:
            return np.interp(x_new,x,y)
        
    def convolve_sar(self,data):  
        return np.convolve(data,[1,2,0,-2,-1],mode='same')
    
    def convolve_sar2(self,data):
        #return np.convolve(data,[1,2,-1,-4,-1,2,1],mode='same')
        return np.convolve(data,[1,4,4,-4,-10,-4,4,4,1],mode='same')
    
    def find_plateau(self,sardata):
        threshhold=150
        steps=5 
        start=0
        end=0
        var=0
        found=0
        plats=[]
        zeros=np.array([])
        params.SAR_cal_start=[]
        params.SAR_cal_end=[]
        data = np.convolve(sardata,[1,4,4,-4,-10,-4,4,4,1],mode='same')
        
        i=20
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
            i +=1
    
        #print(plats)
        calmean=[0]
        for plat in plats: 
            calmean.append(int(np.ceil(np.mean(plat))))
        calmean[0]=int(np.ceil(np.mean(zeros)))
        params.SAR_cal_mean=calmean
        
#         print(params.SAR_cal_start)
#         print(params.SAR_cal_end)
#         print(params.SAR_cal_mean)
    
    def on_serial_data_received(self,data):
        print(data)
        if (self.save_var==21 or self.save_var==22) and data == 'err:stop':
            self.write_message('s')
            time.sleep(0.1)
        
        if data == 'SARstop' or data == 'stop':
            if self.save_var==21:
                self.write_message('new pat')       
                self.command= f'l10s{self.convert_limit(params.SAR_limit)}'
                #print(self.command)
                self.write_message(self.command)
                self.command= f'l6m{self.convert_limit(params.SAR_6mlimit)}'
                #print(self.command)
                self.write_message(self.command)
                self.command= f'tran{self.convert_limit(params.SAR_peak_limit)}'
                #print(self.command)
                self.write_message(self.command)
                self.SAR_10sLimit_lineEdit.setText(f'{params.SAR_limit}')
                self.SAR_6mLimit_lineEdit.setText(f'{params.SAR_6mlimit}')
                self.SAR_PeakLimit_lineEdit.setText(f'{params.SAR_peak_limit}')
                self.save_var=0
                #time.sleep(1)
                self.write_message('start')
                #print(self.command) 
            if self.save_var==22:
                #print('test')
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
            else: # foramtiere
                self.err_count=0
                if self.array_count < 4096:
                    self.command= f'c{self.array_count}:{params.SAR_cal_lookup[self.array_count]}'
                    self.write_message(self.command)
                    #print(self.command)
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
            else: # foramtiere
                self.err_count=0
                self.data_array.append(int(data))
                if len(self.data_array) > 2499:#2499:#9999 :
                    params.SAR_cal_raw=self.data_array
                    params.saveSarCal()
                    
                    self.file_name = f'SAR_Cal_{params.SAR_LOG_counter}.txt'   
                    self.file_path = os.path.join(self.cal_path,self.file_name)
                    np.savetxt(self.file_path,self.data_array)
                   
                    #self.cal_plot()
                    self.data_array.clear()
                    self.save_var=0
                    self.overlay.deleteLater()
                else:
                    self.command= f'rc{self.array_count}'
                    self.write_message(self.command)
                    self.array_count+=1
                        
        if self.save_var == 0:
            #print(data)
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
        
        #self.data_array.append(data)
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
                #self.overlay.deleteLater()  
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
    
    def error_switch(self,error):
        if error == '0':
            self.SAR_Status_lineEdit.setText('Error: Internal')
        elif error == '1':
            self.SAR_Status_lineEdit.setText('Error: Peak limit')
        elif error == '2':
            self.SAR_Status_lineEdit.setText('Error: 10s limit')
        elif error == '3':
            self.SAR_Status_lineEdit.setText('Error: 6m limit')
        elif error == '4':
            self.SAR_Status_lineEdit.setText('Error: Reflection limit')
        elif error == '5':
            self.SAR_Status_lineEdit.setText('Error: No limit')
        elif error == '6':
            self.SAR_Status_lineEdit.setText('Error: COM')
        #elif error == '10':
            #self.SAR_Status_lineEdit.setText('Communication')

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

        self.motor = motor # Refactor to be more precise

        self.load_params()

        self.ui = loadUi('ui/motor_tools.ui')
        self.setWindowTitle('Motor Tools')
        self.setGeometry(420, 40, 400, 370)

        self.Motor_MoveTo_doubleSpinBox.valueChanged.connect(lambda: self.new_move_value(box='to'))
        self.Motor_MoveBy_doubleSpinBox.valueChanged.connect(lambda: self.new_move_value(box='by'))
        self.Motor_Apply_pushButton.clicked.connect(lambda: self.apply())
        self.Motor_Home_pushButton.clicked.connect(lambda: self.home())
        
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

    def home(self):
        self.Motor_Home_pushButton.setEnabled(False)
        self.Motor_Apply_pushButton.setEnabled(False)
        home_s = 'G28\n'
        self.motor.write(home_s.encode('utf-8'))
        self.motor.waitForBytesWritten()

        time.sleep(0.1)

        response_s = 'M118 R0: homing finished\n'
        self.motor.write(response_s.encode('utf-8'))
        self.motor.waitForBytesWritten()

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
        
            apply_s = 'G0 ' + str(params.motor_goto_position) + '\n'
            self.motor.write(apply_s.encode('utf-8'))
            self.motor.waitForBytesWritten()

            time.sleep(0.1)

            response_s = 'M118 R0: finished moving\n'
            self.motor.write(response_s.encode('utf-8'))
            self.motor.waitForBytesWritten()

            # self.setEnabled(False)
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
