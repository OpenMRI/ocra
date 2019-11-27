#!/usr/bin/env python

# import general packages
import sys
import struct

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget, \
    QLabel, QMessageBox, QCheckBox, QFileDialog
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QCoreApplication, QRegExp
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket

# import calculation and plot packages
import numpy as np
import scipy.io as sp
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# import private packages
from globalsocket import gsocket
from basicpara import parameters
from assembler import Assembler

# load .ui files
MRI_Proj_Widget_Form, MRI_Proj_Widget_Base = loadUiType('ui/mri_proj_Widget.ui')


# MRI Lab widget 4: 1D Projection
class MRI_Proj_Widget(MRI_Proj_Widget_Base, MRI_Proj_Widget_Form):
    def __init__(self):
        super(MRI_Proj_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.if_all_projections = 0 # 0 - one projection, 1 - all three projections
        self.acq_num = 0 # for recording the 3 projections

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        # self.freqCheckBox = QCheckBox('Zoom')
        # self.checkBoxLayout.addWidget(self.freqCheckBox)
        self.projAxisValue.addItems(['x', 'y', 'z'])
        self.projAxisValue.currentIndexChanged.connect(self.set_proj_axis)
        self.acquireButton.clicked.connect(self.acquire)
        self.acquireAllButton.clicked.connect(self.acquire_all)

        # Gradient offsets related
        self.loadShimButton.clicked.connect(self.load_shim)
        self.zeroShimButton.clicked.connect(self.zero_shim)
        self.shim_x.setText(str(parameters.get_grad_offset_x()))
        self.shim_y.setText(str(parameters.get_grad_offset_y()))
        self.shim_z.setText(str(parameters.get_grad_offset_z()))
        self.shim_x.setReadOnly(True)
        self.shim_y.setReadOnly(True)
        self.shim_z.setReadOnly(True)

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.projAxisValue.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.acquireAllButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)

        # Setup buffer and offset for incoming data
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8 * self.size)
        self.offset = 0
        self.data = np.frombuffer(self.buffer, np.complex64)
        self.data_x = np.frombuffer(self.buffer, np.complex64)
        self.data_y = np.frombuffer(self.buffer, np.complex64)
        self.data_z = np.frombuffer(self.buffer, np.complex64)
        # print(self.data.size)

        # Setup plot
        self.figure = Figure()
        self.figure.set_facecolor('none')
        # top and bottom axes: 2 rows, 1 column
        self.axes_top = self.figure.add_subplot(2, 1, 1)
        self.axes_bottom = self.figure.add_subplot(2, 1, 2)
        self.canvas = FigureCanvas(self.figure)
        self.plotLayout.addWidget(self.canvas)
        # create navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self.plotWidget, False)
        # remove subplots action (might be useful in the future)
        # actions = self.toolbar.actions()
        # self.toolbar.removeAction(actions[7])
        self.plotLayout.addWidget(self.toolbar)

        # Setup plot for all three projections
        self.all_proj_figure = Figure()
        self.all_proj_figure.set_facecolor('none')
        # top and bottom axes: 3 rows, 1 column
        self.plot_x = self.all_proj_figure.add_subplot(3, 1, 1)
        self.plot_y = self.all_proj_figure.add_subplot(3, 1, 2)
        self.plot_z = self.all_proj_figure.add_subplot(3, 1, 3)
        # self.all_proj_figure.tight_layout()
        self.all_proj_figure.subplots_adjust(hspace=0.300)
        self.all_proj_canvas = FigureCanvas(self.all_proj_figure)
        self.allProjLayout.addWidget(self.all_proj_canvas)
        self.all_proj_toolbar = NavigationToolbar(self.all_proj_canvas, self.allProjWidget, False)
        self.allProjLayout.addWidget(self.all_proj_toolbar)

    def start(self):
        gsocket.write(struct.pack('<I', 4))
        self.load_shim()
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.projAxisValue.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.acquireAllButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        # Setup global socket for receive data
        gsocket.readyRead.connect(self.read_data)
        self.idle = False

    def stop(self):
        self.idle = True
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.projAxisValue.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.acquireAllButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        # Disconnect global socket
        gsocket.readyRead.disconnect()

    def set_freq(self, freq):
        print("\tSetting frequency")
        parameters.set_freq(freq)
        gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * freq)))
        # 2^28 = 268,435,456 for frequency setting
        if not self.idle:
            print("Acquiring data")

    def acquire(self):
        self.if_all_projections = 0
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
        print("Acquiring data")

    def acquire_all(self):
        self.if_all_projections = 1
        gsocket.write(struct.pack('<I', 3 << 28))
        print("Acquiring all projections")
        self.plot_x.clear()
        self.plot_y.clear()
        self.plot_z.clear()
        self.stopButton.setEnabled(False)
        self.projAxisValue.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.acquireAllButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)

    def set_proj_axis(self, currentIndex):
        ''' Sets the projection axis (x, y, z) '''
        if currentIndex == 0:
            print("\tChanging projection axis to X")
            gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24))
        elif currentIndex == 1:
            print("\tChanging projection axis to Y")
            gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24))
        elif currentIndex == 2:
            print("\tChanging projection axis to Z")
            gsocket.write(struct.pack('<I', 2 << 28 | 3 << 24))
        else:
            print("AXIS ERROR")

    def load_shim(self):
        print("\tLoad grad offsets")
        self.shim_x.setText(str(parameters.get_grad_offset_x()))
        self.shim_y.setText(str(parameters.get_grad_offset_y()))
        self.shim_z.setText(str(parameters.get_grad_offset_z()))
        offsetX = int(self.shim_x.text())
        if offsetX > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetX))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetX))
        offsetY = int(self.shim_y.text())
        if offsetY > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetY))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetY))
        offsetZ = int(self.shim_z.text())
        if offsetZ > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetZ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetZ))
        if self.idle:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 0<<20 ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1<<20 ))
            print("Acquiring data")

    def zero_shim(self):
        print("\tZero grad offsets")
        self.shim_x.setText(str(0))
        self.shim_y.setText(str(0))
        self.shim_z.setText(str(0))
        gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 ))
        print("Acquiring data")

    def read_data(self):
        # wait for enough data and read to self.buffer
        size = gsocket.bytesAvailable()
        if size <= 0:
            return
        elif self.offset + size < 8 * self.size:
            self.buffer[self.offset:self.offset + size] = gsocket.read(size)
            self.offset += size
            # if the buffer is not complete, return and wait for more
            return
        else:
            self.buffer[self.offset:8 * self.size] = gsocket.read(8 * self.size - self.offset)
            self.offset = 0

        if not self.if_all_projections:
            self.display_data()
        else:
            self.display_all()

    def display_data(self):
        # Clear the plots: bottom-time domain, top-frequency domain
        self.axes_bottom.clear()
        self.axes_bottom.grid()
        self.axes_top.clear()
        self.axes_top.grid()

        # Get magnitude, real and imaginary part of data
        data = self.data
        mag = np.abs(data)
        real = np.real(data)
        imag = np.imag(data)

        # Plot the bottom (time domain): display time signal from 0~4ms [0~1000]
        mag_t = mag[0:1000]
        real_t = real[0:1000]
        imag_t = imag[0:1000]
        time_axis = np.linspace(0, 4, 1000)
        self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t)   # blue
        self.curve_bottom = self.axes_bottom.plot(time_axis, real_t)  # red
        self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t)  # green
        self.axes_bottom.set_xlabel('time, ms')

        # Plot the top (frequency domain): use signal from 0~4ms
        dclip = data[0:1000];
        freqaxis = np.linspace(-125000, 125000, 1000)
        fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
        self.curve_top = self.axes_top.plot(freqaxis, fft_mag)
        self.axes_top.set_xlabel('frequency, Hz')

        # Update the figure
        self.canvas.draw()

    def display_all(self):
        self.acq_num += 1
        if self.acq_num == 1:
            self.data_x = self.data
            self.display_data()
            self.plot_x.clear()
            self.plot_x.grid()
            dclip_x = self.data_x[0:1000];
            freqaxis = np.linspace(-125000, 125000, 1000)
            fft_mag_x = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip_x))))
            self.plot_x.plot(freqaxis, fft_mag_x)
            # self.plot_x.set_xlabel('frequency, Hz')
            self.plot_x.set_title('x projection')
            self.all_proj_canvas.draw()

        elif self.acq_num == 2:
            self.data_y = self.data
            self.display_data()
            self.plot_y.clear()
            self.plot_y.grid()
            dclip_y = self.data_y[0:1000];
            freqaxis = np.linspace(-125000, 125000, 1000)
            fft_mag_y = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip_y))))
            self.plot_y.plot(freqaxis, fft_mag_y)
            # self.plot_y.set_xlabel('frequency, Hz')
            self.plot_y.set_title('y projection')
            self.all_proj_canvas.draw()

        else:
            print('z')
            self.data_z = self.data
            self.display_data()
            self.plot_z.clear()
            self.plot_z.grid()
            dclip_z = self.data_z[0:1000];
            freqaxis = np.linspace(-125000, 125000, 1000)
            fft_mag_z = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip_z))))
            self.plot_z.plot(freqaxis, fft_mag_z)
            # self.plot_z.set_xlabel('frequency, Hz')
            self.plot_z.set_title('z projection')
            self.all_proj_canvas.draw()

            self.acq_num = 0
            self.stopButton.setEnabled(True)
            self.projAxisValue.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.acquireAllButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)
