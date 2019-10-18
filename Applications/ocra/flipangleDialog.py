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
import mri_lab_1_fid

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
        #self.ui = loadUi('ui/flipangleDialog.ui')
        #self.ui.closeEvent = self.closeEvent

        self.fid = mri_lab_1_fid.MRI_FID_Widget()
        #print(mri_lab_1_fid.MRI_FID_Widget().size)

        # Setup Buttons
        # self.uploadSeq.clicked.connect(self.upload_pulse)
        # self.findCenterBtn.clicked.connect(self.find_centerFreq)
        # self.acceptCenterBtn.clicked.connect(self.confirm_centerFreq)
        # self.applyAtBtn.clicked.connect(self.apply_AT)

        # Setup line edit for estimated frequency
        # self.estimationValue.valueChanged(self.setEstFreqValue())
        # self.estimationValue.setKeyboardTracking(False)

        # Setup line edit as read only
        self.pulsePath.setReadOnly(True)
        self.centerFreqValue.setReadOnly(True)
        self.sigValue.setReadOnly(True)
        self.atValue.setReadOnly(True)

        # Disable UI elements
        self.uploadSeq.setEnabled(False)
        self.estimationValue.setEnabled(True)
        self.findCenterBtn.setEnabled(False)
        self.acceptCenterBtn.setEnabled(False)
        self.applyAtBtn.setEnabled(False)


        def upload_pulse(self):
            dialog = QFileDialog()
            fname = dialog.getOpenFileName(None, "Import Pulse Sequence", "", "Text files (*.txt)")
            print("\tUploading 90 degree flip sequence to server.")
            try:
                self.send_pulse(fname[0])
                self.uploadSeq.setText(fname[0])
            except IOError as e:
                print("\tError: required txt file doesn't exist.")
                return
                print("\tUploaded successfully to server.")
        '''
        def find_centerFreq(self):
            self.estimationValue.setEnabled(False)
            parameters.set_freq(self.estimationValue)
            gsocket.write(struct.pack('<I', 1 << 28 | int(1.0e6 * self.estimationValue)))
            fid_widget.single_acquisition()
            print(fid_widget.single_acq_flag)
            while True:
                if .single_acq_flag == False:
                    print("\tSingle acquisition completed.")
                    self.estimationValue.setEnabled(True)
                else:
                    continue
        '''
