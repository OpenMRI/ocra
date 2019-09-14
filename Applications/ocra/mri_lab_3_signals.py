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
MRI_Sig_Widget_Form, MRI_Sig_Widget_Base = loadUiType('ui/mri_sig_Widget.ui')


# MRI Lab widget 3: Signals
class MRI_Sig_Widget(MRI_Sig_Widget_Base, MRI_Sig_Widget_Form):
    def __init__(self):
        super(MRI_Sig_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
		
		# don't emit valueChanged signal while typing
        self.freqValue.setKeyboardTracking(False)
        
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqCheckBox = QCheckBox('Zoom')
        self.checkBoxLayout.addWidget(self.freqCheckBox)
        self.acquireButton.clicked.connect(self.acquire)

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
			
		# Don't emit valueChanged signal while typing
        self.gradOffset_x.setKeyboardTracking(False)
        self.gradOffset_y.setKeyboardTracking(False)
        self.gradOffset_z.setKeyboardTracking(False)
		
        self.gradOffset_x.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_x))
        self.gradOffset_y.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_y))
        self.gradOffset_z.valueChanged.connect(lambda: self.set_grad_offset(self.gradOffset_z))
        self.saveShimButton.clicked.connect(self.save_shim)
        self.loadShimButton.clicked.connect(self.load_shim)
        self.zeroShimButton.clicked.connect(self.zero_shim)
        self.peak.setReadOnly(True)
        self.fwhm.setReadOnly(True)

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.seqType.setEnabled(False)
        self.uploadSeqButton.setEnabled(False)
        self.seqButton.setEnabled(False)
        self.horizontalSlider_x.setEnabled(False)
        self.horizontalSlider_y.setEnabled(False)
        self.horizontalSlider_z.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)

        # Sequence Type
        self.seqType.addItems(['Free Induction Decay', 'Spin Echo', 'Gradient Echo',
                               'use uploaded seq'])
        self.uploadSeqButton.clicked.connect(self.upload_seq)
        self.seqType_idx = 0
        self.seqButton.clicked.connect(self.set_seq)
        self.seq_set = 0
        self.default_seq_byte_array = []
        self.upload_seq_byte_array = []


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
        # self.newLayout.addWidget(self.canvas)
        self.plotLayout.addWidget(self.canvas)
        # create navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self.plotWidget, False)
        # remove subplots action (might be useful in the future)
        # actions = self.toolbar.actions()
        # self.toolbar.removeAction(actions[7])
        # self.newLayout.addWidget(self.canvas)
        self.plotLayout.addWidget(self.toolbar)

    def start(self):
        gsocket.write(struct.pack('<I', 3))
        self.load_shim()
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.seqType.setEnabled(True)
        self.uploadSeqButton.setEnabled(True)
        self.seqButton.setEnabled(True)
        gsocket.readyRead.connect(self.read_data)
        self.idle = False


    def stop(self):
        self.idle = True
        self.uploadSeq.setText('none')
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.seqType.setEnabled(False)
        self.uploadSeqButton.setEnabled(False)
        self.seqButton.setEnabled(False)
        self.seq_set = 0
        self.seqButton.setText('confirm sequence')
        self.horizontalSlider_x.setEnabled(False)
        self.horizontalSlider_y.setEnabled(False)
        self.horizontalSlider_z.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        # Disconnect global socket
        gsocket.readyRead.disconnect()


    def set_seq(self):
        if not self.seq_set:
            self.seqType_idx = self.seqType.currentIndex()
            if self.seqType_idx == 3 and self.uploadSeq.text() == 'none':
                QMessageBox.warning(self, 'Warning', 'No sequence has been uploaded!',
                                    QMessageBox.Cancel)
                return

            self.seq_set = 1
            self.seqButton.setText('change sequence')
            self.seqType.setEnabled(False)
            self.uploadSeqButton.setEnabled(False)
            self.horizontalSlider_x.setEnabled(True)
            self.horizontalSlider_y.setEnabled(True)
            self.horizontalSlider_z.setEnabled(True)
            self.gradOffset_x.setEnabled(True)
            self.gradOffset_y.setEnabled(True)
            self.gradOffset_z.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.saveShimButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)

            # write a 3 to signal
            gsocket.write(struct.pack('<I', 3 << 28 | self.seqType_idx))
            if self.seqType_idx == 0:
                self.set_pulse('sequence/sig/fid_sig.txt')
            elif self.seqType_idx == 1:
                if self.para_TE.value() == 10:
                    self.set_pulse('sequence/sig/se_sig.txt')
                else:
                    self.generate_se_seq()
                    self.set_pulse('sequence/sig/se_sig_te.txt')
            elif self.seqType_idx == 2:
                self.set_pulse('sequence/sig/gre_sig.txt')
            elif self.seqType_idx == 3:
                self.send_pulse()

        else:
            self.seq_set = 0
            self.seqButton.setText('confirm sequence')
            self.seqType.setEnabled(True)
            self.uploadSeqButton.setEnabled(True)
            self.horizontalSlider_x.setEnabled(False)
            self.horizontalSlider_y.setEnabled(False)
            self.horizontalSlider_z.setEnabled(False)
            self.gradOffset_x.setEnabled(False)
            self.gradOffset_y.setEnabled(False)
            self.gradOffset_z.setEnabled(False)
            self.acquireButton.setEnabled(False)
            self.saveShimButton.setEnabled(False)
            self.loadShimButton.setEnabled(False)
            self.zeroShimButton.setEnabled(False)


    def upload_seq(self):
        ''' Takes an input text file, compiles it to machine code '''
        dialog = QFileDialog() # open a Dialog box to take the file
        fname = dialog.getOpenFileName(None, "Import Pulse Sequence", "", "Text files (*.txt)")
        # returns a tuple, fname[0] is filename(including path), fname[1] is file type
        inp_file = fname[0]
        print("Uploading sequence to server")
        try:
            ass = Assembler()
            self.upload_seq_byte_array = ass.assemble(inp_file)
            self.uploadSeq.setText(inp_file)
        except IOError as e:
            print("Error: required txt file doesn't exist")
            return
        print("Uploaded successfully to server")

    def send_pulse(self):
        ''' Sends the uploaded pulse sequence to the server '''
        gsocket.write(self.upload_seq_byte_array)
        return

    def set_pulse(self, inp_file):
        ''' Sends the default pulse sequence to the server '''
        ass = Assembler()
        self.default_seq_byte_array = ass.assemble(inp_file)
        gsocket.write(self.default_seq_byte_array)
        return

    def set_freq(self, freq):
        print("\tSetting frequency")
        parameters.set_freq(freq)
        gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * freq)))
        # 2^28 = 268,435,456 for frequency setting
        if not self.idle:
            print("Acquiring data")

    def acquire(self):
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
        print("Acquiring data")

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
            print("\tSetting grad offset x")
            offsetX = self.gradOffset_x.value()
            self.horizontalSlider_x.setValue(offsetX)
            if offsetX > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | offsetX))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | 1 << 20 | -offsetX))
            print("Acquiring data")
        elif spinBox.objectName() == 'gradOffset_y':
            print("\tSetting grad offset y")
            offsetY = self.gradOffset_y.value()
            self.horizontalSlider_y.setValue(offsetY)
            if offsetY > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | offsetY))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | 1 << 20 | -offsetY))
            print("Acquiring data")
        elif spinBox.objectName() == 'gradOffset_z':
            print("\tSetting grad offset z")
            offsetZ = self.gradOffset_z.value()
            self.horizontalSlider_z.setValue(offsetZ)
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
        if self.idle:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 0<<20 ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1<<20 ))
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
        # if self.seqType_idx == 3 : # for making the video TSE
        #     data[675:725] = 0
        #     data[2175:2225] = 0
        #     data[3675:3725] = 0
        #     data[5175:5225] = 0

        mag = np.abs(data)
        real = np.real(data)
        imag = np.imag(data)

        # Plot the bottom (time domain): display time signal from 0~time ms [0~time*250]
        if self.seqType_idx == 0 :
            time = 20.4
        elif self.seqType_idx == 1 :
            time = 30
        elif self.seqType_idx == 2 :
            time = 5
        elif self.seqType_idx == 3 :
            time = 30 # 30 for CPMG
        data_idx = int(time * 250)
        mag_t = mag[0:data_idx]
        real_t = real[0:data_idx]
        imag_t = imag[0:data_idx]
        time_axis = np.linspace(0, time, data_idx)
        self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t)   # blue
        self.curve_bottom = self.axes_bottom.plot(time_axis, real_t)  # red
        self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t)  # green
        self.axes_bottom.set_xlabel('time, ms')

        # Plot the top (frequency domain)
        if self.seqType_idx == 0: # FID
            dclip = data[100:5100];
            freqaxis = np.linspace(-125000, 125000, 5000)  # 5000 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            if not self.freqCheckBox.isChecked():  # non zoomed
                self.curve_top = self.axes_top.plot(freqaxis[2000:3000], fft_mag[2000:3000])
            else:  # zoomed
                self.curve_top = self.axes_top.plot(freqaxis[2450:2550], fft_mag[2450:2550])
            self.axes_top.set_xlabel('frequency, Hz')

        elif self.seqType_idx == 1:  # SE
			# the fourier transform is taken on a snippet that is -4ms to + 4ms around the echo
            dclip = data[int((self.para_TE.value()-4)*250):int((self.para_TE.value()+4)*250)]
            freqaxis = np.linspace(-125000, 125000, 2*4*250)  # 2000 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            if not self.freqCheckBox.isChecked():  # non zoomed
                self.curve_top = self.axes_top.plot(freqaxis[500:1500], fft_mag[500:1500])
            else:  # zoomed
                self.curve_top = self.axes_top.plot(freqaxis[950:1050], fft_mag[950:1050])
            self.axes_top.set_xlabel('frequency, Hz')

        elif self.seqType_idx == 2: # GRE
            # Plot the top (frequency domain): use signal from 2~3.6ms: no junk
            dclip = data[500:900];
            freqaxis = np.linspace(-125000, 125000, 400)  # 400 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            if not self.freqCheckBox.isChecked():  # non zoomed
                self.curve_top = self.axes_top.plot(freqaxis, fft_mag)
            else:  # zoomed
                self.curve_top = self.axes_top.plot(freqaxis[150:250], fft_mag[150:250])
            self.axes_top.set_xlabel('frequency, Hz')

        elif self.seqType_idx == 3: # CPMG specific display
            dclip = data[1000:2000];
            freqaxis = np.linspace(-125000, 125000, 1000)  # 1000 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            if not self.freqCheckBox.isChecked():  # non zoomed
                self.curve_top = self.axes_top.plot(freqaxis[0:1000], fft_mag[0:1000])
            else:  # zoomed
                self.curve_top = self.axes_top.plot(freqaxis[450:550], fft_mag[450:550])
            self.axes_top.set_xlabel('frequency, Hz')

        # Update the figure
        self.canvas.draw()

        # Data Analysis
        # Calculate and display properties of the frequency
        peak_value = round(np.max(fft_mag), 2)
        self.peak.setText(str(peak_value))
        max_value = np.max(fft_mag)
        max_index = np.argmax(fft_mag)
        bound_high = max_index
        bound_low = max_index
        # print(max_index)
		
		# TW: Wow, this isn't really code to find the line-width, but hey sometimes this could work (not cool)
        while 1:
          if fft_mag[bound_low] < 0.5 * max_value:
            break
          bound_low = bound_low - 1
        while 1:
          if fft_mag[bound_high] < 0.5 * max_value:
            break
          bound_high = bound_high + 1
        fwhm_value = bound_high - bound_low
        print(fwhm_value)
        self.fwhm.setText(str(fwhm_value))

    def generate_se_seq(self):
        f = open('sequence/sig/se_sig_te.txt', 'r+')
        lines = f.readlines()
        lines[-8] = 'PR 4, ' + str(int(self.para_TE.value()/2 * 1000 - 145)) + '\t// wait&r\n'
        f.close()

        with open('sequence/sig/se_sig_te.txt', "w") as out_file:
            for line in lines:
                out_file.write(line)
