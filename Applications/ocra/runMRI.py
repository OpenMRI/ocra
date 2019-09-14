
#!/usr/bin/env python

# import general packages
from basicpara import parameters
from globalsocket import gsocket
from mri_lab_8_sd import MRI_SD_Widget
from mri_lab_7_rt import MRI_Rt_Widget
from mri_lab_6_imaging3d import MRI_3DImag_Widget
from mri_lab_5_imaging2d import MRI_2DImag_Widget
from mri_lab_4_projection import MRI_Proj_Widget
from mri_lab_3_signals import MRI_Sig_Widget
from mri_lab_2_se import MRI_SE_Widget
from mri_lab_1_fid import MRI_FID_Widget
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
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

# import GUI classes

# import private packages
# from assembler import Assembler

# load .ui files for different pages
Main_Window_Form, Main_Window_Base = loadUiType('ui/mainWindow.ui')
Welcome_Widget_Form, Welcome_Widget_Base = loadUiType('ui/welcomeWidget.ui')
Config_Dialog_Form, Config_Dialog_Base = loadUiType('ui/configDialog.ui')

# # create global TCP socket
# gsocket = QTcpSocket()


# main window
class MainWindow(Main_Window_Base, Main_Window_Form):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.init_menu()
        self.stacked_widget = QStackedWidget()
        self.init_stacked_widget()
        self.setWindowTitle('MRI Tabletop')
        self.setWindowIcon(QIcon('ui/image/icon.png'))
        # setup close event
        self.ui = loadUi('ui/mainWindow.ui')
        self.ui.closeEvent = self.closeEvent

    def init_menu(self):
        # File menu
        self.actionConfig.triggered.connect(self.config)
        self.actionQuit.triggered.connect(self.quit_application)

        # MRI Lab menu
        self.actionFID.triggered.connect(self.open_mri_fid)
        self.actionSE.triggered.connect(self.open_mri_se)
        self.actionSig.triggered.connect(self.open_mri_sig)
        self.actionProj.triggered.connect(self.open_mri_proj)
        self.action2DImag.triggered.connect(self.open_mri_2dimag)
        self.action3DImag.triggered.connect(self.open_mri_3dimag)
        self.actionRTRotate.triggered.connect(self.open_mri_rt)
        self.actionSequence_Design.triggered.connect(self.open_mri_sd)

        # set shortcuts
        self.actionConfig.setShortcut('Ctrl+Shift+C')
        self.actionQuit.setShortcut('Ctrl+Q')
        self.actionFID.setShortcut('Ctrl+1')
        self.actionSE.setShortcut('Ctrl+2')
        self.actionSig.setShortcut('Ctrl+3')
        self.actionProj.setShortcut('Ctrl+4')
        self.action2DImag.setShortcut('Ctrl+5')
        self.action3DImag.setShortcut('Ctrl+6')
        self.actionRTRotate.setShortcut('Ctrl+7')
        self.actionSequence_Design.setShortcut('Ctrl+8')

    def init_stacked_widget(self):
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.welcomeWidget = WelcomeWidget()
        self.mriFidWidget = MRI_FID_Widget()
        self.mriSeWidget = MRI_SE_Widget()
        self.mriSigWidget = MRI_Sig_Widget()
        self.mriProjWidget = MRI_Proj_Widget()
        self.mri2DImagWidget = MRI_2DImag_Widget()
        self.mri3DImagWidget = MRI_3DImag_Widget()
        self.mriRtWidget = MRI_Rt_Widget()
        self.mriSdWidget = MRI_SD_Widget()
        self.mriDesignWidget = MRI_SD_Widget()
        self.stacked_widget.addWidget(self.welcomeWidget)
        self.stacked_widget.addWidget(self.mriFidWidget)
        self.stacked_widget.addWidget(self.mriSeWidget)
        self.stacked_widget.addWidget(self.mriSigWidget)
        self.stacked_widget.addWidget(self.mriProjWidget)
        self.stacked_widget.addWidget(self.mri2DImagWidget)
        self.stacked_widget.addWidget(self.mri3DImagWidget)
        self.stacked_widget.addWidget(self.mriRtWidget)
        self.stacked_widget.addWidget(self.mriSdWidget)
        self.stacked_widget.addWidget(QLabel("Not developed"))
        self.stacked_widget.addWidget(QLabel("Not developed"))

    def config(self):
        self.welcomeWidget.popConfigDialog.show()

    def quit_application(self):
        quit_choice = QMessageBox.question(self, 'Confirm', 'Do you want to quit?',
                                           QMessageBox.Yes | QMessageBox.No)
        if quit_choice == QMessageBox.Yes:
            sys.exit()
            # QCoreApplication.instance().quit() # same function
        else:
            pass

    def closeEvent(self, event):
        quit_choice = QMessageBox.question(self, 'Confirm', 'Do you want to quit?',
                                           QMessageBox.Yes | QMessageBox.No)
        if quit_choice == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def stop_all(self):
        ''' Call stop functions of all widgets before opening a new one'''
        print("Stopping all acquisation!")
        if not self.mriFidWidget.idle:
            self.mriFidWidget.stop()
        if not self.mriSeWidget.idle:
            self.mriSeWidget.stop()
        if not self.mriSigWidget.idle:
            self.mriSigWidget.stop()
        if not self.mriProjWidget.idle:
            self.mriProjWidget.stop()
        if not self.mri2DImagWidget.idle:
            self.mri2DImagWidget.stop()
        if not self.mri3DImagWidget.idle:
            self.mri3DImagWidget.stop()
        if not self.mriRtWidget.idle:
            self.mriRtWidget.stop()

    # start MRI Lab GUIs:
    def open_mri_fid(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(1)
        # update frequency to server
        self.mriFidWidget.set_freq(parameters.get_freq())
        self.mriFidWidget.freqValue.setValue(
            parameters.get_freq())  # maybe put this in lower funcs
        self.setWindowTitle('MRI tabletop - FID GUI')

    def open_mri_se(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(2)
        self.mriSeWidget.set_freq(parameters.get_freq())
        self.mriSeWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - SE GUI')

    def open_mri_sig(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(3)
        self.mriSigWidget.set_freq(parameters.get_freq())
        self.mriSigWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - Signals GUI')

    def open_mri_proj(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(4)
        self.mriProjWidget.set_freq(parameters.get_freq())
        self.mriProjWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - 1D Projection GUI')

    def open_mri_2dimag(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(5)
        self.mri2DImagWidget.set_freq(parameters.get_freq())
        self.mri2DImagWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - 2D Image GUI')

    def open_mri_3dimag(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(6)
        self.mri3DImagWidget.set_freq(parameters.get_freq())
        self.mri3DImagWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - 3D Image GUI')

    def open_mri_rt(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(7)
        self.mriRtWidget.set_freq(parameters.get_freq())
        self.mriRtWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - Real-time Update GUI')

    def open_mri_sd(self):
        self.stop_all()
        self.stacked_widget.setCurrentIndex(8)
        self.mriRtWidget.set_freq(parameters.get_freq())
        self.mriRtWidget.freqValue.setValue(parameters.get_freq())
        self.setWindowTitle('MRI tabletop - Sequence Design GUI')


# configuration dialog
class ConfigDialog(Config_Dialog_Base, Config_Dialog_Form):
    def __init__(self):
        super(ConfigDialog, self).__init__()
        self.setupUi(self)
        # setup closeEvent
        self.ui = loadUi('ui/configDialog.ui')
        self.ui.closeEvent = self.closeEvent
        # setup connection to red-pitaya
        self.connectedLabel.setVisible(False)
        self.connectButton.clicked.connect(self.socket_connect)
        gsocket.connected.connect(self.socket_connected)
        gsocket.error.connect(self.socket_error)
        # IP address validator
        IP_validator = QRegExp(
            '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)'
            '{3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
        self.addrValue.setValidator(
            QRegExpValidator(IP_validator, self.addrValue))

    def socket_connect(self):
        print('Connecting...')
        self.connectButton.setEnabled(False)
        gsocket.connectToHost(self.addrValue.text(), 1001)

    def socket_connected(self):
        print("Connected!")
        self.connectButton.setEnabled(True)
        self.connectedLabel.setVisible(True)

    def socket_error(self, socketError):
        if socketError == QAbstractSocket.RemoteHostClosedError:
            pass
        else:
            QMessageBox.information(
                self, 'PulsedNMR', 'Error: %s.' % gsocket.errorString())
        self.connectButton.setEnabled(True)

    def closeEvent(self, event):
        pass
        # self.connectButton.setEnabled(True)
        # this still cannot solve the waiting problem


# welcome widget
class WelcomeWidget(Welcome_Widget_Base, Welcome_Widget_Form):
    def __init__(self):
        super(WelcomeWidget, self).__init__()
        self.setupUi(self)
        self.popConfigDialog = ConfigDialog()
        self.configButton.clicked.connect(self.config)

    def config(self):
        self.popConfigDialog.show()


# run
def run():
    app = QApplication(sys.argv)
    MRILab = MainWindow()
    MRILab.show()
    sys.exit(app.exec_())


# main function
if __name__ == '__main__':
    run()
