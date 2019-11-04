# import general packages
import sys
import struct
import time

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget, \
    QLabel, QMessageBox, QCheckBox, QFileDialog
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QCoreApplication, QRegExp, QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket

# import calculation and plot packages
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from globalsocket import gsocket
from parameters import params
from dataHandler import data
from dataLogger import logger

CC_RelaxT1_Form, CC_RelaxT1_Base = loadUiType('ui/ccRelaxometerT1.ui')

class CCRelaxT1Widget(CC_RelaxT1_Base, CC_RelaxT1_Form):
    def __init__(self):
        super(CCRelaxT1Widget, self).__init__()
        self.setupUi(self)

        self.load_params()

        self.data = data()
        self.data.readout_finished.connect(self.update_dataplot)
        self.data.t1_finished.connect(self.update_fit)

        self.t1Start_btn.clicked.connect(self.measureT1)

        self.init_figure()
#_______________________________________________________________________________
#   Init Functions

    def init_figure(self): # Function for initialization of plot figure
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax1 = self.fig.add_subplot(2,1,1)
        self.ax2 = self.fig.add_subplot(2,2,3)
        self.ax3 = self.fig.add_subplot(2,2,4)
#_______________________________________________________________________________
#   Control Acquisition and Data Processing

    def measureT1(self):

        print("Start T1")

        self.ax1.clear(); self.ax2.clear(); self.ax3.clear()
        self.ax1.set_ylabel('acquired RX signals [mV]'), self.ax1.set_xlabel('time [ms]')
        self.ax2.set_ylabel('RX signal peak [mV]'), self.ax2.set_xlabel('time of inversion (TI) [ms]')
        self.ax3.set_xlabel('time of inversion (TI) [ms]')

        self.time_ax = []

        self.update_params()
        params.saveFile()

        # Calculate all TI values from input
        self.TI_values = np.rint(np.logspace(np.log10(params.t1Start), np.log10(params.t1End), params.t1Step))
        print(self.TI_values)

        # Set fixed output values:
        self.freq_output.setText(str(round(params.freq, 5)))
        self.at_output.setText(str(params.at))
        duration = round((params.t1Recovery*params.t1Step + sum(self.TI_values))/1000,2)
        self.dur_output.setText(str(duration))

        avgPoint = 1; avgMeas = 1
        if self.measAvg_enable.isChecked(): avgMeas = self.measAvg_input.value()
        if self.dataAvg_enable.isChecked(): avgPoint = self.dataAvg_input.value()

        t1, r2 = self.data.T1_measurement(self.TI_values, params.freq, params.t1Recovery,\
            avgP = avgPoint, avgM = avgMeas)
        logger.add('T1', res=t1, err=r2, val=self.TI_values, avgP = avgPoint, avgM = avgMeas)

        self.t1_output.setText(str(round(t1,2)))
        self.r2_output.setText(str(round(r2,4)))

    def update_dataplot(self):
        print(">> Update plot.")
        self.set_output(self.data.snr, self.data.fwhm_value, float('nan'))

        if self.time_ax == []: self.time_ax = self.data.time_axis
        else: self.time_ax = [t + self.time_ax[-1] for t in self.data.time_axis]

        self.ax1.plot(self.time_ax, self.data.real_con, color='#33A4DF')
        self.ax2.plot(self.data.ti, self.data.peaks[-1], 'x', color='#33A4DF')

        self.fig_canvas.draw()
        QApplication.processEvents()

    def update_fit(self):

        if self.data.idxM == 0: self.fits = pd.DataFrame(self.data.y_fit, columns=['TI fit '+str(self.data.idxM+1)], index=self.data.x_fit)
        else: self.fits['TI fit '+str(self.data.idxM+1)] = self.data.y_fit

        if self.measAvg_enable.isChecked() and self.data.idxM+1 < self.measAvg_input.value():
            self.ax1.clear(); self.ax1.set_ylabel('acquired RX signals [mV]'); self.ax1.set_xlabel('time [ms]')
            self.ax2.clear(); self.ax2.set_ylabel('RX signal peak [mV]'); self.ax2.set_xlabel('time of inversion (TI) [ms]')

        self.ax3.clear(); self.ax3.set_xlabel('time of inversion (TI) [ms]')
        self.fits.plot(ax=self.ax3)
        self.fig_canvas.draw()
        QApplication.processEvents()
#_______________________________________________________________________________
#   Update Output Parameters

    def set_output(self, snr, fwhm, temp):
        self.snr_output.setText(str(round(snr, 5)))
        self.fwhm_output.setText(str(round(fwhm, 2)))
        self.temp_output.setText(str(round(temp, 2)))

    def update_params(self):
        params.t1Start = self.t1Start_input.value()
        params.t1End = self.t1End_input.value()
        params.t1Step = self.t1Step_input.value()
        params.t1Recovery = self.t1Recovery_input.value()
        params.t1avgM = self.measAvg_input.value()
        params.t1avgP = self.dataAvg_input.value()

    def load_params(self):
        self.t1Start_input.setValue(params.t1Start)
        self.t1End_input.setValue(params.t1End)
        self.t1Step_input.setValue(params.t1Step)
        self.t1Recovery_input.setValue(params.t1Recovery)
        self.measAvg_input.setValue(params.t1avgM)
        self.dataAvg_input.setValue(params.t1avgP)
