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
MRI_SE_Widget_Form, MRI_SE_Widget_Base = loadUiType('ui/mri_se_Widget.ui')


# MRI Lab widget 2: Spin Echo (SE)
class MRI_SE_Widget(MRI_SE_Widget_Base, MRI_SE_Widget_Form):
    def __init__(self):
        super(MRI_SE_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.seq_filename = 'sequence/basic/se_default.txt'

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
		# don't emit valueChanged signal while typing
        self.freqValue.setKeyboardTracking(False)
        self.atValue.setKeyboardTracking(False)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.atValue.valueChanged.connect(self.set_at)
        self.zoomCheckBox = QCheckBox('Zoom')
        self.zoomLayout.addWidget(self.zoomCheckBox)
        self.peakWindowCheckBox = QCheckBox('Peak Window')
        self.peakWindowLayout.addWidget(self.peakWindowCheckBox)
        self.acquireButton.clicked.connect(self.acquire)
        # self.cycAcqBtn.clicked.connect(self.averaging)

		# Don't emit valueChanged signal while typing
        self.gradOffset_x.setKeyboardTracking(False)
        self.gradOffset_y.setKeyboardTracking(False)
        self.gradOffset_z.setKeyboardTracking(False)
        self.gradOffset_z2.setKeyboardTracking(False)

        self.gradOffset_x.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_x))
        self.gradOffset_y.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_y))
        self.gradOffset_z.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z))
        self.gradOffset_z2.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z2))

        self.saveShimButton.clicked.connect(self.save_shim)
        self.loadShimButton.clicked.connect(self.load_shim)
        self.zeroShimButton.clicked.connect(self.zero_shim)

        self.peak.setReadOnly(True)
        self.fwhm.setReadOnly(True)
        self.snr.setReadOnly(True)

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.gradOffset_z2.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.cycAcqBtn.setEnabled(False)
        self.cyclesValue.setEnabled(False)
        self.zoomCheckBox.setEnabled(False)
        self.peakWindowCheckBox.setEnabled(False)

        # Setup buffer and offset for incoming data
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8 * self.size)
        self.offset = 0
        self.data = np.frombuffer(self.buffer, np.complex64)

        # Implementation of averaging flag
        self.averageFlag = False
        # self.averageData = 0
        # self.averageData = self.data[0:2500]
        # self.averageMag = self.data[0:2500]
        # self.averageReal = self.data[0:2500]
        # self.averageImag = self.data[0:2500]
        # self.averageCycle = 0

        # setup display
        self.figure = Figure()
        self.figure.set_facecolor('none')
        # top and bottom axes: 2 rows, 1 column
        self.axes_top = self.figure.add_subplot(2, 1, 1)
        self.axes_bottom = self.figure.add_subplot(2, 1, 2)

        self.axes_top.set_xlabel('frequency [Hz]')
        self.axes_top.set_ylabel('freq. domain')
        self.axes_bottom.set_xlabel('time [ms]')
        self.axes_bottom.set_ylabel('time domain')
        self.axes_top.grid()
        self.axes_bottom.grid()

        self.figure.set_tight_layout(True)

        self.canvas = FigureCanvas(self.figure)
        self.plotLayout.addWidget(self.canvas)
        # create navigation toolbar
        # self.toolbar = NavigationToolbar(self.canvas, self.plotWidget, False)

        # remove subplots action (might be useful in the future)
        # actions = self.toolbar.actions()
        # self.toolbar.removeAction(actions[7])
        # self.plotLayout.addWidget(self.toolbar)

    def start(self):
        print("Starting MRI_SE_Widget")

        # send 2 as signal to start MRI_SE_Widget
        gsocket.write(struct.pack('<I', 2))

        # enable/disable GUI elements
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.gradOffset_x.setEnabled(True)
        self.gradOffset_y.setEnabled(True)
        self.gradOffset_z.setEnabled(True)
        self.gradOffset_z2.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.saveShimButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        self.zoomCheckBox.setEnabled(True)
        self.peakWindowCheckBox.setEnabled(True)

        self.cycAcqBtn.setEnabled(False)
        self.cyclesValue.setEnabled(False)

        # setup global socket for receive data
        gsocket.readyRead.connect(self.read_data)

        # send the sequence to the backend
        ass = Assembler()
        seq_byte_array = ass.assemble(self.seq_filename)
        print(len(seq_byte_array))
        gsocket.write(struct.pack('<I', len(seq_byte_array)))
        gsocket.write(seq_byte_array)

        self.load_shim()
        self.idle = False

    def stop(self):
        self.idle = True
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.gradOffset_z2.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.zoomCheckBox.setEnabled(False)
        self.peakWindowCheckBox.setEnabled(False)
        self.cycAcqBtn.setEnabled(False)
        self.cyclesValue.setEnabled(False)
        # Disconnect global socket
        # if (gsocket.readyRead.isSignalConnected()):
        gsocket.readyRead.disconnect()

    def set_freq(self, freq):
        print("\tSetting frequency.")
        parameters.set_freq(freq)
        gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * freq)))
        # 2^28 = 268,435,456 for frequency setting
        if not self.idle:
            print("\tAcquiring data.")

    def acquire(self):
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
        print("Acquiring data")

    def set_at(self, at):
        print("\tSetting attenuation.")
        # at = round(at/0.25)*4
        parameters.set_at(at)
        gsocket.write(struct.pack('<I', 3 << 28 | int(at/0.25)))
        if not self.idle:
            print("\tAquiring data.")

    '''
    def averaging(self):

        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.gradOffset_z2.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.cycAcqBtn.setEnabled(False)
        self.cyclesValue.setEnabled(False)

        cycles = self.cyclesValue.value()
        # set averaging flag to high:
        # moving average is calculated during display data
        self.averageFlag = True

        for i in range(cycles):
            print("\tNew cycle.")
            self.averageCycle = i+1
            gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
            print("\tAveraging Cyce: ", self.averageCycle)
            # Blocks until new data is available for reading, returns true if new data is available for reading
            # Arg "-1" function does not time out, pass msec as int otherwise
            gsocket.waitForReadyRead(100)
            print("\tWait for read finished.")

        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(True)
        self.gradOffset_x.setEnabled(True)
        self.gradOffset_y.setEnabled(True)
        self.gradOffset_z.setEnabled(True)
        self.gradOffset_z2.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.saveShimButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)

        self.cycAcqBtn.setEnabled(True)
        self.cyclesValue.setEnabled(True)

        # Reset averaging flag to false
        self.averageFlag = False
    '''

    def set_grad_offset(self, spinBox):
        if spinBox.objectName() == 'gradOffset_x':
            print("\tSetting grad offset x.")
            offsetX = self.gradOffset_x.value()
            # self.horizontalSlider_x.setValue(offsetX)
            if offsetX > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | offsetX))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | 1 << 20 | -offsetX))
            print("\tAcquiring data.")

        elif spinBox.objectName() == 'gradOffset_y':
            print("\tSetting grad offset y.")
            offsetY = self.gradOffset_y.value()
            # self.horizontalSlider_y.setValue(offsetY)
            if offsetY > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | offsetY))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | 1 << 20 | -offsetY))
            print("\tAcquiring data.")

        elif spinBox.objectName() == 'gradOffset_z':
            print("\tSetting grad offset z.")
            offsetZ = self.gradOffset_z.value()

            if offsetZ > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 3 << 24 | offsetZ))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 3 << 24 | 1 << 20 | -offsetZ))
            print("\tAcquiring data.")

        elif spinBox.objectName() == 'gradOffset_z2':
            print("\tSetting grad offset z2.")
            offsetZ2 = self.gradOffset_z2.value()

            if offsetZ2 > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetZ2))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetZ2))
            print("\tAcquiring data.")

        else:
            print('\tError: set_grad_offset.')
            return

    def save_shim(self):
        parameters.set_grad_offset_x(self.gradOffset_x.value())
        parameters.set_grad_offset_y(self.gradOffset_y.value())
        parameters.set_grad_offset_z(self.gradOffset_z.value())
        parameters.set_grad_offset_z2(self.gradOffset_z2.value())

    def load_shim(self):
        print("\tLoad grad offsets.")
        self.gradOffset_x.valueChanged.disconnect()
        self.gradOffset_y.valueChanged.disconnect()
        self.gradOffset_z.valueChanged.disconnect()
        self.gradOffset_z2.valueChanged.disconnect()
        self.gradOffset_x.setValue(parameters.get_grad_offset_x())
        self.gradOffset_y.setValue(parameters.get_grad_offset_y())
        self.gradOffset_z.setValue(parameters.get_grad_offset_z())
        self.gradOffset_z2.setValue(parameters.get_grad_offset_z2())
        self.gradOffset_x.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_x))
        self.gradOffset_y.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_y))
        self.gradOffset_z.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z))
        self.gradOffset_z2.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z2))

        offsetX = self.gradOffset_x.value()

        if offsetX > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetX))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetX))

        offsetY = self.gradOffset_y.value()

        if offsetY > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetY))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetY))

        offsetZ = self.gradOffset_z.value()

        if offsetZ > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetZ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetZ))

        offsetZ2 = self.gradOffset_z2.value()

        if offsetZ2 > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetZ2))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetZ2))

        if self.idle:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 0<<20 ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1<<20 ))
            print("Acquiring data.")

    def zero_shim(self):
        print("\tZero grad offsets.")
        self.gradOffset_x.valueChanged.disconnect()
        self.gradOffset_y.valueChanged.disconnect()
        self.gradOffset_z.valueChanged.disconnect()
        self.gradOffset_z2.valueChanged.disconnect()
        self.gradOffset_x.setValue(0)
        self.gradOffset_y.setValue(0)
        self.gradOffset_z.setValue(0)
        self.gradOffset_z2.setValue(0)
        self.gradOffset_x.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_x))
        self.gradOffset_y.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_y))
        self.gradOffset_z.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z))
        self.gradOffset_z2.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z2))
        gsocket.write(struct.pack('<I', 2 << 28 | 6 << 24 ))
        print("\tAcquiring data.")

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
        self.axes_top.clear()

        self.axes_top.set_xlabel('frequency [Hz]')
        self.axes_top.set_ylabel('freq. domain')
        self.axes_bottom.set_xlabel('time [ms]')
        self.axes_bottom.set_ylabel('time domain')
        self.axes_top.grid()
        self.axes_bottom.grid()

        self.figure.set_tight_layout(True)

        # Get magnitude, real and imaginary part of data
        data = self.data

        mag = np.abs(data)
        real = np.real(data)
        imag = np.imag(data)

        # Plot the bottom (time domain): display time signal from 0~21ms [0~5250]
        time = 10
        data_idx = int(time * 250)
        mag_t = mag[0:data_idx]
        real_t = real[0:data_idx]
        imag_t = imag[0:data_idx]
        time_axis = np.linspace(0, time, data_idx)

        if self.averageFlag == True:
            # Update average values if flag was set
            self.averageMag = (np.array(self.averageMag) + np.array(mag_t))/self.averageCycle
            self.averageMag = (np.array(self.averageReal) + np.array(real_t))/self.averageCycle
            self.averageMag = (np.array(self.averageImag) + np.array(imag_t))/self.averageCycle
            # Plot average values
            self.curve_bottom = self.axes_bottom.plot(time_axis, self.averageMag, linewidth=1)  # blue
            self.curve_bottom = self.axes_bottom.plot(time_axis, self.averageReal, linewidth=1)  # red
            self.curve_bottom = self.axes_bottom.plot(time_axis, self.averageImag, linewidth=1)  # green
        else:
            # Plot real time signals, if averaging flag was not set
            self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t, linewidth=1)  # blue
            self.curve_bottom = self.axes_bottom.plot(time_axis, real_t, linewidth=1)  # red
            self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t, linewidth=1)  # green

        # Plot the top (frequency domain): use signal from 0.5~20.5ms: first 0.5ms junk
        # update: the junk is already taken care of by the sequence timing
        dclip = data[0:data_idx];
        freqaxis = np.linspace(-125000, 125000, data_idx)  # 2500 points ~ 20ms

        fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))

        if self.averageFlag == True:
            print("\tAveraging data.")
            self.averageData = (np.array(self.averageData) + np.array(fft_mag))/self.averageCycle
            print(self.averageData)
            fft_mag = self.averageData

        # Data Analysis
        # Calculate and display properties of the frequency
        peak_value = round(np.max(fft_mag), 2)
        self.peak.setText(str(peak_value))

        max_value = np.max(fft_mag[int(data_idx/2 - data_idx/10):int(data_idx/2 + data_idx/10)])
        max_index = np.argmax(fft_mag)
        bound_high = max_index
        bound_low = max_index

        while 1:
            if fft_mag[bound_low] < 0.5 * max_value:
                break
            bound_low = bound_low - 1
        while 1:
            if fft_mag[bound_high] < 0.5 * max_value:
                break
            bound_high = bound_high + 1

        # Calculate and set FWHM
        fwhm_value = bound_high - bound_low
        self.fwhm.setText(str(fwhm_value))

        # Plot frequency spectrum with and without zoom
        if not self.zoomCheckBox.isChecked():  # non zoomed
            self.curve_top = self.axes_top.plot(
                freqaxis[int(data_idx / 2 - data_idx / 10):int(data_idx / 2 + data_idx / 10)],
                fft_mag[int(data_idx / 2 - data_idx / 10):int(data_idx / 2 + data_idx / 10)], linewidth=1)
            if self.averageFlag == True:
                print("\tPlot average data.")
                self.curve_top = self.axes_top.plot(
                    freqaxis[int(data_idx / 2 - data_idx / 10):int(data_idx / 2 + data_idx / 10)],
                    self.averageData[int(data_idx / 2 - data_idx / 10):int(data_idx / 2 + data_idx / 10)], linewidth=1)
        else:  # zoomed
            self.curve_top = self.axes_top.plot(
                freqaxis[int(data_idx / 2 - data_idx / 100):int(data_idx / 2 + data_idx / 100)],
                fft_mag[int(data_idx / 2 - data_idx / 100):int(data_idx / 2 + data_idx / 100)], linewidth=1)
            if self.averageFlag == True:
                self.curve_top = self.axes_top.plot(
                    freqaxis[int(data_idx / 2 - data_idx / 100):int(data_idx / 2 + data_idx / 100)],
                    self.averageData[int(data_idx / 2 - data_idx / 100):int(data_idx / 2 + data_idx / 100)], linewidth=1)

        # Calculate the SNR value inside a peak window
        peak_window = fwhm_value*5
        noise_bound_low = int(max_index - peak_window/2)
        noise_bound_high = int(max_index + peak_window/2)

        # Hightlight the peak window
        if self.peakWindowCheckBox.isChecked():

            print("\tPeak window checked.")

            if int(noise_bound_low) >= int(data_idx / 2 - data_idx / 10) and int(noise_bound_high) <= int(data_idx / 2 + data_idx / 10):
                print("\tPeak inside the view.")
                self.curve_top = self.axes_top.plot(freqaxis[noise_bound_low:noise_bound_high], fft_mag[noise_bound_low:noise_bound_high], linewidth=1, linestyle="--")
            elif max_index < int(data_idx / 2 - data_idx / 10):
                print("\tPeak outside the view.")
                self.axes_top.text(freqaxis[int(data_idx/2-data_idx/10)],0.001 ,"<",fontsize=20)
            elif max_index > int(data_idx / 2 + data_idx / 10):
                print("\tPeak outside the view.")
                self.axes_top.text(freqaxis[int(data_idx/2+data_idx/10)],0.001 ,">",fontsize=20)

        # Join noise outside peak window, calculate std. dev. and snr = peak/std.dev.
        noise = np.concatenate((fft_mag[0:noise_bound_low], fft_mag[noise_bound_high:]))
        snr_value = round(peak_value/np.std(noise),2)
        # print("snr_value: ", snr_value)
        self.snr.setText(str(snr_value))

        # Update the figure
        self.canvas.draw()
