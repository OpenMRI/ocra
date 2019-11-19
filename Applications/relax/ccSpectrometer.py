# import general packages
import time
import csv

# import PyQt5 packages
from PyQt5.QtWidgets import QFileDialog
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import pyqtSignal, QStandardPaths

# import calculation and plot packages
import numpy as np
import scipy.io as sp
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from parameters import params
from dataHandler import data
from dataLogger import logger

CC_Spec_Form, CC_Spec_Base = loadUiType('ui/ccSpectrometer.ui')

class CCSpecWidget(CC_Spec_Base, CC_Spec_Form):

    call_update = pyqtSignal()

    def __init__(self):
        super(CCSpecWidget, self).__init__()
        self.setupUi(self)

        self.data = data()
        self.data.readout_finished.connect(self.acq_handler)
        self.data.uploaded.connect(self.sequence_uploaded)

        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax1 = self.fig.add_subplot(3,1,1)
        self.ax2 = self.fig.add_subplot(3,1,2)
        self.ax3 = self.fig.add_subplot(3,1,3)

        self.init_controlcenter()
        self.init_vars()

        self.toolBox.currentChanged.connect(self.switchPlot)

#_______________________________________________________________________________
#   Init Functions

    def init_controlcenter(self): # Init controlcenter
        self.load_params()
        # Set default tool (manual acquisition) and call setup handler
        self.toolBox.setCurrentIndex(0)
        self.switchPlot()
        # Sequence selector
        self.seq_selector.addItems(['Free Induction Decay', 'Spin Echo', 'Inversion Recovery','Saturation Inversion Recovery', 'Custom Sequence'])
        self.seq_selector.currentIndexChanged.connect(self.set_sequence)
        self.seq_selector.setCurrentIndex(0)
        self.set_sequence(0)
        # Manual acquisition toolbox
        self.uploadSeq_btn.clicked.connect(self.upload_sequence)
        self.uploadSeq_confirm.setEnabled(False)
        self.manualFreq_input.setKeyboardTracking(False)
        self.manualAt_input.setKeyboardTracking(False)
        self.manualFreq_input.valueChanged.connect(self.data.set_freq)
        self.manualAt_input.valueChanged.connect(self.data.set_at)
        self.manualAcquire_btn.clicked.connect(self.start_manual)
        self.manualCenter_btn.clicked.connect(self.manual_center)
        self.manualAvg_input.setEnabled(False)
        self.manualAvg_enable.clicked.connect(self.manualAvg_input.setEnabled)
        self.manualTE_input.setKeyboardTracking(False)
        self.manualTE_input.valueChanged.connect(self.data.set_SE)
        self.manualTE_input.setVisible(False)
        self.manualTELabel.setVisible(False)
        self.manualTI_input.setKeyboardTracking(False)
        self.manualTI_input.setVisible(False)
        self.manualTILabel.setVisible(False)
        # Autocenter tool
        self.autoCenter_btn.clicked.connect(self.init_autocenter)
        self.autoCenter_save_btn.clicked.connect(self.save_autocenter)
        self.autoCenter_save_btn.setEnabled(False)
        # Flipangle tool
        self.flipangle_btn.clicked.connect(self.init_flipangle)
        self.flipangle_save_btn.clicked.connect(self.save_flipangle)
        self.flipangle_save_btn.setEnabled(False)
        # Shim tool
        self.setOffset_btn.clicked.connect(self.set_grad_offsets)
        # Output parameters
        self.freq_output.setReadOnly(True)
        self.at_output.setReadOnly(True)
        self.center_output.setReadOnly(True)
        self.peak_output.setReadOnly(True)
        self.fwhm_output.setReadOnly(True)
        self.snr_output.setReadOnly(True)

        self.call_update.emit()

    def init_vars(self):
        # Initialization of values for autocenter and flipangle tool
        self.autocenter_flag = False
        self.flipangle_flag = False
        self.freqsweep_flag = False
        self.peakValue = 0
        self.centerValue = 0
        self.acqCount = 0

    def init_autocenter(self):
        # Setup values and axis
        self.init_vars()
        self.ax1.clear(); self.ax2.clear(); self.ax3.clear();
        self.progressBar.setValue(0)
        self.autocenter_flag = True
        self.peaks = []

        # Read input values
        params.autoSpan = self.freqSpan_input.value()
        params.autoStep = self.freqSteps_input.value()
        params.autoTimeout = self.freqTimeout_input.value()
        logger.add('AUC')

        self.freqSpace = np.linspace(params.freq-params.autoSpan/2, params.freq+params.autoSpan/2,\
            params.autoStep)

        print("Frequency space : ", self.freqSpace)

        # Disable controls and start
        self.disable_controls()
        self.freqsweep_run()

    def init_averaging(self):
        # Initialization of variables and arrays to sum data
        self.init_vars()
        self.timeout = 5 # Default timeout for averaging (5s)
        self.freqsweep_flag = True
        self.autoCenter_save_btn.setEnabled(False)

        self.fft_mag_avg = [0] * self.data.data_idx
        self.t_mag_avg = [0] * self.data.data_idx
        self.t_real_avg = [0] * self.data.data_idx
        self.t_imag_avg = [0] * self.data.data_idx

        # Create array with actual frequency
        params.avgCyc = self.manualAvg_input.value()
        self.freqSpace = [params.freq] * (params.avgCyc)

        # Disable Controls and start
        self.disable_controls()
        self.freqsweep_run()

    def init_flipangle(self):
        # Setup values and axis
        self.init_vars()
        self.at_results = []
        self.ax1.clear(); self.ax2.clear(); self.ax3.clear();
        self.progressBar.setValue(0)
        self.flipangle_save_btn.setEnabled(False)
        self.flipangle_flag = True

        # Read input parameters and
        params.flipStart = self.atStart_input.value()
        params.flipEnd = self.atEnd_input.value()
        params.flipStep = self.atSteps_input.value()
        params.flipTimeout = self.atTimeout_input.value()
        logger.add('FLA')

        self.data.set_freq(params.freq)
        self.at_values = np.linspace(params.flipStart, params.flipEnd, params.flipStep)
        print("Attenuation values : ", self.at_values)

        # Disable controls and start
        self.disable_controls()
        self.flipangle_run()
#_______________________________________________________________________________
#   Control Toolbox: Switch views depending on toolbox

    def switchPlot(self):
        def two_ax(self):
            if len(self.fig.axes) == 2: return
            self.fig.clear()#; self.fig.set_facecolor("None")
            self.ax1 = self.fig.add_subplot(2,1,1)
            self.ax2 = self.fig.add_subplot(2,1,2)
            #self.fig.delaxes(self.ax3)

        def three_ax(self):
            if len(self.fig.axes) == 3: return
            self.fig.clear()#; self.fig.set_facecolor("None")
            self.ax1 = self.fig.add_subplot(3,1,1)
            self.ax2 = self.fig.add_subplot(3,1,2)
            self.ax3 = self.fig.add_subplot(3,1,3)
            #self.fig.add_axes(self.ax3)

        self.progressBar_container.setVisible(True)

        self.update_params()
        params.saveFile()
        idx = self.toolBox.currentIndex()
        plotViews = {
            0: two_ax,
            1: three_ax,
            2: three_ax,
            3: two_ax # plot for shim tool == plot for manual aquisition
        }
        plotViews[idx](self)

        if idx == 0:
            print("-> Manual Acquisition Controlcenter")
            self.progressBar_container.setVisible(False)
        if idx == 1: print("-> Autocenter Conntrolcenter")
        if idx == 2: print("-> Flipangletool Controlcenter")
        if idx == 3: print("-> Shimmingtool Controlcenter")

        self.load_params()
        self.fig_canvas.draw()
        self.call_update.emit()
#_______________________________________________________________________________
#   Control Acquisition and Data Processing

    def set_sequence(self, idx): # Function to switch current sequence
        self.manualTI_input.setVisible(False)
        self.manualTILabel.setVisible(False)
        self.manualTE_input.setVisible(False)
        self.manualTELabel.setVisible(False)
        self.uploadSeq_btn.setVisible(False)
        self.uploadSeq_confirm.setVisible(False)

        seq = {
            0: self.data.set_FID,
            1: self.data.set_SE,
            2: self.data.set_IR,
            3: self.data.set_SIR,
            4: self.customSeq
        }

        if idx == 1:
            self.manualTE_input.setVisible(True)
            self.manualTELabel.setVisible(True)
        elif idx == 2 or idx == 3:
            self.manualTI_input.setVisible(True)
            self.manualTILabel.setVisible(True)
            if idx == 2:
                self.manualTI_input.disconnect()
                self.manualTI_input.valueChanged.connect(self.data.set_IR)
            else:
                self.manualTI_input.disconnect()
                self.manualTI_input.valueChanged.connect(self.data.set_SIR)

        seq[idx]()

    def customSeq(self):
        self.uploadSeq_btn.setVisible(True)
        self.uploadSeq_confirm.setVisible(True)
        self.uploadSeq_confirm.setChecked(False)
        self.disable_controls()

    def upload_sequence(self):
        print("Upload Sequence")
        sequence = QFileDialog.getOpenFileName(self, 'Upload Custom Sequence', QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), 'Textfile (*.txt)')
        self.data.set_uploaded_seq(sequence[0])

    def sequence_uploaded(self):
        self.uploadSeq_confirm.setChecked(True)
        self.enable_controls()

    def set_grad_offsets(self):

        gx = self.xOffset_input.value()
        gy = self.yOffset_input.value()
        gz = self.zOffset_input.value()
        gz2 = self.z2Offset_input.value()

        self.data.set_gradients(gx, gy, gz, gz2)

    def start_manual(self):
        if self.manualAvg_enable.isChecked(): self.init_averaging()
        else: self.data.acquire();

    def manual_center(self): # Function to apply the center frequency manually
        if self.data.center_freq != 'nan':
            self.manualFreq_input.setValue(round(self.data.center_freq,5))
            self.data.set_freq(self.data.center_freq)
            self.data.acquire()

    def acq_handler(self): # Function to handle current acquisition mode -- called whenever signal received
        print("Handling acquisition event.")

        # Set CC output parameters
        self.load_params()
        self.set_output(params.freq, params.at, self.data.center_freq,\
            self.data.peak_value, self.data.fwhm_value, self.data.snr)

        if self.seq_selector.currentIndex()==0: logger.add('ACQ', seq='FID',\
            peak=self.data.peak_value, fwhm=self.data.fwhm_value, snr=self.data.snr)
        if self.seq_selector.currentIndex()==1: logger.add('ACQ', seq='SE',\
            peak=self.data.peak_value, fwhm=self.data.fwhm_value, snr=self.data.snr)
        if self.seq_selector.currentIndex()==2: logger.add('ACQ', seq='IR',\
            peak=self.data.peak_value, fwhm=self.data.fwhm_value, snr=self.data.snr)

        # Make log entry

        if self.manualAvg_enable.isChecked(): # Handel averaging and manual trigger
            self.fft_mag_avg = np.add(self.fft_mag_avg, self.data.fft_mag)
            self.t_mag_avg = np.add(self.t_mag_avg, self.data.mag_t)
            self.t_real_avg = np.add(self.t_real_avg, self.data.real_t)
            self.t_imag_avg = np.add(self.t_imag_avg, self.data.imag_t)
            self.two_ax_plot()
            time.sleep(self.timeout)
            self.freqsweep_run()
            return

        if self.autocenter_flag == True: # Handel autocenter acquisition
            self.peaks.append(self.data.peak_value)
            if self.data.peak_value > self.peakValue and self.acqCount>0:
                # Change peak and center frequency value
                self.peakValue = self.data.peak_value
                self.centerValue = self.data.center_freq
                self.autocenter_output.setText(str(round(self.centerValue,4)))
            self.autocenter_plot() # calls 2-axis plot as well
            self.progressBar.setValue(self.acqCount/len(self.freqSpace)*100)
            self.call_update.emit()

            time.sleep(params.autoTimeout/1000)
            self.freqsweep_run()

        if self.flipangle_flag == True: # Handel flipangle tool acquisition
            if self.acqCount > 0:
                self.at_results.append(round(self.data.peak_value, 2))
            self.flipangle_plot() # calls 2-axis plot as well
            self.progressBar.setValue(self.acqCount/len(self.at_values)*100)
            self.call_update.emit()

            time.sleep(params.flipTimeout/1000)
            self.flipangle_run()

        else: self.two_ax_plot(); # Calls two axis plot for manual trigger

    def freqsweep_run(self): # Function for performing multiple freq acquisitions
        if self.acqCount < len(self.freqSpace):
            params.freq = self.freqSpace[self.acqCount]
            print("\nAcquisition counter: ", self.acqCount+1,"/",len(self.freqSpace),":")
            self.acqCount += 1
            self.data.set_freq(round(params.freq, 5))
            self.data.acquire()
        else:
            print("autocenter finished.")
            if self.autocenter_flag == True:
                params.freq = self.centerValue
                self.manualFreq_input.setValue(params.freq)
                self.autoCenter_save_btn.setEnabled(True)
                self.autocenter_flag = False
                print("set peak frequency: ", self.centerValue)
                self.data.set_freq(self.centerValue)
                self.data.acquire()
            self.enable_controls()

    def flipangle_run(self): # Function for performing multiple AT acquisitions
        if self.acqCount < len(self.at_values):
            params.at = self.at_values[self.acqCount]
            print("\nAcquisition counter: ", self.acqCount+1,"/",len(self.at_values),":")
            self.acqCount += 1
            self.data.set_at(params.at)
            self.data.acquire()
        else:
            self.flipangle_flag = False
            self.enable_controls()
            # init optional
            # init = [np.max(self.at_results), 1/(self.at_values[-1]-self.at_values[0]), np.min(self.at_results)]
            init = [np.max(self.at_results), 1/15, np.min(self.at_results)]

            self.flipangle_save_btn.setEnabled(True)

            try:
                self.fit_x, self.fit_at = self.fit_At(init)
                self.ax3.plot(self.fit_x, self.fit_at)
                self.fig_canvas.draw()
            except:
                print('ERROR: No fit found.')
                self.ax3.plot(abs(self.at_values), self.at_results)
                self.fig_canvas.draw()

            self.atPeak_output.setText(str(round(np.max(self.at_results), 2)))
            self.atMax_output.setText(str(round(self.at_values[np.argmax(self.at_results)], 2)))
            self.manualAt_input.setValue(self.at_values[np.argmax(self.at_results)])

    def fit_At(self, init): # Function that is optimizing the fit
        # parameters = sol(func, x, y, init, method)
        params, params_covariance = curve_fit(self.at_func, self.at_values, self.at_results, init, method='lm')
        x = np.arange(self.at_values[0], self.at_values[-1]+1, 0.1)
        fit = self.at_func(x, params[0], params[1], params[2])
        return x, fit

    def at_func(self, x, a, b, c): # Structure of sinus fitting for attenuation
        return abs(a * np.sin(b * x) + c)
#_______________________________________________________________________________
#   Set Output Parameters

    def set_output(self, freq, at, center, peak, fwhm, snr): # Setting all outputs
        self.freq_output.setText(str(round(freq, 5)))
        self.at_output.setText(str(round(at, 2)))
        self.center_output.setText(str(round(center, 5)))
        self.peak_output.setText(str(round(peak, 2)))
        self.fwhm_output.setText(str(round(fwhm, 2)))
        self.snr_output.setText(str(round(snr, 2)))

    def update_params(self):
        # Get params
        params.freq = self.manualFreq_input.value()
        params.at = self.manualAt_input.value()
        params.avgCyc = self.manualAvg_input.value()
        params.te = self.manualTE_input.value()
        params.ti = self.manualTI_input.value()
        params.autoSpan = self.freqSpan_input.value()
        params.autoStep = self.freqSteps_input.value()
        params.autoTimeout = self.freqTimeout_input.value()
        params.flipStart = self.atStart_input.value()
        params.flipEnd = self.atEnd_input.value()
        params.flipStep = self.atSteps_input.value()
        params.flipTimeout = self.atTimeout_input.value()

    def load_params(self):
        # Set params to GUI elements
        self.manualFreq_input.setValue(params.freq)
        self.manualAt_input.setValue(params.at)
        self.manualAvg_input.setValue(params.avgCyc)
        self.manualTE_input.setValue(params.te)
        self.manualTI_input.setValue(params.ti)
        self.freqCenter_input.setValue(params.freq)
        self.freqSpan_input.setValue(params.autoSpan)
        self.freqSteps_input.setValue(params.autoStep)
        self.freqTimeout_input.setValue(params.autoTimeout)
        self.atStart_input.setValue(params.flipStart)
        self.atEnd_input.setValue(params.flipEnd)
        self.atSteps_input.setValue(params.flipStep)
        self.atTimeout_input.setValue(params.flipTimeout)
#_______________________________________________________________________________
#   Plotting Data

    def two_ax_plot(self):
        if self.manualAvg_enable.isChecked():
            mag_t = self.t_mag_avg/self.acqCount
            real_t = self.t_real_avg/self.acqCount
            imag_t = self.t_imag_avg/self.acqCount
            fft_mag = self.fft_mag_avg/self.acqCount
        else:
            mag_t = self.data.mag_t; real_t = self.data.real_t; imag_t = self.data.imag_t
            fft_mag = self.data.fft_mag

        self.ax1.clear()
        self.ax1.plot(self.data.freqaxis[int(self.data.data_idx/2 - self.data.data_idx/10):int(self.data.data_idx/2 + self.data.data_idx/10)],
            fft_mag[int(self.data.data_idx/2 - self.data.data_idx/10):int(self.data.data_idx/2 + self.data.data_idx/10)])
        self.ax2.clear()
        self.ax2.plot(self.data.time_axis, mag_t, label='Magnitude')
        self.ax2.plot(self.data.time_axis, real_t, label='Real')
        self.ax2.plot(self.data.time_axis, imag_t, label='Imaginary')
        self.ax1.set_ylabel('RX amplitude []')
        self.ax1.set_xlabel('frequency [Hz]')
        self.ax2.set_ylabel('RX signal [mV]')
        self.ax2.set_xlabel('time [ms]')
        self.ax2.legend()
        self.fig_canvas.draw();

        self.call_update.emit()

    def autocenter_plot(self):
        self.ax3.plot(self.data.center_freq, self.data.peak_value,'x', color='#33A4DF')
        self.ax3.set_xlabel('center frequency [MHz]')
        self.ax3.set_ylabel('RX signal peak []')
        self.two_ax_plot()

    def flipangle_plot(self):
        self.ax3.plot(abs(self.at_values[self.acqCount-1]),self.at_results[self.acqCount-1], 'x', color='#33A4DF')
        self.ax3.set_xlabel('attenuation [dB]')
        self.ax3.set_ylabel('RX signal peak []')
        self.two_ax_plot()
#_______________________________________________________________________________
#   Save Data

    def save_flipangle(self):
        path = QFileDialog.getSaveFileName(self, 'Save Flipangle Data', QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), 'csv (*.csv)')
        if not path[0] == '':
            with open(path[0], mode='w', newline='') as file:
                writer = csv.writer(file, delimiter=',')
                writer.writerow(['Flipangletool Data', params.dataTimestamp])
                writer.writerow([''])
                writer.writerow(['attenuation [dB]', 'fft peak magnitude'])
                for n in range(len(self.at_values)):
                    writer.writerow([self.at_values[n], self.at_results[n]])
            print("\nFlipangledata saved.")

    def save_autocenter(self):
        path = QFileDialog.getSaveFileName(self, 'Save Flipangle Data', QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), 'csv (*.csv)')
        if not path[0] == '':
            with open(path[0], mode='w', newline='') as file:
                writer = csv.writer(file, delimiter=',')
                writer.writerow(['Autocenter Data', params.dataTimestamp])
                writer.writerow([''])
                writer.writerow(['frequency [MHz]', 'fft peak magnitude'])
                for n in range(len(self.freqSpace)):
                    writer.writerow([round(self.freqSpace[n],5), self.peaks[n]])
            print("\nAutosavedata saved.")
#_______________________________________________________________________________
#   Functions to Disable and enable control elements like buttons, spinboxes, etc.

    def disable_controls(self): # Function that disables controls
        self.manualAcqWidget.setEnabled(False)
        self.findCenterWidget.setEnabled(False)
        self.flipangleWidget.setEnabled(False)
        self.shimmingWidget.setEnabled(False)

    def enable_controls(self): # Function that enables controls
        self.manualAcqWidget.setEnabled(True)
        self.findCenterWidget.setEnabled(True)
        self.flipangleWidget.setEnabled(True)
        self.shimmingWidget.setEnabled(True)
