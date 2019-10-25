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
import scipy.io as sp
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from math import pi

from globalsocket import gsocket
from parameters import params
from dataHandler import data

CC_RelaxT2_Form, CC_RelaxT2_Base = loadUiType('ui/ccRelaxometerT2.ui')

class CCRelaxT2Widget(CC_RelaxT2_Base, CC_RelaxT2_Form):
    def __init__(self):
        super(CCRelaxT2Widget, self).__init__()
        self.setupUi(self)

        self.load_params()

        self.data = data()
        self.data.readout_finished.connect(self.received_data)

        self.t2Start_btn.clicked.connect(self.init_measurement)
        #self.t2Avg_enable.clicked.connect(self.t2Cycles_input.setEnabled)
        self.t2Avg_enable.setEnabled(False)
        self.t2Cycles_input.setEnabled(False)

        self.init_figure()

#_______________________________________________________________________________
#   Init Functions

    def init_figure(self): # Function for initialization of plot figure
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

    def init_measurement(self):
        print("-> T2 measurement started.")

        # Initializations
        self.acqCount = 0
        self.meas_progress.setValue(0)
        self.average = [0] * self.t2Cycles_input.value()

        # Get values from controlcenter
        params.t2Start = self.t2Start_input.value()
        params.t2End = self.t2End_input.value()
        params.t2Step = self.t2Step_input.value()
        params.t2Recovery = self.t2Recovery_input.value()

        # Calculate all TE values from input
        self.TE_values = np.arange(params.t2Start, params.t2End,\
            (params.t2End-params.t2Start)/params.t2Step)
        self.results = []

        # Calculate estimated Duration in min
        duration = (params.t2Recovery * params.t2Step + sum(self.TE_values)/1000)

        # Set acquisition frequency from parameters
        self.data.set_freq(params.freq)

        # Set fixed output values:
        self.freq_output.setText(str(params.freq))
        self.at_output.setText(str(params.at))
        self.dur_output.setText(str(duration))

        # Disable controlcenter and start
        self.MeasParamWidget.setEnabled(False)
        self.measurement_run()

#_______________________________________________________________________________
#   Control Acquisition and Data Processing

    def measurement_run(self):
        if self.acqCount <= len(self.TE_values)-1:
            print("\nAcquisition counter: ", self.acqCount+1,"/",len(self.TE_values),":")
            self.data.set_SE(int(self.TE_values[self.acqCount]))
            self.data.acquire()
            self.acqCount += 1
        else:
            self.plot_fit()
            self.activeMeas_flag = False
            self.MeasParamWidget.setEnabled(True)

    def received_data(self):
        print("Handling data.")
        self.set_output(self.acqCount, self.data.peak_value, self.data.fwhm_value)

        # centerFreq_idx = self.data.freqaxis[spatial.KDTree(self.data.freqaxis).query(parameters.get_freq)]
        self.results.append(round(self.data.peak_value, 3))
        self.ax.plot(self.TE_values[self.acqCount-1], self.results[self.acqCount-1], 'x', color='#33A4DF')
        self.fig_canvas.draw()

        time.sleep(params.t2Recovery/1000) # Better change recovery time in sequence

        self.meas_progress.setValue(self.acqCount/len(self.TE_values)*100)
        self.measurement_run()

#_______________________________________________________________________________
#   Update Output Parameters

    def set_output(self, snr, temp, fwhm):
        self.snr_output.setText(str(round(snr, 5)))
        self.fwhm_output.setText(str(round(fwhm, 2)))
        self.temp_output.setText(str(round(temp, 2)))

    def update_params(self):
        params.t2Start = self.t2Start_input.value()
        params.t2End = self.t2End_input.value()
        params.t2Step = self.t2Step_input.value()
        params.t2Recovery = self.t2Recovery_input.value()
        params.t2Cycles_input = self.t2Cyc.value()

    def load_params(self):
        self.t2Start_input.setValue(params.t2Start)
        self.t2End_input.setValue(params.t2End)
        self.t2Step_input.setValue(params.t2Step)
        self.t2Recovery_input.setValue(params.t2Recovery)
        self.t2Cycles_input.setValue(params.t2Cyc)
#_______________________________________________________________________________
#   Plotting Data

    def plot_fit(self):
        self.ax.plot(self.TE_values[:self.acqCount], self.results[:self.acqCount], color='#33A4DF')
        self.fig_canvas.draw()
        print("Data plotted.")
