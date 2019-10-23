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
MRI_3DImag_Widget_Form, MRI_3DImag_Widget_Base = loadUiType('ui/mri_3dimag_Widget.ui')


# MRI Lab widget 6: 3D Image
class MRI_3DImag_Widget(MRI_3DImag_Widget_Base, MRI_3DImag_Widget_Form):
    def __init__(self):
        super(MRI_3DImag_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.acquireButton.clicked.connect(self.acquire)

        # Gradient offsets related
        self.loadShimButton.clicked.connect(self.load_shim)
        self.zeroShimButton.clicked.connect(self.zero_shim)
        self.shim_x.setText(str(parameters.get_grad_offset_x()))
        self.shim_y.setText(str(parameters.get_grad_offset_y()))
        self.shim_z.setText(str(parameters.get_grad_offset_z()))
        self.shim_x.setReadOnly(True)
        self.shim_y.setReadOnly(True)
        self.shim_z.setReadOnly(True)

        # Sequence Type
        self.seqType.addItems(['Spin Echo', 'Gradient Echo'])
        # self.seqType.addItems(['Spin Echo', 'Gradient Echo', 'Turbo Spin Echo'])

        # Imaging parameters
        self.npe.addItems(['4', '8', '16', '32', '64', '128', '256'])
        self.npe.currentIndexChanged.connect(self.set_readout_size)
        self.npe2.addItems(['4', '8', '16', '32'])
        self.size1.setText(self.npe.currentText())
        self.size1.setReadOnly(True)

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)

        # Setup buffer and offset for incoming data
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8 * self.size)
        self.offset = 0
        self.data = np.frombuffer(self.buffer, np.complex64)
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

        # Acquire image
        self.full_data = np.matrix(np.zeros(np.size(self.data)))
        self.fnameprefix = "acq_data_aspa_se_64_16_"
        self.fname = ""
        self.buffers_received = 0 # for npe  phase encoding 1
        self.slice_received = 0   # for npe2 phase encoding 2
        self.num_pe = 0  # self.num_TR
        self.num_pe2 = 0
        self.npe_idx = 0
        self.npe2_idx = 0
        self.seqType_idx = 0


    def start(self):
        self.buffers_received = 0
        gsocket.write(struct.pack('<I', 6))
        self.load_shim()
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.acquireButton.setEnabled(True)
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
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        # Disconnect global socket
        # if (gsocket.readyRead.isSignalConnected()):
        gsocket.readyRead.disconnect()

    def set_freq(self, freq):
        print("\tSetting frequency")
        parameters.set_freq(freq)
        gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * freq)))
        # 2^28 = 268,435,456 for frequency setting
        if not self.idle:
            print("Acquiring data")

    def set_readout_size(self):
        self.size1.setText(self.npe.currentText())

    def acquire(self):
        self.num_pe = int(self.npe.currentText())
        self.num_pe2 = int(self.npe2.currentText())
        self.npe_idx = self.npe.currentIndex()
        self.npe2_idx = self.npe2.currentIndex()
        self.seqType_idx = self.seqType.currentIndex()
        print(self.npe_idx)
        print(self.num_pe)
        print(self.npe2_idx)
        print(self.num_pe2)
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24 | self.npe2_idx<<8 | self.npe_idx<<4 |
                                  self.seqType_idx ))
        print("Acquiring data = {} x {} x {}".format(self.num_pe, self.num_pe, self.num_pe2))
        self.freqValue.setEnabled(False)
        self.seqType.setEnabled(False)
        self.npe.setEnabled(False)
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)

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

        self.display_data()

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
        self.curve_top, = self.axes_top.plot(freqaxis, fft_mag)
        self.axes_top.set_xlabel('frequency, Hz')

        # Update the figure
        self.canvas.draw()

        # Record kspace data for 2D image reconstruction
        self.full_data = np.vstack([self.full_data, self.data])
        print("Acquired {}th TR = {}".format(self.slice_received, self.buffers_received))
        self.buffers_received = self.buffers_received + 1
        if self.buffers_received == self.num_pe:
            self.buffers_received = 0
            self.slice_received = self.slice_received + 1
            self.fname = self.fnameprefix + str(self.slice_received)
            sp.savemat(self.fname, {"acq_data": self.full_data}) # Save the data
            self.full_data = np.matrix(np.zeros(np.size(self.data)))
            print("Data saved!")
            self.buffers_received = 0
            # self.reconButton.setEnabled(True)  # Let the user recon now
            self.freqValue.setEnabled(True)
            self.seqType.setEnabled(True)
            self.npe.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)
