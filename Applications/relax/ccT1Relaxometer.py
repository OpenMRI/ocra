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
from scipy.optimize import curve_fit, brentq
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from math import pi

from globalsocket import gsocket
from parameters import params
from dataprocessing import data

CC_RelaxT1_Form, CC_RelaxT1_Base = loadUiType('ui/ccRelaxometerT1.ui')

class CCRelaxT1Widget(CC_RelaxT1_Base, CC_RelaxT1_Form):
    def __init__(self):
        super(CCRelaxT1Widget, self).__init__()
        self.setupUi(self)

        self.load_params()

        self.data = data()
        self.data.readout_finished.connect(self.received_data)

        self.t1Start_btn.clicked.connect(self.init_measurement)
        #self.t1Avg_enable.clicked.connect(self.t1Cycles_input.setEnabled)
        self.t1Avg_enable.setEnabled(False)
        self.t1Cycles_input.setEnabled(False)

        self.init_figure()
#_______________________________________________________________________________
#   Init Functions

    def init_figure(self): # Function for initialization of plot figure
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax1 = self.fig.add_subplot(2,1,1)
        self.ax2 = self.fig.add_subplot(2,1,2)

    def init_measurement(self):

        print("-> T1 measurement started.")

        # Initializations
        self.acqCount = 0
        self.meas_progress.setValue(0)
        self.average = [0] * self.t1Cycles_input.value()
        self.results = []
        self.ax1.clear(); self.ax2.clear()

        # Get values from controlcenter
        self.update_params()
        params.saveFile()

        # Calculate all TE values from input
        self.TI_values = np.rint(np.logspace(np.log10(params.t1Start), np.log10(params.t1End), params.t1Step))
        print(self.TI_values)

        # Calculate estimated Duration in min
        duration = round((params.t1Recovery*params.t1Step + sum(self.TI_values))/1000,2)

        # Set acquisition frequency from parameters
        self.data.set_freq(params.freq)

        # Set fixed output values:
        self.freq_output.setText(str(round(params.freq, 5)))
        self.at_output.setText(str(params.at))
        self.dur_output.setText(str(duration))

        # Add: Ensure same recovery for first measurement (optional)

        # Disable controlcenter and start
        self.MeasParamWidget.setEnabled(False)
        self.measurement_run()
#_______________________________________________________________________________
#   Control Acquisition and Data Processing

    def measurement_run(self):
        if self.acqCount < len(self.TI_values):
            print("\nAcquisition counter: ", self.acqCount+1,"/",len(self.TI_values),":")
            self.data.set_IR(int(self.TI_values[self.acqCount]))#, int(params.t1Recovery))
            self.data.acquire()
            self.acqCount += 1
        else:
            self.plot_fit()
            self.activeMeas_flag = False
            self.MeasParamWidget.setEnabled(True)

    def received_data(self):
        print("Handling data.")
        # Set output values and plot
        self.set_output(self.acqCount, self.data.peak_value, self.data.fwhm_value)
        time_ax = [t + self.TI_values[self.acqCount-1] for t in self.data.time_axis]
        self.ax1.plot(time_ax, self.data.real_con, color = '#33A4DF')

        # centerFreq_idx = self.data.freqaxis[spatial.KDTree(self.data.freqaxis).query(parameters.get_freq)]
        #self.results.append(self.data.peak_value)
        time_peak = np.argmax(abs(self.data.real_con))
        print(time_peak, ', peak : ', self.data.real_con[time_peak])
        self.results.append(self.data.real_con[time_peak])

        self.ax2.plot(self.TI_values[self.acqCount-1], self.results[self.acqCount-1], 'x', color='#33A4DF')
        self.fig_canvas.draw()

        # time.sleep(self.t1Recovery) # Better change recovery time in sequence
        time.sleep(params.t1Recovery/1000)
        self.meas_progress.setValue(self.acqCount/len(self.TI_values)*100)
        self.measurement_run()

#_______________________________________________________________________________
#   Update Output Parameters

    def set_output(self, snr, temp, fwhm):
        self.snr_output.setText(str(round(snr, 5)))
        self.fwhm_output.setText(str(round(fwhm, 2)))
        self.temp_output.setText(str(round(temp, 2)))

    def update_params(self):
        params.t1Start = self.t1Start_input.value()
        params.t1End = self.t1End_input.value()
        params.t1Step = self.t1Step_input.value()
        params.t1Recovery = self.t1Recovery_input.value()
        params.t1Cyc = self.t1Cycles_input.value()

    def load_params(self):
        self.t1Start_input.setValue(params.t1Start)
        self.t1End_input.setValue(params.t1End)
        self.t1Step_input.setValue(params.t1Step)
        self.t1Recovery_input.setValue(params.t1Recovery)
        self.t1Cycles_input.setValue(params.t1Cyc)
#_______________________________________________________________________________
#   Plotting Fit

    def fit_function(self, x, A, B, C):
        return A - B * np.exp(-C * x)

    def plot_fit(self):

        params, cov = curve_fit(self.fit_function, self.TI_values, self.results)
        #x_fit = np.linspace(self.TI_values[0], self.TI_values[-1], 1000)
        x_fit = np.linspace(0, int(1.2*self.TI_values[-1]), 1000)
        self.ax2.plot(x_fit, self.fit_function(x_fit, *params))
        self.fig_canvas.draw()
        print("Data plotted.")
        def func(x):
            return params[0] - params[1] * np.exp(-params[2]*x)
        T1 = round(brentq(func,self.TI_values[0],self.TI_values[-1]),2)
        self.t1_output.setText(str(T1))

        res = self.results - self.fit_function(self.TI_values, *params)
        ss_res = np.sum(res**2)
        ss_tot = np.sum((self.results-np.mean(self.results))**2)
        R2 = 1-(ss_res/ss_tot)

        self.r2_output.setText(str(round(R2,5)))
