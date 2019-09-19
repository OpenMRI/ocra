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


# import private packages
from globalsocket import gsocket
from basicpara import parameters
from assembler import Assembler

# load .ui files
Flipangle_Dialog_Form, Flipangle_Dialog_Base = loadUiType('ui/flipangleDialog.ui')

# Flipangle dialog window
class FlipangleDialog(Flipangle_Dialog_Base, Flipangle_Dialog_Form):
    def __init__(self):
        super(FlipangleDialog, self).__init__()
        self.setupUi(self)
        # setup closeEvent
        self.ui = loadUi('ui/flipangleDialog.ui')
        self.ui.closeEvent = self.closeEvent

        # Setup Buttons
        # self.uploadSeq.connect(self.upload_pulse)
        # self.findCenterBtn.connect(self.find_centerFreq)
        # self.acceptCenterBtn.connect(self.confirm_centerFreq)
        # self.applyAtBtn.connect(self.apply_AT)

        # Setup line edit for estimated frequency
        # self.estimationValue.valueChanged(self.setEstimatedFreq)

        # Setup line edit as read only
        self.pulsePath.setReadOnly(True)
        self.centerFreqValue.setReadOnly(True)
        self.sigValue.setReadOnly(True)
        self.atValue.setReadOnly(True)

        # Disable UI elements
        self.uploadSeq.setEnabled(True)
        self.estimationValue.setEnabled(False)
        self.findCenterBtn.setEnabled(False)
        self.acceptCenterBtn.setEnabled(False)
        self.applyAtBtn.setEnabled(False)


        def upload_pulse(self):

            dialog = QFileDialog()
            fname = dialog.getOpenFileName(None, "Import Pulse Sequence", "", "Text files (*.txt)")
