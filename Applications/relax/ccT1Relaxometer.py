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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from parameters import params
from dataHandler import data
from dataLogger import logger

CC_RelaxT1_Form, CC_RelaxT1_Base = loadUiType('ui/ccRelaxometerT1.ui')

class CCRelaxT1Widget(CC_RelaxT1_Base, CC_RelaxT1_Form):

    call_update = pyqtSignal()

    def __init__(self):
        super(CCRelaxT1Widget, self).__init__()
        self.setupUi(self)

        self.load_params()

        self.data = data()
        self.data.readout_finished.connect(self.update_dataplot)
        self.data.t1_finished.connect(self.update_fit)

        self.t1Start_btn.clicked.connect(self.measureT1)

        self.seq_selector.addItems(['Inversion Recovery', 'Saturation Inversionn Recovery'])
        self.seq_selector.currentIndexChanged.connect(self.set_sequence)
        self.seq_selector.setCurrentIndex(0)
        self.seq = 'ir'

        self.init_figure()
#_______________________________________________________________________________
#   Init Functions

    def init_figure(self): # Function for initialization of plot figure
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax1 = self.fig.add_subplot(2,1,1); self.ax1.set_ylabel('acquired RX signals [mV]'); self.ax1.set_xlabel('time [ms]')
        self.ax2 = self.fig.add_subplot(2,1,2); self.ax2.set_ylabel('RX signal peak [mV]'); self.ax2.set_xlabel('time of inversion (TI) [ms]')
        self.plotNav_widget.setVisible(False)
        self.prevPlot_btn.clicked.connect(self.prevPlot)
        self.nextPlot_btn.clicked.connect(self.nextPlot)
        self.call_update.emit()

    def set_sequence(self, idx): # Function to switch current sequence
        seq = {
            0: self.data.set_IR,
            1: self.data.set_SIR
        }
        if idx == 1: self.seq = 'sir'
        else: self.seq = 'ir'
        seq[idx]()
        try: print(self.seq)
        except: pass
#_______________________________________________________________________________
#   Control Acquisition and Data Processing

    def measureT1(self):
        print("Start T1")

        # Setup and update parameters
        self.ax1.clear(); self.ax2.clear()
        self.controls.setEnabled(False)
        self.plotNav_widget.setVisible(False)
        self.time_ax = []; self.acq_data = []
        self.datapoints_ti = []; self.datapoints_peaks = []

        self.update_params()
        params.saveFile()

        # Calculate all TI values from input
        self.TI_values = np.rint(np.logspace(np.log10(params.t1Start), np.log10(params.t1End), params.t1Step))
        print(self.TI_values)

        # Determine averaging variables
        avgPoint = 1; avgMeas = 1
        if self.measAvg_enable.isChecked(): avgMeas = self.measAvg_input.value()
        if self.dataAvg_enable.isChecked(): avgPoint = self.dataAvg_input.value()
        self.n_acq = params.t1Step*avgMeas*avgPoint
        self.acq_count = 0

        # Set fixed output values:
        self.freq_output.setText(str(round(params.freq, 5)))
        self.at_output.setText(str(params.at))
        duration = round((params.t1Recovery+sum(self.TI_values))*self.n_acq/1000,2)
        self.dur_output.setText(str(duration))

        self.call_update.emit()

        # Call T1 function from dataHandler
        t1, r2 = self.data.T1_measurement(self.TI_values, params.freq, params.t1Recovery,\
            avgP = avgPoint, avgM = avgMeas, seqType = self.seq)
        logger.add('T1', res=t1, err=r2, val=self.TI_values, avgP = avgPoint, avgM = avgMeas)

        if avgMeas > 1: self.interactive_plot()
        self.controls.setEnabled(True)
#_______________________________________________________________________________
#    Update functions during acquisition

    def update_dataplot(self):
        print(">> Update plot.")
        self.set_output(self.data.snr, self.data.fwhm_value, float('nan'))
        self.acq_count+= 1
        self.meas_progress.setValue(self.acq_count*100/self.n_acq)

        if self.time_ax == []: self.time_ax.extend(self.data.time_axis)
        else:self.time_ax.extend([t + self.time_ax[-1] for t in self.data.time_axis])
        self.acq_data.extend(self.data.mag_con)

        self.ax1.clear(); self.ax1.set_ylabel('acquired RX signals [mV]'), self.ax1.set_xlabel('time [ms]')
        self.ax1.plot(self.time_ax, self.acq_data, color='#33A4DF')
        self.ax2.plot(self.data.ti, self.data.peaks[-1], 'x', color='#33A4DF')
        self.fig_canvas.draw(); self.call_update.emit()

        self.datapoints_ti.append(self.data.ti)
        self.datapoints_peaks.append(self.data.peaks[-1])

        self.call_update.emit()

    def update_fit(self):

        if self.data.idxM == 0:
            self.acq_frame = pd.DataFrame(self.acq_data, columns=['magnitude acq '+str(self.data.idxM+1)], index=self.time_ax)
            self.fits_frame = pd.DataFrame(self.data.y_fit, columns=['TE fit '+str(self.data.idxM+1)], index=self.data.x_fit)
            self.peak_frame = pd.DataFrame(self.datapoints_peaks, columns=['datapoints fit '+str(self.data.idxM+1)], index=self.datapoints_ti)
            self.meas_frame = pd.DataFrame(self.data.measurement, columns=['datapoints fit '+str(self.data.idxM+1)], index=self.TI_values)
            self.fitparams = pd.DataFrame(self.data.fit_params, columns=['params fit '+str(self.data.idxM+1)])
        else:
            self.acq_frame['magnitude acq '+str(self.data.idxM+1)] = self.acq_data # raw magnitude signals
            self.fits_frame['TI fit '+str(self.data.idxM+1)] = self.data.y_fit # curve fits
            self.peak_frame['datapoints fit '+str(self.data.idxM+1)] = self.datapoints_peaks # all measured datapoints
            self.meas_frame['datapoints fit '+str(self.data.idxM+1)] = self.data.measurement # averaged datapoints (only applies, when avgP > 1)
            self.fitparams['params fit '+str(self.data.idxM+1)] = self.data.fit_params # parameters for curve fit > export

        self.datapoints_ti = []; self.datapoints_peaks = []
        self.time_ax = []; self.acq_data = []

        self.t1_output.setText(str(round(self.data.T1[-1],2)))
        self.r2_output.setText(str(round(self.data.R2[-1],4)))

        self.fits_frame.plot(ax=self.ax2, color='#4260FF', legend=False); self.fig_canvas.draw()
        self.call_update.emit()

        if self.measAvg_enable.isChecked() and self.data.idxM+1 < self.measAvg_input.value():
            # time.sleep(5)
            self.ax1.clear(); self.ax1.set_ylabel('acquired RX signals [mV]'); self.ax1.set_xlabel('time [ms]')
            self.ax2.clear(); self.ax2.set_ylabel('RX signal peak [mV]'); self.ax2.set_xlabel('time of inversion (TI) [ms]')
            self.call_update.emit()

#_______________________________________________________________________________
#   Interactive Plot (post acquisition)

    def interactive_plot(self):
        self.ax1.clear(); self.ax2.clear()
        self.plot_index = 0
        self.plot_frame(self.plot_index)
        self.plotNav_widget.setVisible(True)
        self.fig_canvas.draw()
        self.call_update.emit()

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
        self.ax1.set_ylabel('acquired RX signals [mV]'); self.ax1.set_xlabel('time [ms]')
        self.ax2.set_ylabel('RX signal peak [mV]'); self.ax2.set_xlabel('time of inversion (TI) [ms]')
        self.acq_frame.iloc[:, idx].plot(ax=self.ax1)
        self.peak_frame.iloc[:,idx].plot(style='x', ax=self.ax2, legend='True')
        self.fits_frame.iloc[:,idx].plot(ax=self.ax2, color='#4260FF', legend=True)
        self.fig_canvas.draw()
        self.call_update.emit()
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
#_______________________________________________________________________________
#   Save data to .csv

    def saveData(self, path_str):

        with open(path_str,'w') as file:
            file.write(self.meas_frame.to_csv()+"\n\n"+self.fitparams.to_csv())
