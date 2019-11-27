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
MRI_2DImag_Widget_Form, MRI_2DImag_Widget_Base = loadUiType('ui/mri_2dimag_Widget.ui')


# MRI Lab widget 5: 2D Image
class MRI_2DImag_Widget(MRI_2DImag_Widget_Base, MRI_2DImag_Widget_Form):
    def __init__(self):
        super(MRI_2DImag_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        # setup basic GUI
        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.acquireButton.clicked.connect(self.acquire)
        # self.enterFlipangleBtn.clicked.connect(self.openFlipangleDialog)
        self.progressBar.setValue(0)

        # setup gradient offsets related GUI
        self.loadShimButton.clicked.connect(self.load_shim)
        self.zeroShimButton.clicked.connect(self.zero_shim)
        self.shim_x.setText(str(parameters.get_grad_offset_x()))
        self.shim_y.setText(str(parameters.get_grad_offset_y()))
        self.shim_z.setText(str(parameters.get_grad_offset_z()))
        self.shim_z2.setText(str(parameters.get_grad_offset_z2()))
        self.shim_x.setReadOnly(True)
        self.shim_y.setReadOnly(True)
        self.shim_z.setReadOnly(True)
        self.shim_z.setReadOnly(True)

        # setup sequence type
        self.seqType.addItems(['Spin Echo', 'Gradient Echo',
                               'SE (slice)', 'GRE (slice)',
                               'Turbo Spin Echo',
                               'EPI', 'EPI (grad_y off)',
                               'Spiral'])
        # self.seqType.currentIndexChanged.connect(self.seq_type_customized_display)
        self.etlComboBox.addItems(['2', '4', '8', '16', '32'])
        self.etlLabel.setVisible(False)
        self.etlComboBox.setVisible(False)
        self.uploadSeqButton.clicked.connect(self.upload_seq)

        # setup imaging parameters
        self.npe.addItems(['4', '8', '16', '32', '64', '128', '256', '384', '512', '640', '768', '1024'])
        # self.npe.currentIndexChanged.connect(self.set_readout_size)
        # self.size1.setText(self.npe.currentText())
        # self.size1.setReadOnly(True)

        # disable GUI elements at first
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.uploadSeqButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.enterFlipangleBtn.setEnabled(False)

        # setup buffer and offset for incoming data
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8 * self.size)
        self.offset = 0
        self.data = np.frombuffer(self.buffer, np.complex64)

        # setup display
        # display 1: image
        self.figure = Figure()
        self.figure.set_facecolor('whitesmoke')
        self.figure.set_tight_layout(True)

        # Large image view 1 row, 1 column
        self.axes_image = self.figure.add_subplot(111)
        self.axes_image.axis('off')

        self.canvas = FigureCanvas(self.figure) # canvas = image
        self.imageLayout.addWidget(self.canvas)
        # create navigation toolbar
        # self.toolbar = NavigationToolbar(self.canvas, self.imageWidget, False)
        # self.imageLayout.addWidget(self.toolbar)

        # display 2: real time signals
        self.figure2 = Figure()
        self.figure2.set_facecolor('none')
        self.figure2.set_tight_layout(True)

        # Real time signal view with 2 rows, 1 column
        self.axes_top = self.figure2.add_subplot(2, 1, 1)
        self.axes_bottom = self.figure2.add_subplot(2, 1, 2)

        self.axes_top.set_xlabel('frequency [Hz]')
        self.axes_bottom.set_xlabel('time [ms]')
        self.axes_top.set_ylabel('freq. domain')
        self.axes_bottom.set_ylabel('time domain')
        self.axes_top.grid()
        self.axes_bottom.grid()

        self.canvas2 = FigureCanvas(self.figure2) # canvas2 = real time
        self.plotLayout.addWidget(self.canvas2)
        # create navigation toolbar
        # self.toolbar2 = NavigationToolbar(self.canvas2, self.plotWidget, False)
        # self.plotLayout.addWidget(self.toolbar2)

        # Acquire image
        self.full_data = np.matrix(np.zeros(np.size(self.data)))
        self.fname = "acq_data"
        self.buffers_received = 0
        self.images_received = 0
        self.num_pe = 0
        self.num_TR = 0  # num_TR = num_pe/etl (echo train length)
        self.etl = 2
        self.etl_idx = 0
        self.npe_idx = 0
        self.seqType_idx = 0
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
        print("Starting MRI_2DImag_Widget")

        # send 5 as signal to start MRI_2DImag_Widget
        gsocket.write(struct.pack('<I', 5))

        # enable/disable GUI elements
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.uploadSeqButton.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        # self.enterFlipangleBtn.setEnabled(True)

        # setup global socket for receive data
        gsocket.readyRead.connect(self.read_data)

        self.load_shim()
        self.idle = False


    def stop(self):
        print("Stopping MRI_2DImag_Widget")

        # self.uploadSeq.setText('none')

        # send 0 as signal to stop MRI_2DImag_Widget
        gsocket.write(struct.pack('<I', 0))

        # enable/disable GUI elements
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.uploadSeqButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.enterFlipangleBtn.setEnabled(False)

        # Disconnect global socket
        gsocket.readyRead.disconnect()

        self.idle = True

        self.axes_image.clear()
        self.axes_image.axis('off')
        self.figure.set_tight_layout(True)
        self.axes_bottom.clear()
        self.axes_top.clear()
        self.figure2.set_tight_layout(True)
        self.canvas.draw()
        self.canvas2.draw()

        self.progressBar.setValue(0)

        # Reset buffer


    def set_freq(self, freq):
        print("\tSetting frequency")
        parameters.set_freq(freq)
        gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * freq)))
        # 2^28 = 268,435,456 for frequency setting
        if not self.idle:
            print("Acquiring data")


    # def set_readout_size(self):
    #     self.size1.setText(self.npe.currentText())


    def upload_seq(self):
        ''' Takes an input text file, compiles it, and sends it to the server as machine code '''
        # Open a Dialog box to take the file
        dialog = QFileDialog()
        fname = dialog.getOpenFileName(None, "Import Pulse Sequence", "", "Text files (*.txt)")
        # returns a tuple, fname[0] is filename(including path), fname[1] is file type
        print("Uploading sequence to server")
        try:
            self.send_pulse(fname[0])
            self.uploadSeq.setText(fname[0])
        except IOError as e:
            print("Error: required txt file doesn't exist")
            return
        print("Uploaded successfully to server")


    def send_pulse(self, inp_file):
        ''' Sends the pulse sequence to the server '''
        # write a 3 to signal that the button has been pushed
        gsocket.write(struct.pack('<I', 3 << 28))
        ass = Assembler()
        btye_array = ass.assemble(inp_file)
        print("Byte array = {}".format(btye_array))
        print("Length of byte array = {}".format(len(btye_array)))
        gsocket.write(btye_array)
        print("Sent byte array")

    def seq_type_customized_display(self):
        self.seqType_idx = self.seqType.currentIndex()
        if self.seqType_idx != 4: # not tse
            self.etlLabel.setVisible(False)
            self.etlComboBox.setVisible(False)
        else: # tse
            self.etlLabel.setVisible(True)
            self.etlComboBox.setVisible(True)
        if self.seqType_idx in [5, 6, 7]: # epi or spiral
            # self.size1.setEnabled(False)
            self.npe.setEnabled(False)
        else:
            # self.size1.setEnabled(True)
            self.npe.setEnabled(True)

    def acquire(self):
        if self.uploadSeq.text() == 'none':
            QMessageBox.warning(self, 'Warning', 'No sequence has been uploaded!',
                                QMessageBox.Cancel)
            return

        # clear the plots, need to call draw() to update

        self.axes_image.clear()
        self.axes_image.axis('off')
        self.figure.set_tight_layout(True)
        self.canvas.draw()

        # Disables k-space representation
        # self.axes_k_amp.clear()
        # self.axes_k_pha.clear()

        # ---- display k-space ---- #
        #plt.show()
        #self.kspace_ax = plt.gca()


        self.axes_bottom.clear()
        self.axes_top.clear()
        self.figure2.set_tight_layout(True)
        self.canvas2.draw()

        self.progressBar.setValue(0)

        self.num_pe = int(self.npe.currentText())
        self.npe_idx = self.npe.currentIndex()
        self.seqType_idx = self.seqType.currentIndex()
        self.etl = int(self.etlComboBox.currentText())
        self.etl_idx = self.etlComboBox.currentIndex()

        if self.seqType_idx != 4: # not tse
            self.num_TR = self.num_pe
        else:  # tse
            self.num_TR = int(self.num_pe / self.etl)

        self.kspace_full = np.matrix(np.zeros((self.num_TR, 50000), dtype=np.complex64))

        crop_size = int(self.num_pe / 64 * self.crop_factor)
        self.kspace = np.matrix(np.zeros((self.num_pe, crop_size), dtype = np.complex64))
        self.k_amp = np.matrix(np.zeros((self.num_pe, self.num_pe*2)))
        self.k_pha = np.matrix(np.zeros((self.num_pe, self.num_pe*2)))
        self.tse_kspace = np.matrix(np.zeros((self.num_pe, crop_size), dtype = np.complex64))
        self.tse_k_amp = np.matrix(np.zeros((self.num_pe, self.num_pe * 2)))
        self.tse_k_pha = np.matrix(np.zeros((self.num_pe, self.num_pe * 2)))
        self.img = np.matrix(np.zeros((self.num_pe,self.num_pe)))

        # signal to the server and start acquisition
        if self.seqType_idx != 4: # not tse
            gsocket.write(
                struct.pack('<I', 2 << 28 | 0 << 24 | self.npe_idx << 4 | self.seqType_idx))
            print("Acquiring data = {} x {}".format(self.num_pe, self.num_pe))

        else:  # tse
            gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24 | self.etl_idx << 8 | self.npe_idx << 4 | self.seqType_idx))
            print("Acquiring data = {} x {} echo train length = {}".format(self.num_pe, self.num_pe, self.etl))

        # enable/disable GUI elements
        self.freqValue.setEnabled(False)
        self.seqType.setEnabled(False)
        self.npe.setEnabled(False)
        self.etlComboBox.setEnabled(False)
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.uploadSeqButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)
        self.enterFlipangleBtn.setEnabled(False)


    def load_shim(self):
        print("\tLoad grad offsets")
        self.shim_x.setText(str(parameters.get_grad_offset_x()))
        self.shim_y.setText(str(parameters.get_grad_offset_y()))
        self.shim_z.setText(str(parameters.get_grad_offset_z()))
        self.shim_z2.setText(str(parameters.get_grad_offset_z2()))

        offsetX = int(self.shim_x.text())
        if offsetX > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetX))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetX))

        offsetY = int(self.shim_y.text())
        if offsetY > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetY))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetY))

        offsetZ = int(self.shim_z.text())
        if offsetZ > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetZ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetZ))

        offsetZ2 = int(self.shim_z2.text())
        if offsetZ2 > 0:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | offsetZ2))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1 << 20 | -offsetZ2))

        if self.idle:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 0<<20 ))
        else:
            gsocket.write(struct.pack('<I', 2 << 28 | 5 << 24 | 1<<20 ))
            print("Acquiring data")


    def zero_shim(self):
        print("\tZero grad offsets")
        self.shim_x.setText(str(0))
        self.shim_y.setText(str(0))
        self.shim_z.setText(str(0))
        self.shim_z2.setText(str(0))
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
        self.axes_top.clear()
        self.axes_bottom.clear()
        # Reset the plots
        self.axes_top.set_xlabel('frequency [Hz]')
        self.axes_bottom.set_xlabel('time [ms]')
        self.axes_top.set_ylabel('freg. domain')
        self.axes_bottom.set_ylabel('time domain')
        self.axes_top.grid()
        self.axes_bottom.grid()

        self.figure2.set_tight_layout(True)

        # Get magnitude, real and imaginary part of data
        data = self.data
        mag = np.abs(data)
        pha = np.angle(data)
        real = np.real(data)
        imag = np.imag(data)

        if self.seqType_idx in [0, 1]: # SE GRE
            time = 4 # ms
        elif self.seqType_idx in [2, 3]: # SE GRE (slice selective)
            time = 20
        else: # other
            time = 45 # ms
        data_idx = time * 250 # sample rate is 250kHz, therefore 250 samples per ms
        mag_t = mag[0:data_idx]
        real_t = real[0:data_idx]
        imag_t = imag[0:data_idx]
        time_axis = np.linspace(0, time, data_idx)

        self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t, linewidth=0.5)   # blue
        self.curve_bottom = self.axes_bottom.plot(time_axis, real_t, linewidth=0.5)  # red
        self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t, linewidth=0.5)  # green

        # Plot the top (frequency domain)
        if self.seqType_idx in [0, 1]: # SE GRE
            dclip = data[0:1000]    # use signal from 0~4ms
            freqaxis = np.linspace(-125000, 125000, 1000)
        if self.seqType_idx in [2, 3]: # SE GRE (slice selective)
            dclip = data[0:1000]    # use signal from 0~4ms
            freqaxis = np.linspace(-125000, 125000, 1000)
        elif self.seqType_idx == 4: # tse
            dclip = data[4500:5500]    # use signal from 18~22ms (second echo)
            freqaxis = np.linspace(-125000, 125000, 1000)
        elif self.seqType_idx in [5, 6]: # epi
            print('epi')
            dclip = data[4950:5050] # display only the central peak
            freqaxis = np.linspace(-125000, 125000, 100)
            # dclip = data[4000:6000]
            # freqaxis = np.linspace(-125000, 125000, 2000)
        elif self.seqType_idx == 7: # spiral
            print('spiral')
            dclip = data[1250:5250]
            freqaxis = np.linspace(-125000, 125000, 4000)

        fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
        self.curve_top, = self.axes_top.plot(freqaxis, fft_mag, linewidth=0.5)

        # Update the figure
        self.canvas2.draw()


        if self.seqType_idx in [0, 1, 2, 3, 4]: # not single shot sequence such as epi and spiral
            self.kspace_full[self.buffers_received, :] = self.data
            self.full_data = np.vstack([self.full_data, self.data])

            if self.seqType_idx != 4:  # not tse
                # display kspace
                self.k_amp[self.buffers_received, :] = mag[self.kspace_center - self.num_pe
                                                           : self.kspace_center + self.num_pe]
                self.k_pha[self.buffers_received, :] = pha[self.kspace_center - self.num_pe
                                                           : self.kspace_center + self.num_pe]
                k_amp_1og10 = np.log10(self.k_amp)

                # Disabled k-space representation:
                # self.axes_k_amp.imshow(k_amp_1og10, cmap='plasma')
                # self.axes_k_amp.set_title('k-space amplitude (log10)')

                # self.axes_k_pha.imshow(self.k_amp, cmap='plasma')
                # self.axes_k_pha.set_title('k-space amplitude')

                # self.axes_k_pha.imshow(self.k_pha, cmap='plasma')
                # self.axes_k_pha.set_title('k-space phase')
                # self.canvas2.draw()

                #self.kspace_ax.imshow(k_amp_1og10, cmap='plasma')
                #plt.draw()
                #plt.pause(0.0000001)

                # display image
                crop_size = int(self.num_pe / 64 * self.crop_factor)
                half_crop_size = int(crop_size / 2)
                # cntr = int(crop_size * 0.975 / 2)
                cntr = int(crop_size * 0.99 / 2)
                # cntr = int(crop_size * 0.96 / 2)
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
                # self.axes_image.set_title('image')

                self.canvas.draw()

            else: # tse
                # display kspace
                TE1 = 10 * 250  # int(9.992*250) #10*250 # 10 ms
                TE2 = 20 * 250  # int(19.984*250) #20*250 # 20 ms
                self.k_amp[self.buffers_received * 2, :] = mag[TE1 - self.num_pe
                                                               : TE1 + self.num_pe]
                self.k_amp[self.buffers_received * 2 + 1, :] = mag[TE2 - self.num_pe
                                                                   : TE2 + self.num_pe]
                # self.k_amp[self.buffers_received * 2 + 1, :] = np.flip(mag[TE2 - self.num_pe
                #                                                    : TE2 + self.num_pe],0)

                self.k_pha[self.buffers_received * 2, :] = pha[TE1 - self.num_pe
                                                               : TE1 + self.num_pe]
                self.k_pha[self.buffers_received * 2 + 1, :] = pha[TE2 - self.num_pe
                                                                   : TE2 + self.num_pe]
                # self.k_pha[self.buffers_received * 2 + 1, :] = np.flip(pha[TE2 - self.num_pe
                #                                                    : TE2 + self.num_pe],0)

                k_amp_1og10 = np.log10(self.k_amp)

                # Disabled k-space representation:

                # self.axes_k_amp.imshow(k_amp_1og10, cmap='plasma')
                # self.axes_k_amp.set_title('k-space amplitude (log10)')
                # self.axes_k_pha.imshow(self.k_amp, cmap='plasma')
                # self.axes_k_pha.set_title('k-space amplitude')
                # self.axes_k_pha.imshow(self.k_pha, cmap='plasma')
                # self.axes_k_pha.set_title('k-space phase')
                # self.canvas2.draw()

                # display image
                crop_size = int(self.num_pe / 64 * self.crop_factor)
                half_crop_size = int(crop_size / 2)
                # cntr = int(crop_size * 0.975 / 2)
                # cntr = int(crop_size * 0.985 / 2)
                cntr = int(crop_size * 0.99 / 2)
                # cntr = int(crop_size * 1.0 / 2)
                # cntr = int(crop_size * 0.96 / 2)
                self.tse_kspace[self.buffers_received * 2, :] = self.kspace_full[
                                                                self.buffers_received,
                                                                TE1 - half_crop_size: TE1 + half_crop_size]
                self.tse_kspace[self.buffers_received * 2 + 1, :] = self.kspace_full[
                                                                    self.buffers_received,
                                                                    TE2 - half_crop_size: TE2 + half_crop_size]
                # self.tse_kspace[self.buffers_received * 2 + 1, :] = np.flip(self.kspace_full[
                #                   self.buffers_received, TE2 - half_crop_size: TE2 + half_crop_size],0)

                Y = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(self.tse_kspace)))
                img = np.abs(Y[:, cntr - int(self.num_pe / 2 - 1):cntr + int(self.num_pe / 2 + 1)])
                self.img = img
                self.axes_image.imshow(self.img, cmap='gray')
                #self.axes_image.set_title('image')

                self.canvas.draw()

        elif self.seqType_idx in [5, 6]:  # epi
            readout_size = 70
            phase_size = 64
            half_readout_size = int(readout_size/2)
            half_phase_size = int(phase_size / 2)
            center_times = np.arange(4.5, 4.5+0.5*64, 0.5)
            center_idxes = center_times * 250
            kspace = np.zeros((phase_size, readout_size), dtype=np.complex64)
            kspace_odd = np.zeros((half_phase_size, readout_size), dtype=np.complex64)
            kspace_even = np.zeros((half_phase_size, readout_size), dtype=np.complex64)
            for i in range(0,64):
                kspace[i, :] = data[int(center_idxes[i]) - half_readout_size :
                              int(center_idxes[i]) + half_readout_size]
                if i%2:
                    kspace[i, :] = np.flip(kspace[i, :], 0)

            for i in range(0,64):
                if i % 2:
                    kspace_even[int((i-1)/2), :] = kspace[i, :]
                else:
                    kspace_odd[int(i/2), :] = kspace[i, :]

            img = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.fftshift(kspace))))
            img_odd = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.fftshift(kspace_odd))))
            img_even = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.fftshift(kspace_even))))

            # Disabled k-space representation
            # self.axes_k_amp.imshow(img_odd, cmap='gray')
            # self.axes_k_amp.set_title('image recon by odd lines')
            # self.axes_k_pha.imshow(img_even, cmap='gray')
            # self.axes_k_pha.set_title('image recon by even lines')

            self.axes_image.imshow(img, cmap='gray')
            # self.axes_image.set_title('image recon by all lines')

            self.canvas.draw()

            self.images_received += 1
            sp.savemat('epi_' + str(self.images_received),
                       {"acq_data": data})  # Save the data
            print("Data saved!")
            self.buffers_received = 0
            # enable/disable GUI elements
            self.freqValue.setEnabled(True)
            self.seqType.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.uploadSeqButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)
            # self.enterFlipangleBtn.setEnabled(True)
            return

        elif self.seqType_idx == 7: # spiral (recon not included)
            self.images_received += 1
            sp.savemat('spiral_' + str(self.images_received),
                       {"acq_data": data})  # Save the data
            print("Data saved!")
            self.buffers_received = 0
            # enable/disable GUI elements
            self.freqValue.setEnabled(True)
            self.seqType.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.uploadSeqButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)
            # self.enterFlipangleBtn.setEnabled(True)
            return


        self.buffers_received = self.buffers_received + 1

        self.progressBar.setValue(self.buffers_received/self.num_TR*100)
        print("Acquired TR = {}".format(self.buffers_received))
        if self.buffers_received == self.num_TR:
            self.images_received += 1
            sp.savemat(self.fname + '_' + str(self.images_received), {"acq_data": self.full_data}) # Save the data
            print("Data saved!")
            self.buffers_received = 0

            # enable/disable GUI elements
            self.freqValue.setEnabled(True)
            self.seqType.setEnabled(True)
            self.npe.setEnabled(True)
            self.etlComboBox.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.uploadSeqButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)
            self.full_data = np.matrix(np.zeros(np.size(self.data)))
