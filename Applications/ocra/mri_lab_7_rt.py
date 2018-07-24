#!/usr/bin/env python

# import general packages
import sys
import struct
import time

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget, \
    QLabel, QMessageBox, QCheckBox, QFileDialog
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QCoreApplication, QRegExp, QTimer
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket
from scipy import signal

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
MRI_Rt_Widget_Form, MRI_Rt_Widget_Base = loadUiType('ui/mri_rt_Widget.ui')


# MRI Lab widget 4: 1D Projection
class MRI_Rt_Widget(MRI_Rt_Widget_Base, MRI_Rt_Widget_Form):
    def __init__(self):
        super(MRI_Rt_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        # Set up basic GUi
        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqValue.setKeyboardTracking(False) # Value is sent only when enter or arrow key pressed
        self.acquireButton.clicked.connect(self.acquire)
        self.progressBar.setValue(0)

        # Gradient offsets related
        self.gradOffset_disp_x.setVisible(False)
        self.gradOffset_disp_y.setVisible(False)
        self.gradOffset_disp_z.setVisible(False)
        # use lambda function and objectName() to distinguish different Q-objects
        self.horizontalSlider_x.sliderMoved.connect(
            lambda: self.slider_disp_grad_offset(self.horizontalSlider_x))
        self.horizontalSlider_y.sliderMoved.connect(
            lambda: self.slider_disp_grad_offset(self.horizontalSlider_y))
        self.horizontalSlider_z.sliderMoved.connect(
            lambda: self.slider_disp_grad_offset(self.horizontalSlider_z))
        self.horizontalSlider_x.sliderReleased.connect(
            lambda: self.slider_set_grad_offset(self.horizontalSlider_x))
        self.horizontalSlider_y.sliderReleased.connect(
            lambda: self.slider_set_grad_offset(self.horizontalSlider_y))
        self.horizontalSlider_z.sliderReleased.connect(
            lambda: self.slider_set_grad_offset(self.horizontalSlider_z))
        self.gradOffset_x.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_x))
        self.gradOffset_y.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_y))
        self.gradOffset_z.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z))
        self.saveShimButton.clicked.connect(self.save_shim)
        self.loadShimButton.clicked.connect(self.load_shim)
        self.zeroShimButton.clicked.connect(self.zero_shim)


        # Setup buffer and offset for incoming data
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8 * self.size)
        self.offset = 0
        self.data = np.frombuffer(self.buffer, np.complex64)
        self.data_sum = np.frombuffer(self.buffer, np.complex64)

        # Real time projection demo
        self.angleSpin.valueChanged.connect(self.set_angle_spin)
        self.angleSpin.setKeyboardTracking(False)
        self.dial.sliderReleased.connect(self.set_angle)
        self.dial.sliderMoved.connect(self.set_angle_disp)
        self.angleDisp.setVisible(False)
        self.maxAngleDisp.setVisible(False)
        self.numAvg.valueChanged.connect(self.set_num_avg)
        self.angle = 0
        self.avgs_received = 0  # Number of averages acquired
        self.num_avgs = 1  # by default
        # self.num_pe = 64
        
        # Search demo
        self.max = 0.0
        self.maxes = []
        self.max_angle = 0.0
        self.counter = 0
        self.proj = np.zeros(1000)
        self.TR = 2000  # [ms]
        self.step = 0
        self.timer = QTimer(self)
        self.searchButton.clicked.connect(self.search_clicked)
        self.acqType.addItems(['Projection', '2D Image'])
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)

        # setup display
        # display 1: real time signal
        self.figure = Figure()
        self.figure.set_facecolor('none')
        # top and bottom axes: 2 rows, 1 column
        self.axes_top = self.figure.add_subplot(2, 1, 1)
        self.axes_bottom = self.figure.add_subplot(2, 1, 2)
        self.canvas = FigureCanvas(self.figure)
        self.plotLayout.addWidget(self.canvas)
        # create navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self.plotWidget, False)
        self.plotLayout.addWidget(self.toolbar)

        # display 2: k-space and image
        self.figure2 = Figure()
        self.figure2.set_facecolor('whitesmoke')
        self.axes_k_amp = self.figure2.add_subplot(3, 1, 1)
        self.axes_k_pha = self.figure2.add_subplot(3, 1, 2)
        self.axes_image = self.figure2.add_subplot(3, 1, 3)
        self.canvas2 = FigureCanvas(self.figure2)
        self.imageLayout.addWidget(self.canvas2)
        # create navigation toolbar
        self.toolbar2 = NavigationToolbar(self.canvas2, self.imageWidget, False)
        self.imageLayout.addWidget(self.toolbar2)

        # Acquire image
        self.full_data = np.matrix(np.zeros(np.size(self.data)))
        self.fname = "acq_data"
        self.buffers_received = 0
        self.images_received = 0
        self.num_pe = 64
        self.num_TR = 64 # num_TR = num_pe/etl (echo train length)
        self.etl = 2
        self.etl_idx = 0
        self.npe_idx = 0
        # self.seqType_idx = 0
        self.acqType_idx = 0
        self.img = []
        self.kspace_full = [] # full data
        self.kspace = [] # for recon
        self.k_amp = [] # for display
        self.k_pha = [] # for display
        self.tse_kspace = []
        self.tse_k_amp = []
        self.tse_k_pha = []
        self.kspace_center = 475 # k center time = 1.9*250: echo time is at 1.9ms after acq start
        self.crop_factor = 640 # 64 matrix size ~ 640 readout length (need FURTHER CALIBRATION)

    def start(self):
        self.idle = False
        gsocket.write(struct.pack('<I', 7))
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        self.horizontalSlider_x.setEnabled(True)
        self.horizontalSlider_y.setEnabled(True)
        self.horizontalSlider_z.setEnabled(True)
        self.gradOffset_x.setEnabled(True)
        self.gradOffset_y.setEnabled(True)
        self.gradOffset_z.setEnabled(True)
        # Setup global socket for receive data
        gsocket.readyRead.connect(self.read_data)

        # Send the number of averages
        self.set_num_avg(self.num_avgs)

    def stop(self):
        print("Stopping MRI_Rt_Widget")
        self.idle = True
        gsocket.write(struct.pack('<I', 0))

        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.horizontalSlider_x.setEnabled(False)
        self.horizontalSlider_y.setEnabled(False)
        self.horizontalSlider_z.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        gsocket.readyRead.disconnect()

    def set_freq(self, freq):
        print("\tSetting frequency")
        parameters.set_freq(freq)
        gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * freq)))
        # 2^28 = 268,435,456 for frequency setting
        if not self.idle:
            print("Acquiring data")

    def set_angle(self, *args):
        ''' Sends the angle to the server '''
        if self.idle: return

        if len(args) == 0:
            value = self.dial.value()
            value = (value - 90)  # So that zero degrees is horizontal
            # value = value-270 # So that zero degrees is horizontal
            if value < 0:
                self.angle = 360 + value  # Need positive angle to pack
            else:
                self.angle = value
        else:
            self.angle = args[0]
            # self.dial.setValue(self.angle + 90)

        self.angleDisp.setVisible(False)
        self.angleSpin.setValue(self.angle)

    def set_angle_spin(self, value):
        if self.idle: return
        if value < 0:
            self.angle = 360 + value  # Need positive angle to pack
        else:
            self.angle = value

        # print("Value = {}".format(value))
        self.dial.setValue(value + 90)  # dial is offset 90 degrees from spin box 
        # self.dial.setValue(value - 90)
        # print("Current angle = {}".format(self.angle))
        # represent this with at least 12 bits, so that we can cover 0 to 360
        gsocket.write(struct.pack('<I', 3 << 28 | self.angle))

    def set_angle_disp(self, value):
        if self.idle: return
        if value < 0:
            angle = 360 + value  # Need positive angle to pack
        else:
            angle = value
        self.angleDisp.setVisible(True)
        self.angleDisp.setText(str(angle))

    def set_num_avg(self, value):
        if self.idle: return
        self.num_avgs = int(value)
        print("Number of averages = {}".format(value))
        gsocket.write(struct.pack('<I', 4 << 28 | int(value)))

    def set_acq_type(self, *args):
        if len(args) == 0:
            self.acqType_idx = self.acqType.currentIndex()
        else:
            self.acqType_idx = args[0]
            self.acqType.setCurrentIndex(self.acqType_idx)

    def acquire(self):
        # clear the plots, need to call draw() to update
        self.axes_bottom.clear()
        self.axes_top.clear()
        self.canvas.draw()
        self.axes_k_amp.clear()
        self.axes_k_pha.clear()
        self.axes_image.clear()
        self.canvas2.draw()

        self.progressBar.setValue(0)

        self.kspace_full = np.matrix(np.zeros((self.num_TR, 50000), dtype=np.complex64))

        crop_size = int(self.num_pe / 64 * self.crop_factor)
        self.kspace = np.matrix(np.zeros((self.num_pe, crop_size), dtype = np.complex64))
        self.k_amp = np.matrix(np.zeros((self.num_pe, self.num_pe*2)))
        self.k_pha = np.matrix(np.zeros((self.num_pe, self.num_pe*2)))
        self.img = np.matrix(np.zeros((self.num_pe,self.num_pe)))

        self.acqType_idx = self.acqType.currentIndex()
        if self.acqType_idx == 0: # Projections
            gsocket.write(struct.pack('<I', 3 << 28 | self.angle))
            print("CMD: Acquiring projection")
        elif self.acqType_idx == 1: # Image
            gsocket.write(struct.pack('<I', 5 << 28 | self.angle))
            print("CMD: Acquiring 2D image")   

        # # enable/disable GUI elements
        self.freqValue.setEnabled(False)
        self.acqType.setEnabled(False)
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.searchButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)

    def slider_disp_grad_offset(self, slider):
        if slider.objectName() == 'horizontalSlider_x':
            self.gradOffset_disp_x.setVisible(True)
            self.gradOffset_disp_x.setText(str(self.horizontalSlider_x.value()))
        elif slider.objectName() == 'horizontalSlider_y':
            self.gradOffset_disp_y.setVisible(True)
            self.gradOffset_disp_y.setText(str(self.horizontalSlider_y.value()))
        elif slider.objectName() == 'horizontalSlider_z':
            self.gradOffset_disp_z.setVisible(True)
            self.gradOffset_disp_z.setText(str(self.horizontalSlider_z.value()))
        else:
            print('Error: slider_disp_grad_offset')
            return

    def slider_set_grad_offset(self, slider):
        if slider.objectName() == 'horizontalSlider_x':
            self.gradOffset_disp_x.setVisible(False)
            self.gradOffset_x.setValue(self.horizontalSlider_x.value())
        elif slider.objectName() == 'horizontalSlider_y':
            self.gradOffset_disp_y.setVisible(False)
            self.gradOffset_y.setValue(self.horizontalSlider_y.value())
        elif slider.objectName() == 'horizontalSlider_z':
            self.gradOffset_disp_z.setVisible(False)
            self.gradOffset_z.setValue(self.horizontalSlider_z.value())
        else:
            print('Error: slider_set_grad_offset')
            return

    def set_grad_offset(self, spinBox):
        if spinBox.objectName() == 'gradOffset_x':
            offsetX = self.gradOffset_x.value()
            self.horizontalSlider_x.setValue(offsetX)
            print("\tSetting grad offset x to {}".format(offsetX))
            if offsetX > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | offsetX))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | 1 << 20 | -offsetX))
            print("Acquiring data")
        elif spinBox.objectName() == 'gradOffset_y':
            offsetY = self.gradOffset_y.value()
            self.horizontalSlider_y.setValue(offsetY)
            print("\tSetting grad offset y to {}".format(offsetY))
            if offsetY > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | offsetY))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | 1 << 20 | -offsetY))
            print("Acquiring data")
        elif spinBox.objectName() == 'gradOffset_z':
            offsetZ = self.gradOffset_z.value()
            self.horizontalSlider_z.setValue(offsetZ)
            print("\tSetting grad offset z to {}".format(offsetZ))
            if offsetZ > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 3 << 24 | offsetZ))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 3 << 24 | 1 << 20 | -offsetZ))
            print("Acquiring data")
        else:
            print('Error: set_grad_offset')
            return

    def save_shim(self):
        parameters.set_grad_offset_x(self.gradOffset_x.value())
        parameters.set_grad_offset_y(self.gradOffset_y.value())
        parameters.set_grad_offset_z(self.gradOffset_z.value())

    def load_shim(self):
        print("\tLoad grad offsets")
        self.gradOffset_x.valueChanged.disconnect()
        self.gradOffset_y.valueChanged.disconnect()
        self.gradOffset_z.valueChanged.disconnect()
        self.gradOffset_x.setValue(parameters.get_grad_offset_x())
        self.gradOffset_y.setValue(parameters.get_grad_offset_y())
        self.gradOffset_z.setValue(parameters.get_grad_offset_z())
        self.horizontalSlider_x.setValue(parameters.get_grad_offset_x())
        self.horizontalSlider_y.setValue(parameters.get_grad_offset_y())
        self.horizontalSlider_z.setValue(parameters.get_grad_offset_z())
        self.gradOffset_x.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_x))
        self.gradOffset_y.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_y))
        self.gradOffset_z.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z))
        offsetX = self.gradOffset_x.value()
        self.horizontalSlider_x.setValue(offsetX)
        if offsetX > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetX))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetX))
        offsetY = self.gradOffset_y.value()
        self.horizontalSlider_y.setValue(offsetY)
        if offsetY > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetY))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetY))
        offsetZ = self.gradOffset_z.value()
        self.horizontalSlider_z.setValue(offsetZ)
        if offsetZ > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetZ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetZ))
        print("Acquiring data")

    def zero_shim(self):
        print("\tZero grad offsets")
        self.gradOffset_x.valueChanged.disconnect()
        self.gradOffset_y.valueChanged.disconnect()
        self.gradOffset_z.valueChanged.disconnect()
        self.gradOffset_x.setValue(0)
        self.gradOffset_y.setValue(0)
        self.gradOffset_z.setValue(0)
        self.horizontalSlider_x.setValue(0)
        self.horizontalSlider_y.setValue(0)
        self.horizontalSlider_z.setValue(0)
        self.gradOffset_x.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_x))
        self.gradOffset_y.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_y))
        self.gradOffset_z.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z))
        gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24))
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

        current_data = self.data

        print("Read data - current index = {}".format(self.acqType_idx))
        if self.acqType_idx == 1: # image
            self.avgs_received = 0 
            print("Acquired TR = {}".format(self.buffers_received))
            self.buffers_received += 1
        else: # for averaging projections
            self.data_sum += current_data
        
        self.avgs_received += 1
            # print("Averages acquired = {}".format(self.avgs_received))

        if self.buffers_received == self.num_pe:
            sp.savemat(self.fname, {"acq_data": self.full_data})  # Save the data
            print("Data saved!")
            self.buffers_received = 0
            self.full_data = np.matrix(np.zeros(np.size(self.data)))
            self.startButton.setEnabled(False)
            self.freqValue.setEnabled(True)
            self.acqType.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)

        self.display_data()

    def display_data(self):
        # Clear the plots: bottom-time domain, top-frequency domain
        self.axes_bottom.clear()
        self.axes_bottom.grid()
        self.axes_top.clear()
        self.axes_top.grid()

        print("Averages acquired = {}".format(self.avgs_received))

        if self.avgs_received == self.num_avgs:
            data = self.data_sum/(self.num_avgs + 1.0)
            dclip = data[0:1000]
            fft_data = np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip)))

            fft_avg = self.running_avg(fft_data)
            cntr = int(np.floor(len(fft_avg)/2))
            mag_avg = np.abs(fft_avg)
            mag_avg = mag_avg[cntr - 100: cntr+100]
            freqaxis_avg = np.linspace(-10000, 10000,len(mag_avg))
            self.curve_top = self.axes_top.plot(freqaxis_avg, mag_avg)
            self.axes_top.set_xlabel('Frequency (Hz)')

            # set the proj attribute
            self.proj = mag_avg

            # Enable/disable buttons
            self.acquireButton.setEnabled(True)
            self.acqType.setEnabled(True)
            self.searchButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)
            self.saveShimButton.setEnabled(True)

            # # FOR DEBUGGING
            maxind = np.argmax(self.proj)
            maxval = self.proj[maxind]
            print("maxval = {}".format(maxval))
            self.avgs_received = 0
            self.data_sum = np.frombuffer(self.buffer, np.complex64)  # reset the data

        else:
            data = self.data

        mag = np.abs(data)
        pha = np.angle(data)
        real = np.real(data)
        imag = np.imag(data)

        # Plot the top (frequency domain): use signal from 0~4ms
        dclip = data[0:1000]
        freqaxis = np.linspace(-125000, 125000, 1000)
        fft_data = np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip)))

        # Plot the bottom (time domain): display time signal from 0~4ms [0~1000]
        mag_t = mag[0:1000]
        real_t = real[0:1000]
        imag_t = imag[0:1000]
        time_axis = np.linspace(0, 4, 1000)
        self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t)   # blue
        self.curve_bottom = self.axes_bottom.plot(time_axis, real_t)  # red
        self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t)  # green
        self.axes_bottom.set_xlabel('Time (ms)')

        # Update the figure
        self.canvas.draw()

        if self.acqType_idx == 1: # image
            # Imaging plots
            self.kspace_full[self.buffers_received, :] = data

            # display kspace
            self.k_amp[self.buffers_received, :] = mag[self.kspace_center - self.num_pe
                                                       : self.kspace_center + self.num_pe]
            self.k_pha[self.buffers_received, :] = pha[self.kspace_center - self.num_pe
                                                       : (self.kspace_center + self.num_pe)]
            k_amp_1og10 = np.log10(self.k_amp)

            self.axes_k_amp.imshow(k_amp_1og10, cmap='plasma')
            self.axes_k_amp.set_title('k-space amplitude (log10)')
            self.axes_k_pha.imshow(self.k_pha, cmap='plasma')
            self.axes_k_pha.set_title('k-space phase')
            self.canvas2.draw()

            # display image
            crop_size = int(self.num_pe / 64 * self.crop_factor)
            half_crop_size = int(crop_size / 2)
            # cntr = int(crop_size * 0.975 / 2)
            # cntr = int(crop_size * 0.98 / 2)
            cntr = int(crop_size * 1.0 / 2)
            if self.num_pe >= 128:
                self.kspace = self.kspace_full[0:self.num_pe, 0:crop_size]
                Y = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspace)))
                img = np.abs(
                    Y[:, cntr - int(self.num_pe / 2 - 1):cntr + int(self.num_pe / 2 + 1)])
            else:
                self.kspace = self.kspace_full[0:self.num_pe,
                              self.kspace_center - half_crop_size
                              : self.kspace_center + half_crop_size]
                Y = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.kspace)))
                img = np.abs(
                    Y[:, cntr - int(self.num_pe / 2 - 1):cntr + int(self.num_pe / 2 + 1)])
            self.img = img
            self.axes_image.imshow(self.img, cmap='gray')
            self.axes_image.set_title('image')
            self.canvas2.draw()

            self.progressBar.setValue(self.buffers_received/self.num_TR*100)

    def running_avg(self, x):
        N = 5 # number of points to average over
        avg = np.convolve(x, np.ones((N,)) / N, mode='valid')
        return avg

    def search_clicked(self):
        # Parameters
        self.max_angle = 0.0
        self.max = 0.0
        self.counter = 0
        self.angle = 0
        maxval = 0
        self.num_avgs = self.numAvg.value()
        self.searchButton.setEnabled(False)
        self.acquireButton.setEnabled(False)

        self.set_acq_type(0)
        print("Current index = {}".format(self.acqType.currentIndex()))
        self.timer.timeout.connect(self.search)
        self.search()
        self.timer.start(2000) # ms
        # self.timer.start(900)


    def search(self):
        # Try to do a coarse search first
        angles = [0, 30, 60, 90, 120, 150]

        maxind = np.argmax(self.proj)
        maxval = self.proj[maxind]
        self.maxes.append(maxval)
        print("Max val = {}".format(maxval))
        print("Maxes = {}".format(self.maxes))

        if self.counter < len(angles):
            self.set_angle(angles[self.counter])
            self.counter += 1
        else:
            # Find the coarse max
            starting_ind = np.argmax(self.maxes)
            print("Starting ind = {}".format(starting_ind))
            # starting_angle = angles[starting_ind]
            if starting_ind != 0: # The first angle is repeated twice
                self.max = self.maxes[starting_ind - 1]
                starting_angle = angles[starting_ind - 1]
            else:
                self.max = self.maxes[starting_ind]
                starting_angle = angles[starting_ind]
            print("Starting angle = {}".format(starting_angle))
            self.set_angle(starting_angle)

            # Reset params
            self.counter = 0
            self.maxes = []
            self.timer.timeout.disconnect(self.search)
            self.acquireButton.setEnabled(True)
            self.counter = 0

            # Now do a fine search
            # self.step = 5
            self.step = 10
            self.timer.timeout.connect(self.fine_search)
            self.timer.start(2000)
            # self.timer.start(900)


        print("Angle = {}".format(self.angle))
        print("")

    def fine_search(self):
        # parameters
        # tolerance = 2 # degrees
        tolerance = 1 # degrees
        # step_sizes = [10,7,5,4,3,2,1]
        step_sizes = [7,5,4,3,2,1]

        # compute max
        maxind = np.argmax(self.proj)
        maxval = self.proj[maxind]

        # print("")
        print("Max val = {}".format(maxval))
        print("Max = {}".format(self.max))
        
        if maxval > self.max:
            # increment angle by step
            self.max = maxval
            self.max_angle = self.angle
            self.angle += self.step

        elif maxval < self.max:
            # We have overshot
            if self.counter < len(step_sizes):
                self.step = step_sizes[self.counter]
                self.angle -= self.step
                self.counter += 1

        if self.step <= tolerance:
            print("Max angle is {}".format(self.max_angle))
            print("Max value is {}".format(self.max))
            if self.max_angle - 90 < 0:
                self.set_angle(self.max_angle - 90 + 360)
            else:
                self.set_angle(self.max_angle - 90)
            self.maxAngleDisp.setText(str(self.max_angle))
            self.timer.timeout.disconnect(self.fine_search)
            self.searchButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.maxAngleDisp.setVisible(True)
            self.acqType.setEnabled(True)

            # # Reset parameters
            self.counter = 0
            self.max_angle = 0.0
            self.max = 0.0
            return

        # Set the next angle
        print("")
        print("Angle = {}".format(self.angle))

        if self.angle < 0:
            self.angle = self.angle + 360 # make it positive
        self.set_angle(self.angle)

    def recon(self):
        data_contents = sp.loadmat(self.fname)
        acq_data = data_contents['acq_data']
        print(np.size(acq_data, 0))
        print(np.size(acq_data, 1))
        print(np.size(acq_data))
        # kspace = acq_data[1:self.num_TR+1, 0:750]
        kspace = acq_data[1:self.num_TR + 1, 0:640]
        Y = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(kspace)))
        # cntr = int(750 / 2 - 5)
        cntr = int(640 / 2 - 5)
        img = np.abs(Y[:, cntr - int(self.num_TR / 2 - 1):cntr + int(self.num_TR / 2 + 1)])
        plt.figure()
        plt.imshow(img, cmap='gray')
        plt.show()
