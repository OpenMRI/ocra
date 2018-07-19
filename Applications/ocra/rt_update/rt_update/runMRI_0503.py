#!/usr/bin/env python

# import general packages
import sys
import struct
import time

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget, \
    QLabel, QMessageBox, QCheckBox
from PyQt5.uic import loadUiType
from PyQt5.QtCore import QCoreApplication, QRegExp, QTimer
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
from basicpara import parameters


# load .ui files for different pages
Main_Window_Form, Main_Window_Base = loadUiType('ui/mainWindow.ui')
Welcome_Widget_Form, Welcome_Widget_Base = loadUiType('ui/welcomeWidget.ui')
Config_Dialog_Form, Config_Dialog_Base = loadUiType('ui/configDialog.ui')
MRI_FID_Widget_Form, MRI_FID_Widget_Base = loadUiType('ui/mri_fid_Widget.ui')
MRI_SE_Widget_Form, MRI_SE_Widget_Base = loadUiType('ui/mri_se_Widget.ui')
MRI_Proj_Widget_Form, MRI_Proj_Widget_Base = loadUiType('ui/mri_proj_Widget.ui')
MRI_2DImag_Widget_Form, MRI_2DImag_Widget_Base = loadUiType('ui/mri_2dimag_Widget.ui')
MRI_3DImag_Widget_Form, MRI_3DImag_Widget_Base = loadUiType('ui/mri_3dimag_Widget.ui')
MRI_Proj_Rt_Widget_Form, MRI_Proj_Rt_Widget_Base = loadUiType('ui/mri_rt_proj_Widget.ui')


# create global TCP socket
gsocket = QTcpSocket()


# main window
class MainWindow(Main_Window_Base, Main_Window_Form):
    start_flags = [0, 0, 0, 0, 0, 0, 0]

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.init_menu()
        self.stacked_widget = QStackedWidget()
        self.init_stacked_widget()
        self.setWindowTitle('MRI Tabletop')
        self.setWindowIcon(QIcon('ui/image/icon.png'))
        self.popConfigDialog = ConfigDialog()

    def init_menu(self):
        # File menu
        self.actionConfig.triggered.connect(self.config)
        self.actionQuit.triggered.connect(self.quit_application)

        # MRI Lab menu
        self.actionFID.triggered.connect(self.open_mri_fid)
        self.actionSE.triggered.connect(self.open_mri_se)
        self.actionProj.triggered.connect(self.open_mri_proj)
        self.action2DImag.triggered.connect(self.open_mri_2dimag)
        self.action3DImag.triggered.connect(self.open_mri_3dimag)
        self.actionRot.triggered.connect(self.open_mri_rot)

        # Set shortcuts
        self.actionConfig.setShortcut('Ctrl+Shift+C')
        self.actionQuit.setShortcut('Ctrl+Q')

    def init_stacked_widget(self):
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.welcomeWidget = WelcomeWidget()
        self.mriFidWidget = MRI_FID_Widget()
        self.mriSeWidget = MRI_SE_Widget()
        self.mriProjWidget = MRI_Proj_Widget()
        self.mri2DImagWidget = MRI_2DImag_Widget()
        self.mri3DImagWidget = MRI_3DImag_Widget()
        self.mriRotWidget = MRI_Proj_Rt_Widget()
        self.stacked_widget.addWidget(self.welcomeWidget)
        self.stacked_widget.addWidget(self.mriFidWidget)
        self.stacked_widget.addWidget(self.mriSeWidget)
        self.stacked_widget.addWidget(self.mriProjWidget)
        self.stacked_widget.addWidget(self.mri2DImagWidget)
        self.stacked_widget.addWidget(self.mri3DImagWidget)
        self.stacked_widget.addWidget(self.mriRotWidget)
        self.stacked_widget.addWidget(QLabel("Not developed"))
        self.stacked_widget.addWidget(QLabel("Not developed"))

    def config(self):
        self.popConfigDialog.show()

    def quit_application(self):
        quit_choice = QMessageBox.question(self, 'Confirm', 'Do you want to quit?',
                                           QMessageBox.Yes | QMessageBox.No)
        if quit_choice == QMessageBox.Yes:
            sys.exit()
            # QCoreApplication.instance().quit() # same function
        else: pass


    def stop_all(self):
        ''' Call stop functions of all widgets before opening a new one'''
        print("Stopping all acquisition!")
        if (MainWindow.start_flags[1]):
            self.mriFidWidget.stop()
        if (MainWindow.start_flags[2]):
            self.mriSeWidget.stop()
        if (MainWindow.start_flags[3]):
            self.mriProjWidget.stop()
        if (MainWindow.start_flags[4]):
            self.mri2DImagWidget.stop()
        if (MainWindow.start_flags[5]):
            self.mri3DImagWidget.stop()
        if (MainWindow.start_flags[6]):
            # FOR DEBUGGING
            # print("Stopping Widget 6")
            self.mriRotWidget.stop()

    # Start MRI Lab GUIs:
    def open_mri_fid(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(1)
        # self.stacked_widget.setCurrentWidget(???) # not working

        # self.mriProjWidget.stop()
        # self.mri2DImagWidget.stop()

        # update frequency
        self.mriFidWidget.set_freq(parameters.get_freq())
        self.mriFidWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - FID GUI')

    def open_mri_se(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(2)
        # update frequency
        self.mriSeWidget.set_freq(parameters.get_freq())
        self.mriSeWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - SE GUI')

    def open_mri_proj(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(3)
        # update frequency
        self.mriProjWidget.set_freq(parameters.get_freq())
        self.mriProjWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - Projection GUI')

    def open_mri_2dimag(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(4)
        # update frequency
        self.mri2DImagWidget.set_freq(parameters.get_freq())
        self.mri2DImagWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - 2D Image GUI')

    def open_mri_3dimag(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(5)
        # update frequency
        self.mri3DImagWidget.set_freq(parameters.get_freq())
        self.mri3DImagWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - 3D Image GUI')

    def open_mri_rot(self):
        # FOR DEBUGGING
        print("Rotation GUI opened")
        self.stop_all()
        self.stacked_widget.setCurrentIndex(6)
        # update frequency
        self.mriRotWidget.set_freq(parameters.get_freq())
        self.mriRotWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - 1D Rotation GUI')


# configuration dialog
class ConfigDialog(Config_Dialog_Base, Config_Dialog_Form):
    def __init__(self):
        super(ConfigDialog, self).__init__()
        self.setupUi(self)

        # Setup connection to red-pitaya
        self.connectedLabel.setVisible(False)
        self.connectButton.clicked.connect(self.socket_connect)
        gsocket.connected.connect(self.socket_connected)
        # IP address validator
        IP_validator = QRegExp(
            '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)' \
            '{3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
        self.addrValue.setValidator(QRegExpValidator(IP_validator, self.addrValue))

    def socket_connect(self):
        print('Connecting...')
        self.connectButton.setEnabled(False)
        gsocket.connectToHost(self.addrValue.text(), 1001)

    def socket_connected(self):
        print("Connected!")
        self.connectButton.setEnabled(True)
        self.connectedLabel.setVisible(True)


# MRI Lab GUIs:
#   different widgets for different functions

# welcome widget
class WelcomeWidget(Welcome_Widget_Base, Welcome_Widget_Form):
    def __init__(self):
        super(WelcomeWidget, self).__init__()
        self.setupUi(self)
        self.popConfigDialog = ConfigDialog()
        self.configButton.clicked.connect(self.config)

    def config(self):
        self.popConfigDialog.show()

# MRI Lab widget 1: FID
class MRI_FID_Widget(MRI_FID_Widget_Base, MRI_FID_Widget_Form):
    def __init__(self):
        super(MRI_FID_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqValue.setKeyboardTracking(False) # Value is sent only when enter or arrow key pressed
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

    def start(self):
        self.idle = False
        MainWindow.start_flags[1] = 1
        gsocket.write(struct.pack('<I', 1))
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
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
        # Setup global socket for receive data
        # print(100)
        # print(receivers(gsocket.readyRead))
        # print(isSignalConnected(gsocket.readyRead))
        gsocket.readyRead.connect(self.read_data)
        # print(200)
        # print(isSignalConnected(gsocket.readyRead))

    def stop(self):
        self.idle = True
        MainWindow.start_flags[1] = 0
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
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
        # if (gsocket.readyRead.isSignalConnected()):
        gsocket.readyRead.disconnect()

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
        mag = np.abs(data)
        real = np.real(data)
        imag = np.imag(data)

        # Plot the bottom (time domain): display time signal from 0~21ms [0~5250]
        mag_t = mag[0:5250]
        real_t = real[0:5250]
        imag_t = imag[0:5250]
        time_axis = np.linspace(0, 21, 5250)
        self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t)   # blue
        self.curve_bottom = self.axes_bottom.plot(time_axis, real_t)  # red
        self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t)  # green
        self.axes_bottom.set_xlabel('time, ms')

        # Plot the top (frequency domain): use signal from 1~21ms
        dclip = data[250:5250];
        if not self.freqCheckBox.isChecked(): # non zoomed
            freqaxis = np.linspace(-125000, 125000, 1000) # 1000 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            self.curve_top = self.axes_top.plot(freqaxis, fft_mag[2000:3000])
        else: # zoomed
            freqaxis = np.linspace(-1000, 1000, 80) # 80 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            self.curve_top = self.axes_top.plot(freqaxis, fft_mag[2460:2540])
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
        while 1:
          if fft_mag[bound_low] < 0.5 * max_value:
            break
          bound_low = bound_low - 1
        while 1:
          if fft_mag[bound_high] < 0.5 * max_value:
            break
          bound_high = bound_high + 1
        fwhm_value = bound_high - bound_low
        self.fwhm.setText(str(fwhm_value))

# MRI Lab widget 2: Spin Echo (SE)
class MRI_SE_Widget(MRI_SE_Widget_Base, MRI_SE_Widget_Form):
    def __init__(self):
        super(MRI_SE_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqValue.setKeyboardTracking(False) # Value is sent only when enter or arrow key pressed
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

    def start(self):
        self.idle = False
        MainWindow.start_flags[2] = 1
        gsocket.write(struct.pack('<I', 2))
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
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
        # Setup global socket for receive data
        # print(100)
        # print(receivers(gsocket.readyRead))
        # print(isSignalConnected(gsocket.readyRead))
        gsocket.readyRead.connect(self.read_data)
        # print(200)
        # print(isSignalConnected(gsocket.readyRead))

    def stop(self):
        self.idle = True
        MainWindow.start_flags[2] = 0
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
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
        # if (gsocket.readyRead.isSignalConnected()):
        gsocket.readyRead.disconnect()

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
        mag = np.abs(data)
        real = np.real(data)
        imag = np.imag(data)


        ## need to modify
        # # Plot the bottom (time domain): display time signal from 0~21ms [0~5250]
        # mag_t = mag[0:5250]
        # real_t = real[0:5250]
        # imag_t = imag[0:5250]
        # time_axis = np.linspace(0, 21, 5250)
        # self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t)   # blue
        # self.curve_bottom = self.axes_bottom.plot(time_axis, real_t)  # red
        # self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t)  # green
        # self.axes_bottom.set_xlabel('time, ms')

        # Plot the bottom (time domain): display time signal from 0~4ms [0~1000]
        mag_t = mag[0:1000]
        real_t = real[0:1000]
        imag_t = imag[0:1000]
        time_axis = np.linspace(0, 4, 1000)
        self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t)  # blue
        self.curve_bottom = self.axes_bottom.plot(time_axis, real_t)  # red
        self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t)  # green
        self.axes_bottom.set_xlabel('time, ms')

        # Plot the top (frequency domain): use signal from 1~21ms
        # dclip = data[250:5250];
        dclip = data[0:1000];
        if not self.freqCheckBox.isChecked(): # non zoomed
            freqaxis = np.linspace(-125000, 125000, 1000) # 1000 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            # self.curve_top = self.axes_top.plot(freqaxis, fft_mag[2000:3000])
            self.curve_top = self.axes_top.plot(freqaxis, fft_mag)
        else: # zoomed
            freqaxis = np.linspace(-1000, 1000, 80) # 80 points
            fft_mag = abs(np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip))))
            # self.curve_top = self.axes_top.plot(freqaxis, fft_mag[2460:2540])
            self.curve_top = self.axes_top.plot(freqaxis, fft_mag[460:540])
        self.axes_top.set_xlabel('frequency, Hz')

        # Update the figure
        self.canvas.draw()

        # Data Analysis
        # Calculate and display properties of the frequency
        # peak_value = round(np.max(fft_mag), 2)
        # self.peak.setText(str(peak_value))
        # max_value = np.max(fft_mag)
        # max_index = np.argmax(fft_mag)
        # bound_high = max_index
        # bound_low = max_index
        # # print(max_index)
        # while 1:
        #   if fft_mag[bound_low] < 0.5 * max_value:
        #     break
        #   bound_low = bound_low - 1
        # while 1:
        #   if fft_mag[bound_high] < 0.5 * max_value:
        #     break
        #   bound_high = bound_high + 1
        # fwhm_value = bound_high - bound_low
        # self.fwhm.setText(str(fwhm_value))

# MRI Lab widget 3: 1D Projection
class MRI_Proj_Widget(MRI_Proj_Widget_Base, MRI_Proj_Widget_Form):
    def __init__(self):
        super(MRI_Proj_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqValue.setKeyboardTracking(False) # Value is sent only when enter or arrow key pressed
        # self.freqCheckBox = QCheckBox('Zoom')
        # self.checkBoxLayout.addWidget(self.freqCheckBox)
        self.projAxisValue.addItems(['x', 'y', 'z'])
        self.projAxisValue.currentIndexChanged.connect(self.set_proj_axis)
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

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.projAxisValue.setEnabled(False)
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

    def start(self):
        self.idle = False
        MainWindow.start_flags[3] = 1
        gsocket.write(struct.pack('<I', 3))
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.projAxisValue.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        # Setup global socket for receive data
        gsocket.readyRead.connect(self.read_data)

    def stop(self):
        self.idle = True
        MainWindow.start_flags[3] = 0
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.projAxisValue.setEnabled(False)
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

    def acquire(self):
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
        print("Acquiring data")

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

# MRI Lab widget 4: 2D Image
class MRI_2DImag_Widget(MRI_2DImag_Widget_Base, MRI_2DImag_Widget_Form):
    def __init__(self):
        super(MRI_2DImag_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqValue.setKeyboardTracking(False) # Value is sent only when enter or arrow key pressed
        self.acquireButton.clicked.connect(self.acquire)
        self.reconButton.clicked.connect(self.recon)

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
        self.seqType.addItems(['Spin Echo', 'Gradient Echo', 'Turbo Spin Echo'])

        # Imaging parameters
        self.npe.addItems(['32', '64', '128', '256'])
        self.npe.currentIndexChanged.connect(self.set_readout_size)
        self.size1.setText(self.npe.currentText())
        self.size1.setReadOnly(True)

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.reconButton.setEnabled(False)
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
        self.fname = "acq_data"
        self.buffers_received = 0
        self.num_TR = 0  # maybe change name to npe for consistency
        self.npe_idx = 0
        self.seqType_idx = 0


    def start(self):
        self.idle = False
        self.buffers_received = 0
        MainWindow.start_flags[4] = 1
        gsocket.write(struct.pack('<I', 4))
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        # Setup global socket for receive data
        gsocket.readyRead.connect(self.read_data)

    def stop(self):
        self.idle = True
        MainWindow.start_flags[4] = 0
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.reconButton.setEnabled(False)
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
        self.num_TR = int(self.npe.currentText())
        self.npe_idx = self.npe.currentIndex()
        self.seqType_idx = self.seqType.currentIndex()
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24 | self.npe_idx<<4 | self.seqType_idx ))
        print("Acquiring data = {} x {}".format(self.num_TR,self.num_TR))
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
        print("Acquired TR = {}".format(self.buffers_received))
        self.buffers_received = self.buffers_received + 1
        if self.buffers_received == self.num_TR:
            sp.savemat(self.fname, {"acq_data": self.full_data}) # Save the data
            print("Data saved!")
            self.buffers_received = 0
            self.reconButton.setEnabled(True)  # Let the user recon now
            self.freqValue.setEnabled(True)
            self.seqType.setEnabled(True)
            self.npe.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)

    def recon(self):
        data_contents = sp.loadmat(self.fname)
        acq_data = data_contents['acq_data']
        print(np.size(acq_data, 0))
        print(np.size(acq_data, 1))
        print(np.size(acq_data))
        kspace = acq_data[1:self.num_TR+1, 0:750]
        Y = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(kspace)))
        cntr = int(750 / 2 - 5)
        img = np.abs(Y[:, cntr - int(self.num_TR/2-1):cntr + int(self.num_TR/2+1)])
        print(np.size(img,0))
        print(np.size(img,1))
        print(np.size(img))
        plt.figure()
        plt.imshow(img, cmap='gray')
        plt.show()

# MRI Lab widget 5: 3D Image
class MRI_3DImag_Widget(MRI_3DImag_Widget_Base, MRI_3DImag_Widget_Form):
    def __init__(self):
        super(MRI_3DImag_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqValue.setKeyboardTracking(False) # Value is sent only when enter or arrow key pressed
        self.acquireButton.clicked.connect(self.acquire)
        self.reconButton.clicked.connect(self.recon)

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
        self.seqType.addItems(['Spin Echo', 'Gradient Echo', 'Turbo Spin Echo'])

        # Imaging parameters
        self.npe.addItems(['32', '64', '128', '256'])
        self.npe.currentIndexChanged.connect(self.set_readout_size)
        self.npe2.addItems(['8', '16', '32'])
        self.size1.setText(self.npe.currentText())
        self.size1.setReadOnly(True)

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.reconButton.setEnabled(False)
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
        self.fname = "acq_data"
        self.buffers_received = 0
        self.num_TR = 0  # maybe change name to npe for consistency
        self.npe_idx = 0
        self.npe2_idx = 0
        self.seqType_idx = 0


    def start(self):
        self.idle = False
        self.buffers_received = 0
        MainWindow.start_flags[4] = 1
        gsocket.write(struct.pack('<I', 5))
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.acquireButton.setEnabled(True)
        self.loadShimButton.setEnabled(True)
        self.zeroShimButton.setEnabled(True)
        # Setup global socket for receive data
        gsocket.readyRead.connect(self.read_data)

    def stop(self):
        self.idle = True
        MainWindow.start_flags[4] = 0
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.reconButton.setEnabled(False)
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
        self.num_TR = int(self.npe.currentText())
        self.npe_idx = self.npe.currentIndex()
        self.npe2_idx = self.npe2.currentIndex()
        self.seqType_idx = self.seqType.currentIndex()
        gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24 | self.npe2_idx<<8 | self.npe_idx<<4 |
                                  self.seqType_idx ))
        print("Acquiring data = {} x {}".format(self.num_TR,self.num_TR))
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
        print("Acquired TR = {}".format(self.buffers_received))
        self.buffers_received = self.buffers_received + 1
        if self.buffers_received == self.num_TR:
            sp.savemat(self.fname, {"acq_data": self.full_data}) # Save the data
            print("Data saved!")
            self.buffers_received = 0
            self.reconButton.setEnabled(True)  # Let the user recon now
            self.freqValue.setEnabled(True)
            self.seqType.setEnabled(True)
            self.npe.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.acquireButton.setEnabled(True)
            self.loadShimButton.setEnabled(True)
            self.zeroShimButton.setEnabled(True)

    def recon(self):
        pass
        # data_contents = sp.loadmat(self.fname)
        # acq_data = data_contents['acq_data']
        # print(np.size(acq_data, 0))
        # print(np.size(acq_data, 1))
        # print(np.size(acq_data))
        # kspace = acq_data[1:self.num_TR+1, 0:750]
        # Y = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(kspace)))
        # cntr = int(750 / 2 - 5)
        # img = np.abs(Y[:, cntr - int(self.num_TR/2-1):cntr + int(self.num_TR/2+1)])
        # print(np.size(img,0))
        # print(np.size(img,1))
        # print(np.size(img))
        # plt.figure()
        # plt.imshow(img, cmap='gray')
        # plt.show()

# MRI Lab widget 6: 1D Projection with rotation
class MRI_Proj_Rt_Widget(MRI_Proj_Rt_Widget_Base, MRI_Proj_Rt_Widget_Form):
    def __init__(self):

        # FOR DEBUGGING
        print("Init!")

        super(MRI_Proj_Rt_Widget, self).__init__()
        self.setupUi(self)

        self.idle = True  # state variable: True-stop, False-start

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.stop)
        self.freqValue.valueChanged.connect(self.set_freq)
        self.freqValue.setKeyboardTracking(False) # Value is sent only when enter or arrow key pressed
        self.startButton.setEnabled(True)
        self.acquireButton.clicked.connect(self.acquire)

        # Gradient offsets related - ADDED 5/22 TO ENABLE SHIMMING FROM CLIENT
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
        # self.peak.setReadOnly(True)
        # self.fwhm.setReadOnly(True)

        # Setup buffer and offset for incoming data
        self.size = 50000  # total data received (defined by the server code)
        self.buffer = bytearray(8 * self.size)
        self.offset = 0
        self.data = np.frombuffer(self.buffer, np.complex64)
        # print(self.data.size)

        # FOR DEBUGGING
        self.full_data = np.matrix(np.zeros(np.size(self.data)))
        # self.full_data_sum = np.matrix(np.zeros(np.size(self.data)))
        self.fname = "acq_data_06_05_3"
        self.buffers_received = 0
        self.avgs_received = 0

        # Real time projection demo
        # self.dial.valueChanged.connect(self.set_angle)
        # self.dial.setTracking(False) # Send value only when released
        self.angleSpin.valueChanged.connect(self.set_angle_spin)
        self.angleSpin.setKeyboardTracking(False) 
        self.dial.sliderReleased.connect(self.set_angle)
        self.dial.sliderMoved.connect(self.set_angle_disp)
        self.angleDisp.setVisible(False)
        self.maxAngleDisp.setVisible(False)
        self.numAvg.valueChanged.connect(self.set_num_avg)
        self.angle = 0
        self.acq_avgs = 0 # Number of averages acquired
        # self.num_avgs = 20 # Number of averages to acquire
        # self.num_avgs = self.numAvg.value()
        self.num_avgs = 1 # by default
        self.num_TR = 64
        self.data_sum = np.frombuffer(self.buffer, np.complex64)
        # Search demo
        self.max = 0.0
        # self.maxval = 0.0
        self.flag = 0 # flag for imaging
        self.max_angle = 0.0
        self.counter = 0
        self.proj = np.zeros(1000)
        self.TR = 2000 # [ms]
        self.step = 0
        self.timer = QTimer(self)
        # self.timer.timeout.connect(self.bin_search)
        self.searchButton.clicked.connect(self.search_clicked)
        # gsocket.readyRead.connect(self.bin_search)

        # Disable if not start yet
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        # self.projAxisValue.setEnabled(False)
        self.acquireButton.setEnabled(False)
        self.loadShimButton.setEnabled(False)
        self.zeroShimButton.setEnabled(False)

        # Setup plot
        self.figure = Figure()
        self.figure.set_facecolor('none')
        # top and bottom axes: 2 rows, 1 column
        self.axes_top = self.figure.add_subplot(2, 1, 1)
        # self.axes_mid = self.figure.add_subplot(3, 1, 2) # COMMENT OUT FOR POSTER
        self.axes_bottom = self.figure.add_subplot(2, 1, 2)
        # self.axes_bottom = self.figure.add_subplot(3, 1, 3)
        self.canvas = FigureCanvas(self.figure)
        self.plotLayout.addWidget(self.canvas)
        # create navigation toolbar
        # self.toolbar = NavigationToolbar(self.canvas, self.plotWidget, False)
        # remove subplots action (might be useful in the future)
        # actions = self.toolbar.actions()
        # self.toolbar.removeAction(actions[7])
        # self.plotLayout.addWidget(self.toolbar)

    def start(self):
        self.idle = False
        MainWindow.start_flags[6] = 1
        gsocket.write(struct.pack('<I', 6))
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        # self.projAxisValue.setEnabled(True)
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
        # FOR DEBUGGING
        print("Stopping")
        self.idle = True
        MainWindow.start_flags[6] = 0
        gsocket.write(struct.pack('<I', 0))
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        # self.projAxisValue.setEnabled(False)
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

    def set_angle(self, *args):
        ''' Sends the angle to the server '''
        if self.idle: return

        if len(args) == 0:
            value = self.dial.value()  
            # print("Value = {}".format(value))      
            value = (value-90) # So that zero degrees is horizontal
            # value = value-270 # So that zero degrees is horizontal
            if value < 0:
                self.angle = 360 + value # Need positive angle to pack
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
          self.angle = 360 + value # Need positive angle to pack
        else:
          self.angle = value

        # print("Value = {}".format(value))
        self.dial.setValue(value + 90) # dial is offset 90 degrees from spin box for whatever reason
        # self.dial.setValue(value - 90)
        # print("Current angle = {}".format(self.angle))
        # represent this with at least 12 bits, so that we can cover 0 to 360
        gsocket.write(struct.pack('<I', 3<<28 | self.angle ))

    def set_angle_disp(self, value):
        if self.idle: return
        if value < 0:
          angle = 360 + value # Need positive angle to pack
        else:
          angle = value
        self.angleDisp.setVisible(True)
        self.angleDisp.setText(str(angle))

    def set_num_avg(self, value):
        if self.idle: return
        self.num_avgs = int(value)
        print("Number of averages = {}".format(value))
        gsocket.write(struct.pack('<I', 4<<28 | int(value)))

    def acquire(self):
        # gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24))
        gsocket.write(struct.pack('<I', 3<<28 | self.angle ))
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

        current_data = self.data
        self.data_sum = self.data_sum + current_data

        # Record kspace data for 2D image reconstruction
        self.full_data = np.vstack([self.full_data, self.data])
        # self.full_data_sum = np.vstack([self.full_data_sum, self.data_sum])

        if self.flag:
            print("Acquired TR = {}".format(self.buffers_received))
            self.buffers_received = self.buffers_received + 1
        # else:
        self.avgs_received = self.avgs_received + 1

        self.display_data()

        if self.avgs_received == self.num_avgs:
            # sp.savemat(self.fname, {"data_sum": self.full_data_sum,
            #                          "data":self.full_data}) # Save the data
            # print("Data saved!")
            self.avgs_received = 0
            # self.display_data()
            self.data_sum = np.frombuffer(self.buffer, np.complex64) # reset the data


        if self.buffers_received == self.num_TR:
            sp.savemat(self.fname, {"acq_data":self.full_data}) # Save the data
            print("Data saved!")
            self.buffers_received = 0
            self.recon()

    def display_data(self):
        # Clear the plots: bottom-time domain, top-frequency domain
        self.axes_bottom.clear()
        self.axes_bottom.grid()
        # self.axes_mid.clear()
        # self.axes_mid.grid()
        self.axes_top.clear()
        self.axes_top.grid()

        # Get magnitude, real and imaginary part of data
        # data = self.data
        # print("Acquired TR = {}".format(self.buffers_received))
        # self.buffers_received = self.buffers_received + 1
        # if self.buffers_received == self.num_avgs:
        if self.avgs_received == self.num_avgs:
            # print("Averaging data...")
            data = self.data_sum/(self.num_avgs + 1.0)
        else:
            data = self.data
        # mag = np.abs(data)
        # real = np.real(data)
        # imag = np.imag(data)

        mag = np.abs(data)
        real = np.real(data)
        imag = np.imag(data)

        # Plot the top (frequency domain): use signal from 0~4ms
        # dclip = data[0:1000];
        dclip = data[0:1000]
        # dclip = data[0:750]
        freqaxis = np.linspace(-125000, 125000, 1000)
        # freqaxis = np.linspace(-10000, 10000,750)
        fft_data = np.fft.fftshift(np.fft.fft(np.fft.fftshift(dclip)))
        # self.curve_top, = self.axes_top.plot(freqaxis, np.abs(fft_data))
        # self.axes_top.set_xlabel('frequency, Hz')

        # Plot the bottom (time domain): display time signal from 0~4ms [0~1000]
        mag_t = mag[0:1000]
        real_t = real[0:1000]
        imag_t = imag[0:1000]
        time_axis = np.linspace(0, 4, 1000)
        self.curve_bottom = self.axes_bottom.plot(time_axis, mag_t)   # blue
        self.curve_bottom = self.axes_bottom.plot(time_axis, real_t)  # red
        self.curve_bottom = self.axes_bottom.plot(time_axis, imag_t)  # green
        self.axes_bottom.set_xlabel('Time (ms)')

        # self.canvas.draw()

        if self.avgs_received == self.num_avgs:
            # Middle: running average of fft
            fft_avg = self.running_avg(fft_data)
            print(len(fft_avg))
            # fft_avg = fft_data
            # mag_avg = np.abs(fft_avg)
            cntr = int(np.floor(len(fft_avg)/2))
            mag_avg = np.abs(fft_avg)
            mag_avg = mag_avg[cntr - 100: cntr+100]
            # print(len(mag_avg))
            # mag_avg = mag_avg[]
            # freqaxis_avg = np.linspace(-125000, 125000, len(mag_avg))
            freqaxis_avg = np.linspace(-10000, 10000,len(mag_avg))
            # freqaxis_avg = np.linspace(-10000, 10000,len(mag_avg))
            # self.curve_mid, = self.axes_mid.plot(freqaxis_avg, mag_avg) # COMMENT OUT FOR POSTER
            self.curve_top = self.axes_top.plot(freqaxis_avg, mag_avg)
            # self.curve_mid, = self.axes_mid.plot(freqaxis, np.abs(fft_data))
            self.axes_top.set_xlabel('Frequency (Hz)')
            # self.axes_mid.set_xlabel('Frequency (Hz)')

            # set the proj attribute
            self.proj = mag_avg

            # FOR DEBUGGING
            maxind = np.argmax(self.proj)
            maxval = self.proj[maxind]
            print("maxval = {}".format(maxval))
            print("")
            self.maxval = maxval


        # Update the figure
        self.canvas.draw()


    def running_avg(self, x):
        # N = 10 # number of points to average over
        N = 5
        # N = 2 
        avg = np.convolve(x, np.ones((N,))/N, mode='valid')
        return avg

    def search_clicked(self):

        # Parameters
        self.max_angle = 0.0
        self.max = 0.0
        self.counter = 0
        self.angle = 0
        maxval = 0
        self.step = 30 
        self.searchButton.setEnabled(False)
        self.acquireButton.setEnabled(False)

        # if self.searchButton.text() == "Find angle":        
        #     self.bin_search()
        #     self.timer.timeout.connect(self.bin_search)
        #     # self.timer.start(self.TR)
        #     # FOR DEBUGGING
        #     # self.timer.start(3000)
        #     # self.timer.start(2000)
        #     self.timer.start(900)

        # else:
        #     # Acquire a 2D image
        #     # FOR DEBUGGIGN
        #     self.searchButton.setEnabled(True)
        #     self.flag = 1
        #     gsocket.write(struct.pack('<I', 5<<28 | self.angle ))

        self.searchButton.setEnabled(True)
        self.flag = 1
        self.angle = 300
        gsocket.write(struct.pack('<I', 5<<28 | self.angle ))

    def bin_search(self):

        # FOR DEBUGGING
        # self.angle = 0
        # gsocket.write(struct.pack('<I', 5<<28 | self.angle ))
        self.angle = 300
        self.searchButton.setText("Acquire image")


        # tolerance = 2 # degrees
        # # maxval = self.maxval

        # maxind = np.argmax(self.proj)
        # maxval = self.proj[maxind]
        # print("Max val = {}".format(maxval))
        # print("Max = {}".format(self.max))
        # print("Step size = {}".format(self.step))
        # # print("Max ind = {}".format(maxind))
        # print("")

        # # step_sizes = [40, 20, 10, 5, 4, 3, 2, 1]
        # # step_sizes = [30, 20, 10, 5, 4, 3, 2, 1]
        # # step_sizes = [20, 10, 5, 4, 3, 2, 1]
        # step_sizes = [30, 20, 10, 5, 4, 3, 2, 1]
        # # self.step = step_sizes[self.counter]
        # error = 0.01
        # # if maxval > self.max + error or self.max - error <= maxval <= self.max + error:
        # # if maxval > self.max + error:
        # if maxval > self.max:
        # # if maxval - self.max > 0.02: # take a big step
        #     # increment angle by step
        #     self.max = maxval
        #     self.max_angle = self.angle
        #     self.angle += self.step
        #     # self.angle += 20
            
        # # elif maxval < self.max - error:
        # # elif maxval - self.max < 0.02:
        # elif maxval < self.max:
        #     # We have overshot
        #     # if self.counter <= len(step_sizes):
        #     if self.counter < len(step_sizes):
        #         # self.counter += 1
        #         self.step = step_sizes[self.counter]
        #         self.angle -= self.step
        #         # self.angle -= 5
        #         self.counter += 1
        #         # FOR DEBUGGING
        #         # print("Counter = {}".format(self.counter))

        # # elif self.max - error <= maxval <= self.max + error:
        # if self.step <= tolerance:
        #     print("Max angle is {}".format(self.max_angle))
        #     print("Max value is {}".format(self.max))
        #     # self.set_angle(self.max_angle)
        #     # Set the angle to be 90 degrees from the max angle
        #     if self.max_angle - 90 < 0:
        #         self.set_angle(self.max_angle - 90 + 360)
        #     else:
        #         self.set_angle(self.max_angle - 90)
        #     self.maxAngleDisp.setText(str(self.max_angle))
        #     self.timer.timeout.disconnect(self.bin_search)
            
        #     # Take a 2D image
        #     # self.flag = 1
        #     # gsocket.write(struct.pack('<I', 5<<28 | self.angle ))
        #     # self.buffers_received = 0
        #     # Allow the user to take an image
        #     self.searchButton.setText("Acquire image")
        #     self.searchButton.setEnabled(True)
        #     self.maxAngleDisp.setVisible(True)

        #     # # Reset parameters
        #     self.counter = 0
        #     self.max_angle = 0.0
        #     self.max = 0.0
        #     # # self.step = step_sizes[0]
        #     # self.step = 30
        #     return

        #     # else:
        #     #     # self.counter += 1
        #     #     # self.angle += 3
        #     #     # add some randomness to shake it out of its place
        #     #     self.angle += np.random.randint(-3,3)


        # print("Angle = {}".format(self.angle))
        # if self.angle < 0:
        #     self.angle = self.angle + 360 # make it positive
        # self.set_angle(self.angle)        

    def recon(self):
        data_contents = sp.loadmat(self.fname)
        acq_data = data_contents['acq_data']
        print(np.size(acq_data, 0))
        print(np.size(acq_data, 1))
        print(np.size(acq_data))
        # kspace = acq_data[1:self.num_TR+1, 0:750]
        kspace = acq_data[1:self.num_TR+1, 0:640]
        Y = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(kspace)))
        # cntr = int(750 / 2 - 5)
        cntr = int(640/2 - 5)
        img = np.abs(Y[:, cntr - int(self.num_TR/2-1):cntr + int(self.num_TR/2+1)])
        # print(np.size(img,0))
        # print(np.size(img,1))
        # print(np.size(img))
        plt.figure()
        plt.imshow(img, cmap='gray')
        plt.show()





# run
def run():
    # parameters = BasicParameter()
    app = QApplication(sys.argv)
    MRILab = MainWindow()
    MRILab.show()
    sys.exit(app.exec_())


# main function
if __name__ == '__main__':
    run()
