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
import scipy.io as sp
import matplotlib
from matplotlib.widgets import Button
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from parameters import params
from dataHandler import data
from dataLogger import logger

CC_RelaxT2_Form, CC_RelaxT2_Base = loadUiType('ui/ccRelaxometerT2.ui')

class CCRelaxT2Widget(CC_RelaxT2_Base, CC_RelaxT2_Form):
    def __init__(self):
        super(CCRelaxT2Widget, self).__init__()
        self.setupUi(self)

        self.load_params()

        self.data = data()
        self.data.readout_finished.connect(self.update_dataplot)
        self.data.t2_finished.connect(self.update_fit)

        self.t2Start_btn.clicked.connect(self.measureT2)

        self.init_figure()

#_______________________________________________________________________________
#   Init Functions

    def init_figure(self): # Function for initialization of plot figure
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax1 = self.fig.add_subplot(2,1,1)
        self.ax2 = self.fig.add_subplot(2,1,2)
        self.plotNav_widget.setVisible(False)
        self.prevPlot_btn.clicked.connect(self.prevPlot)
        self.nextPlot_btn.clicked.connect(self.nextPlot)
#_______________________________________________________________________________
#   Control Acquisition and Data Processing

    def measureT2(self):
        print("Start T2")

        # Setup and update parameters
        self.ax1.clear(); self.ax2.clear()
        self.controls.setEnabled(False)
        self.plotNav_widget.setVisible(False)
        self.time_ax = []; self.acq_data = []
        self.datapoints_te = []; self.datapoints_peaks = []

        self.update_params()
        params.saveFile()

        # Calculate all TE values from input
        self.TE_values = np.rint(np.logspace(np.log10(params.t2Start), np.log10(params.t2End), params.t2Step))
        print(self.TE_values)

        # Determine averaging variables
        avgPoint = 1; avgMeas = 1
        if self.measAvg_enable.isChecked(): avgMeas = self.measAvg_input.value()
        if self.dataAvg_enable.isChecked(): avgPoint = self.dataAvg_input.value()
        self.n_acq = params.t2Step*avgMeas*avgPoint
        self.acq_count = 0

        # Set fixed output values:
        self.freq_output.setText(str(round(params.freq, 5)))
        self.at_output.setText(str(params.at))
        duration = round((params.t2Recovery + sum(self.TE_values))*self.n_acq/1000,2)
        self.dur_output.setText(str(duration))

        # Call T2 function from dataHandler
        t2, r2 = self.data.T2_measurement(self.TE_values, params.freq, params.t2Recovery,\
            avgP = avgPoint, avgM = avgMeas)
        logger.add('T2', res=t2, err=r2, val=self.TE_values, avgP = avgPoint, avgM = avgMeas)

        # Setup results and call interactive plot tool if necessary
        self.t2_output.setText(str(round(t2,2)))
        self.r2_output.setText(str(round(r2,4)))

        if avgMeas > 1: self.interactive_plot()
        self.controls.setEnabled(True)
#_______________________________________________________________________________
#    Update functions during acquisition

    def update_dataplot(self):
        print(">> Update plot.")
        self.set_output(self.data.snr, float('nan'), self.data.fwhm_value)
        self.acq_count+= 1
        self.meas_progress.setValue(self.acq_count*100/self.n_acq)

        if self.time_ax == []: self.time_ax.extend(self.data.time_axis)
        else:self.time_ax.extend([t + self.time_ax[-1] for t in self.data.time_axis])
        self.acq_data.extend(self.data.mag_con)

        self.ax1.clear(); self.ax1.set_ylabel('acquired RX signals [mV]'), self.ax1.set_xlabel('time [ms]')
        self.ax1.plot(self.time_ax, self.acq_data, color='#33A4DF'); self.fig_canvas.draw()
        self.ax2.plot(self.data.te, self.data.peaks[-1], 'x', color='#33A4DF'); self.fig_canvas.draw()

        self.datapoints_te.append(self.data.te)
        self.datapoints_peaks.append(self.data.peaks[-1])

        self.fig_canvas.flush_events()

    def update_fit(self):

        if self.data.idxM == 0:
            self.acq_frame = pd.DataFrame(self.acq_data, columns=['magnitude acq '+str(self.data.idxM+1)], index=self.time_ax)
            self.fits_frame = pd.DataFrame(self.data.y_fit, columns=['TE fit '+str(self.data.idxM+1)], index=self.data.x_fit)
            self.peak_frame = pd.DataFrame(self.datapoints_peaks, columns=['datapoints fit '+str(self.data.idxM+1)], index=self.datapoints_te)
            self.meas_frame = pd.DataFrame(self.data.measurement, columns=['datapoints fit '+str(self.data.idxM+1)], index=self.TE_values)
            self.fitparams = pd.DataFrame(self.data.fit_params, columns=['params fit '+str(self.data.idxM+1)])
        else:
            self.acq_frame['magnitude acq '+str(self.data.idxM+1)] = self.acq_data # raw magnitude signals
            self.fits_frame['TE fit '+str(self.data.idxM+1)] = self.data.y_fit # curve fits
            self.peak_frame['datapoints fit '+str(self.data.idxM+1)] = self.datapoints_peaks # all measured datapoints
            self.meas_frame['datapoints fit '+str(self.data.idxM+1)] = self.data.measurement # averaged datapoints (only applies, when avgP > 1)
            self.fitparams['params fit '+str(self.data.idxM+1)] = self.data.fit_params # parameters for curve fit > export

        self.datapoints_te = []; self.datapoints_peaks = []
        self.time_ax = []; self.acq_data = []

        self.t2_output.setText(str(round(self.data.T2[-1],2)))
        self.r2_output.setText(str(round(self.data.R2[-1],4)))

        self.fits_frame.plot(ax=self.ax2, color='#4260FF', legend=False); self.fig_canvas.draw()

        if self.measAvg_enable.isChecked() and self.data.idxM+1 < self.measAvg_input.value():
            # time.sleep(5)
            self.ax1.clear(); self.ax1.set_ylabel('acquired RX signals [mV]'); self.ax1.set_xlabel('time [ms]')
            self.ax2.clear(); self.ax2.set_ylabel('RX signal peak [mV]'); self.ax2.set_xlabel('echo time (TE) [ms]')

        QApplication.processEvents()
#_______________________________________________________________________________
#   Interactive Plot (post acquisition)

    def interactive_plot(self):
        self.ax1.clear(); self.ax2.clear()
        self.plot_index = 0
        self.plot_frame(self.plot_index)
        self.plotNav_widget.setVisible(True)
        self.fig_canvas.draw()

    def nextPlot(self):
        if self.plot_index < len(self.fits_frame.columns)-1:
            self.plot_index += 1
            self.plot_frame(self.plot_index)
        else: return

    def prevPlot(self):
        if self.plot_index > 0:
            self.plot_index -= 1
            self.plot_frame(self.plot_index)
        else: return

    def plot_frame(self, idx):
        self.ax1.clear(); self.ax2.clear()
        self.ax2.set_title('Aquisition '+str(idx+1)+'/'+str(len(self.fits_frame.columns)))
        self.ax1.set_ylabel('acquired RX signals [mV]'), self.ax1.set_xlabel('time [ms]')
        self.ax2.set_ylabel('RX signal peak [mV]'), self.ax2.set_xlabel('echo time (TE) [ms]')
        self.acq_frame.iloc[:, idx].plot(ax=self.ax1)
        self.peak_frame.iloc[:,idx].plot(style='x', ax=self.ax2, legend='True')
        self.fits_frame.iloc[:,idx].plot(ax=self.ax2, color='#4260FF', legend=True)
        self.fig_canvas.draw()
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
        params.t2avgM = self.measAvg_input.value()
        params.t2avgP = self.dataAvg_input.value()

    def load_params(self):
        self.t2Start_input.setValue(params.t2Start)
        self.t2End_input.setValue(params.t2End)
        self.t2Step_input.setValue(params.t2Step)
        self.t2Recovery_input.setValue(params.t2Recovery)
        self.measAvg_input.setValue(params.t2avgM)
        self.dataAvg_input.setValue(params.t2avgP)
#_______________________________________________________________________________
#   Save data to .csv

    def saveData(self, path_str):

        with open(path_str,'w') as file:
            file.write(self.meas_frame.to_csv()+"\n\n"+self.fitparams.to_csv())
