#!/usr/bin/env python

# import general packages
import sys
import struct
import time

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
from scipy.optimize import curve_fit
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
MRI_FID_Widget_Form, MRI_FID_Widget_Base = loadUiType('ui/mri_fid_Widget.ui')
Flipangle_Dialog_Form, Flipangle_Dialog_Base = loadUiType('ui/flipangleDialog.ui')

# MRI Lab widget 1: FID
class MRI_FID_Widget(MRI_FID_Widget_Base, MRI_FID_Widget_Form):
    def __init__(self, parent=None):
        super(MRI_FID_Widget, self).__init__(parent)
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start
        self.seq_filename = 'sequence/basic/fid_default.txt'

        self.flipangleTool = FlipangleDialog(self)

        # connect basic GUI signals
        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.openFlipangletoolBtn.clicked.connect(self.open_flipangleDialog)
        self.acquireButton.clicked.connect(self.acquire)

        # setup frequency related GUI
		# don't emit valueChanged signal while typing
        self.freqValue.setKeyboardTracking(False)
        self.atValue.setKeyboardTracking(False)

        self.freqValue.valueChanged.connect(self.set_freq)
        self.atValue.valueChanged.connect(self.set_at)
        self.freqWindowCheckBox = QCheckBox()
        self.zoomCheckBox = QCheckBox('Zoom')
        self.zoomLayout.addWidget(self.zoomCheckBox)
        self.peakWindowCheckBox = QCheckBox('Peak Window')
        self.peakWindowLayout.addWidget(self.peakWindowCheckBox)
        self.center_freq = 0
        self.applyFreqButton.clicked.connect(self.apply_center_freq)

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

        # disable GUI elements at first
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.applyFreqButton.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.gradOffset_z2.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.openFlipangletoolBtn.setEnabled(False)

        # setup buffer and offset for incoming data
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8*self.size)
        self.offset = 0
        self.data = np.frombuffer(self.buffer, np.complex64)

        # Declare global Variables
        self.data_idx = []
        self.mag_t = []
        self.real_t = []
        self.imag_t = []
        self.time_axis = []
        self.dclip = []
        self.freqaxis = []
        self.fft_mag = []

        self.peak_value = 0
        self.max_value = 0
        self.fwhm_value = 0
        self.noise_bound_low = 0
        self.noise_bound_high = 0
        self.snr_value = 0
        self.center_freq = 0

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

    def start(self):
        print("Starting MRI_FID_Widget")

        # send 1 as signal to start MRI_FID_Widget
        gsocket.write(struct.pack('<I', 1))

        # enable/disable GUI elements
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.applyFreqButton.setEnabled(True)
        self.gradOffset_x.setEnabled(True)
        self.gradOffset_y.setEnabled(True)
        self.gradOffset_z.setEnabled(True)
        self.gradOffset_z2.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.saveShimButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        self.openFlipangletoolBtn.setEnabled(True)

        # setup global socket for receive data
        gsocket.setReadBufferSize(8*self.size)
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
        print("Stopping MRI_FID_Widget")

        # send 0 as signal to stop MRI_FID_Widget
        gsocket.write(struct.pack('<I', 0))

        # enable/disable GUI elements
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.applyFreqButton.setEnabled(False)
        self.gradOffset_x.setEnabled(False)
        self.gradOffset_y.setEnabled(False)
        self.gradOffset_z.setEnabled(False)
        self.gradOffset_z2.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.saveShimButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.openFlipangletoolBtn.setEnabled(False)

        # Disconnect global socket
        # gsocket.readyRead.disconnect()

        self.idle = True

    def set_freq(self, freq):
        # Setting frequency without triggering aquisition: parameters.set_freq
        print("Setting frequency.")
        parameters.set_freq(freq)
        gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * freq)))
        # 2^28 = 268,435,456 for frequency setting
        if not self.idle:
            print("\tAcquiring data.")

    def apply_center_freq(self):
        # print(self.center_freq)
        if self.center_freq != 0 :
            self.freqValue.setValue(self.center_freq)
            print("\tCenter frequency applied.")

    def open_flipangleDialog(self):
        self.flipangleTool.show()

    def acquire(self):
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
        print("\tAcquiring data.")

    def set_at(self, at):
        # Setting attenuation without triggering aquisition: parameters.set_at
        print("Setting attenuation.")
        # at = round(at/0.25)*4
        parameters.set_at(at)
        gsocket.write(struct.pack('<I', 3 << 28 | int(at/0.25)))
        if not self.idle:
             print("\tAquiring data.")

    def set_grad_offset(self, spinBox):
        if spinBox.objectName() == 'gradOffset_x':
            print("Setting grad offset x.")
            offsetX = self.gradOffset_x.value()
            # self.horizontalSlider_x.setValue(offsetX)
            if offsetX > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | offsetX))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 1 << 24 | 1 << 20 | -offsetX))
            print("\tAcquiring data.")

        elif spinBox.objectName() == 'gradOffset_y':
            print("Setting grad offset y.")
            offsetY = self.gradOffset_y.value()
            # self.horizontalSlider_y.setValue(offsetY)
            if offsetY > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | offsetY))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 2 << 24 | 1 << 20 | -offsetY))
            print("\tAcquiring data.")

        elif spinBox.objectName() == 'gradOffset_z':
            print("Setting grad offset z.")
            offsetZ = self.gradOffset_z.value()
            # self.horizontalSlider_z.setValue(offsetZ)
            if offsetZ > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 3 << 24 | offsetZ))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 3 << 24 | 1 << 20 | -offsetZ))
            print("\tAcquiring data.")

        elif spinBox.objectName() == 'gradOffset_z2':
            print("Setting grad offset z2.")
            offsetZ2 = self.gradOffset_z2.value()

            if offsetZ2 > 0:
                gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | offsetZ2))
            else:
                gsocket.write(struct.pack('<I', 2 << 28 | 4 << 24 | 1 << 20 | -offsetZ2))
            print("\tAcquiring data.")

        else:
            print('Error: set_grad_offset.')
            return


    def save_shim(self):
        parameters.set_grad_offset_x(self.gradOffset_x.value())
        parameters.set_grad_offset_y(self.gradOffset_y.value())
        parameters.set_grad_offset_z(self.gradOffset_z.value())
        parameters.set_grad_offset_z2(self.gradOffset_z2.value())


    def load_shim(self):
        print("Loading shim.")
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
            print("\tAcquiring data.")


    def zero_shim(self):
        print("Zero shims.")
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
        gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 ))
        print("\tAcquiring data.")

    def read_data(self):
        '''
        size = gsocket.bytesAvailable()
        if size == self.size:
            self.buffer = gsocket.read(8*self.size)
            print(len(self.buffer))

            print("Start processing readout.")
            self.process_readout()
            print("Start analyzing data.")
            self.analytics()
            print("Display data.")
            self.display_data()

        '''
        # Test if buffer can be filled by one line (see code above)
        # print("Reading...")

        # wait for enough data and read to self.buffer
        size = gsocket.bytesAvailable()
        print(size)
        if size <= 0:
            return
        elif self.offset + size < 8 * self.size:
            self.buffer[self.offset:self.offset + size] = gsocket.read(size)
            self.offset += size
            # if the buffer is not complete, return and wait for more
            return
        else:
            print("Finished Readout.")
            self.buffer[self.offset:8 * self.size] = gsocket.read(8 * self.size - self.offset)
            self.offset = 0
            # print("\tBuffer size: ", len(self.buffer))

        print("Start processing readout.")
        self.process_readout()
        print("Start analyzing data.")
        self.analytics()
        print("Display data.")
        self.display_data()

        if self.flipangleTool.acqCount > 0 and self.flipangleTool.centeringFlag == True:
            print(time.ctime())
            time.sleep(self.flipangleTool.acqTimeout)
            print(time.ctime())
            self.flipangleTool.find_Ceter()
        elif self.flipangleTool.acqCount > 0 and self.flipangleTool.attenuationFlag == True:
            print(time.ctime())
            time.sleep(self.flipangleTool.acqTimeout)
            print(time.ctime())
            self.flipangleTool.find_At()

    def process_readout(self):
        # Get magnitude, real and imaginary part of data
        data = self.data
        mag = np.abs(data)
        real = np.real(data)
        imag = np.imag(data)

        time = 20

        self.data_idx = int(time * 250)
        self.mag_t = mag[0:self.data_idx]
        self.real_t = real[0:self.data_idx]
        self.imag_t = imag[0:self.data_idx]
        self.time_axis = np.linspace(0, time, self.data_idx)
        self.dclip = data[0:self.data_idx];
        self.freqaxis = np.linspace(-125000, 125000, self.data_idx)  # 5000 points ~ 20ms
        self.fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(self.dclip))))

        print("\tReadout processed.")

    def analytics(self):

        self.peak_value = round(np.max(self.fft_mag), 2)
        self.peak.setText(str(self.peak_value))

        # Calculate fwhm
        max_value = np.max(self.fft_mag)
        self.max_index = np.argmax(self.fft_mag)
        bound_high = self.max_index
        bound_low = self.max_index

        while 1:
            if self.fft_mag[bound_low] < 0.5 * max_value:
                break
            bound_low = bound_low - 1
        while 1:
            if self.fft_mag[bound_high] < 0.5 * max_value:
                break
            bound_high = bound_high + 1

        self.fwhm_value = bound_high - bound_low
        freq_span = abs(np.min(self.freqaxis))+abs(np.max(self.freqaxis))
        self.fwhm.setText(str(round(self.fwhm_value*freq_span/self.data_idx))+" Hz")

        # Calculate the SNR value inside a peak window
        peak_window = self.fwhm_value*5
        self.noise_bound_low = int(self.max_index - peak_window/2)
        self.noise_bound_high = int(self.max_index + peak_window/2)
        # Join noise outside peak window, calculate std. dev. and snr = peak/std.dev.
        noise = np.concatenate((self.fft_mag[0:self.noise_bound_low], self.fft_mag[self.noise_bound_high:]))
        self.snr_value = round(self.peak_value/np.std(noise),2)
        # print("snr_value: ", snr_value)
        self.snr.setText(str(self.snr_value))

        # Calculate center frequency
        self.center_freq = parameters.get_freq() + ((self.max_index - 5000/2) * 250000 / 5000 ) / 1.0e6
        # 250000 sampling rate, 5000 number of samples for FFT
        self.centerFreq.setText(str(round(self.center_freq, 5)))

        print("\tData analysed.")

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

        # Plot the bottom (time domain): display time signal from 0~21ms [0~5250]
        self.curve_bottom = self.axes_bottom.plot(self.time_axis, self.mag_t, linewidth=1)   # blue
        self.curve_bottom = self.axes_bottom.plot(self.time_axis, self.real_t, linewidth=1)  # red
        self.curve_bottom = self.axes_bottom.plot(self.time_axis, self.imag_t, linewidth=1)  # green
        self.axes_bottom.set_xlabel('time [ms]')

        # Plot the top (frequency domain): use signal from 0.5~20.5ms: first 0.5ms junk
        # update: the junk is already taken care of by the sequence timing
        if not self.zoomCheckBox.isChecked(): # non zoomed
            self.curve_top = self.axes_top.plot(
                self.freqaxis[int(self.data_idx/2 - self.data_idx/10):int(self.data_idx/2 + self.data_idx/10)],
                self.fft_mag[int(self.data_idx/2 - self.data_idx/10):int(self.data_idx/2 + self.data_idx/10)], linewidth=1)
        else: # zoomed
            self.curve_top = self.axes_top.plot(
                self.freqaxis[int(self.data_idx/2 - self.data_idx/100):int(self.data_idx/2 + self.data_idx/100)],
                self.fft_mag[int(self.data_idx/2 - self.data_idx/100):int(self.data_idx/2 + self.data_idx/100)], linewidth=1)
        self.axes_top.set_xlabel('frequency [Hz]')

        # Hightlight the peak window
        if self.peakWindowCheckBox.isChecked():

            print("\tPeak window checked.")

            if int(self.noise_bound_low) >= int(self.data_idx/2 - self.data_idx/10) and int(self.noise_bound_high) <= int(self.data_idx/2 + self.data_idx/10):
                print("\tPeak inside the view.")
                self.curve_top = self.axes_top.plot(self.freqaxis[self.noise_bound_low:self.noise_bound_high], self.fft_mag[self.noise_bound_low:self.noise_bound_high], linewidth=1, linestyle="--")
            elif self.max_index < int(self.data_idx/2 - self.data_idx/10):
                print("\tPeak outside the view.")
                self.axes_top.text(self.freqaxis[int(self.data_idx/2-self.data_idx/10)],0.001 ,"<",fontsize=20)
            elif self.max_index > int(self.data_idx/2 + self.data_idx/10):
                print("\tPeak outside the view.")
                self.axes_top.text(self.freqaxis[int(self.data_idx/2+self.data_idx/10)],0.001 ,">",fontsize=20)

        # Update the figure
        self.canvas.draw()
        print("\tData plot updated.")

#-------------------------------------------------------------------------------

class FlipangleDialog(Flipangle_Dialog_Base, Flipangle_Dialog_Form):
    def __init__(self, parent=None):

        # split tools for finding center frequency and flipangle

        super(FlipangleDialog, self).__init__(parent)
        self.setupUi(self)
        # setup closeEvent
        self.ui = loadUi('ui/flipangleDialog.ui')
        self.ui.closeEvent = self.closeEvent

        # Setup Buttons
        # self.uploadSeq.clicked.connect(self.upload_pulse)
        # self.findCenterBtn.clicked.connect(self.start_find_Center)
        # self.findAtBtn.clicked.connect(self.start_find_At)
        self.startCenterBtn.clicked.connect(self.start_find_Center)
        self.startAtBtn.clicked.connect(self.start_find_At)
        self.confirmAtBtn.clicked.connect(self.at_confirmed)

        # Setup line edit for estimated frequency
        # self.freqEstimation.valueChanged(self.setEstFreqValue())
        self.freqEstimation.setKeyboardTracking(False)

        # Setup line edit as read only
        self.pulsePath.setReadOnly(True)
        self.centerFreqValue.setReadOnly(True)
        self.at90Value.setReadOnly(True)
        self.at180Value.setReadOnly(True)
        self.at180Value.setEnabled(False)

        # Disable/Enable UI elements
        self.uploadSeq.setEnabled(False)
        self.freqEstimation.setEnabled(True)
        self.freqSpan.setEnabled(True)
        self.freqSteps.setEnabled(True)
        self.atStart.setEnabled(True)
        self.atStop.setEnabled(True)
        self.atSteps.setEnabled(True)
        self.timeoutValue.setEnabled(True)

        self.startCenterBtn.setEnabled(True)
        self.startAtBtn.setEnabled(True)
        self.confirmAtBtn.setEnabled(False)

        self.init_var()

        # self.at_values = [15.0, 17.5, 20.0, 22.5, 25.0]
        # self.at_results = []

        self.figure = Figure()
        self.figure.set_facecolor('none')
        self.axes = self.figure.add_subplot()
        self.axes.set_xlabel('Attenuation')
        self.axes.set_ylabel('Peak')
        self.axes.grid()
        self.figure.set_tight_layout(True)
        self.plotWidget = FigureCanvas(self.figure)
        self.plotLayout.addWidget(self.plotWidget)

        self.fid = parent

    '''
    def upload_pulse(self):
            dialog = QFileDialog()
            fname = dialog.getOpenFileName(None, "Import Pulse Sequence", "", "Text files (*.txt)")
            print("\tUploading 90 degree flip sequence to server.")
        try:
            self.send_pulse(fname[0])
            self.uploadSeq.setText(fname[0])
        except IOError as e:
            print("\tError: required txt file doesn't exist.")
            return                print("\tUploaded successfully to server.")
    '''
    def init_var(self):
        self.centeringFlag = False
        self.attenuationFlag = False

        self.acqTimeout = self.timeoutValue.value()/1000
        self.acqCount= 0

        self.centerFreq = 0
        self.centerPeak = 0

        self.at_results = []

        self.freqEstimation.setValue(parameters.get_freq())
        self.freqSpan.setValue(0.60)
        self.freqSteps.setValue(6)
        self.atStart.setValue(16)
        self.atStop.setValue(24)
        self.atSteps.setValue(8)

    def freq_search_init(self):
        center = self.freqEstimation.value()
        span = self.freqSpan.value()
        steps = self.freqSteps.value()
        self.acqTimeout = self.timeoutValue.value()/1000

        self.search_space = np.arange(center-span/2, center+span/2, span/steps)

    def flip_calib_init(self):
        start = self.atStart.value()
        stop = self.atStop.value()
        steps = self.atSteps.value()
        self.acqTimeout = self.timeoutValue.value()/1000

        self.at_values = np.arange(start, stop, (stop-start)/steps)
        self.at_results = []

    def start_find_Center(self):

        self.freqEstimation.setEnabled(False)
        self.freqSpan.setEnabled(False)
        self.freqSteps.setEnabled(False)
        self.startCenterBtn.setEnabled(False)
        self.timeoutValue.setEnabled(False)
        self.startAtBtn.setEnabled(False)
        self.resetFigure()

        self.freq_search_init()
        self.at_results = []

        self.acqCount = 0
        self.centeringFlag = True
        self.find_Ceter()

    def find_Ceter(self):
        if self.fid.peak_value > self.centerPeak:
            # Change peak and center frequency value
            self.centerPeak = self.fid.peak_value
            self.centerFreq = round(self.fid.center_freq, 5)
            # Set up text edit
            self.centerFreqValue.setText(str(round(self.centerFreq,4)))
        if self.acqCount <= len(self.search_space)-1:
            # Continue until all frequencies are aquired
            print("\nAcquisition counter: ", self.acqCount+1,"/",len(self.search_space),":")
            self.centerFreqValue.setText(str(round(self.search_space[self.acqCount],5)))
            self.fid.set_freq(round(self.search_space[self.acqCount],5))
            self.acqCount += 1
        else:
            # Acquisition finished
            self.acqCount = 0
            self.centerFreqValue.setText(str(round(self.centerFreq,4)))
            print("Acquisition for confirmation:")
            self.fid.set_freq(self.centerFreq)

            # Disable/Enable GUI elements
            self.freqEstimation.setEnabled(True)
            self.freqSpan.setEnabled(True)
            self.freqSteps.setEnabled(True)
            self.timeoutValue.setEnabled(True)

            self.startCenterBtn.setEnabled(True)
            self.startAtBtn.setEnabled(True)

            self.centeringFlag = False

    def start_find_At(self):
        print("Center frequency confirmed.")

        self.resetFigure()

        # Disable/Enable GUI elements

        self.atStart.setEnabled(False)
        self.atStop.setEnabled(False)
        self.atSteps.setEnabled(False)
        self.timeoutValue.setEnabled(False)

        self.startCenterBtn.setEnabled(False)
        self.startAtBtn.setEnabled(False)

        self.flip_calib_init()

        self.acqCount = 0
        self.attenuationFlag = True
        self.fid.set_at(self.at_values[self.acqCount])

        self.find_At()

    def find_At(self):
        if self.acqCount > 0:
            self.at_results.append(round(self.fid.peak_value, 2))

            self.axes.plot(self.at_values[self.acqCount-1],self.at_results[self.acqCount-1],'x',color='red')
            self.plotWidget.draw()

        if self.acqCount < len(self.at_values):
            # Continue until all AT values are aquired
            print("Acquisition counter: ", self.acqCount+1,"/",len(self.at_values),":")
            self.fid.set_at(self.at_values[self.acqCount])
            self.acqCount += 1
        else:
            # Disable/Enable GUI elements

            self.atStart.setEnabled(True)
            self.atStop.setEnabled(True)
            self.atSteps.setEnabled(True)
            self.confirmAtBtn.setEnabled(True)
            self.timeoutValue.setEnabled(True)

            self.startCenterBtn.setEnabled(True)
            self.startAtBtn.setEnabled(True)

            self.attenuationFlag = False
            self.acqCount = 0

            # init optional
            # init = [np.max(self.at_results), 1/(self.at_values[-1]-self.at_values[0]), np.min(self.at_results)]
            init = [np.max(self.at_results), 1/15, np.min(self.at_results)]

            try:
                self.fit_x, self.fit_at = self.fit_At(init)
                self.axes.plot(self.fit_x, self.fit_at, linewidth=1, color='red')
                self.plotWidget.draw()
            except:
                print('ERROR: No fit found.')

            self.at90Value.setText(str(np.max(self.at_results)))

    def fit_At(self, init):
        # parameters = sol(func, x, y, init, method)
        params, params_covariance = curve_fit(self.at_func, self.at_values, self.at_results, init, method='lm')
        x = np.arange(self.at_values[0], self.at_values[-1]+1, 0.1)
        fit = self.at_func(x, params[0], params[1], params[2])
        return x, fit

    # Function model for sinus fitting
    def at_func(self, x, a, b, c):
        return abs(a * np.sin(b * x) + c)

    def at_confirmed(self):
        return

    def resetFigure(self):
        # Reset Plot
        self.axes.clear()
        self.axes.set_xlabel('Attenuation')
        self.axes.set_ylabel('Peak')
        self.axes.grid()
        self.figure.set_tight_layout(True)
