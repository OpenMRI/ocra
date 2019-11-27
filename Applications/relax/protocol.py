# import general packages
import time
import csv

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QTableWidgetItem, QFileDialog, QDesktopWidget
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import Qt, pyqtSignal, QStandardPaths

# import calculation and plot packages
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from parameters import params
from dataHandler import data
from dataLogger import logger

Protocol_Form, Protocol_Base = loadUiType('ui/protocol.ui')
CC_Protocol_Form, CC_Protocol_Base = loadUiType('ui/ccProtocol.ui')
Popup_Dialog_Form, Popup_Dialog_Base = loadUiType('ui/prot_popup.ui')

class ProtocolWidget(Protocol_Base, Protocol_Form):

    call_update = pyqtSignal()
    update_output = pyqtSignal()

    def __init__(self, parent=None):
        super(ProtocolWidget, self).__init__(parent)
        self.setupUi(self)

        self.data = data()
        self.protocolCC = CCProtocolWidget(self)
        self.init_meas_list()
        self.fitPlottedFlag = False

        self.add_btn.clicked.connect(self.add_measurement)
        self.remove_btn.clicked.connect(self.remove_measurement)

        self.protocolCC.execute.connect(self.init_protocol_exec)

        self.data.t1_finished.connect(self.plot_fit)
        self.data.t2_finished.connect(self.plot_fit)
        self.data.readout_finished.connect(self.plot_data)

        self.protocol.itemChanged.connect(self.protocol.resizeColumnsToContents)

        self.freqCalib = [20.08, 20.10, 20.12]

    # Init list with commands
    def init_meas_list(self):
        self.cmdList = []
        self.cmd_list.addItems(['T1 Measurement',\
            'T2 Measurement',\
            'Pause',\
            'Set Temperature',\
            'Change Sample',\
            'Calibrate Frequency'])
        self.cmd_list.itemDoubleClicked.connect(self.add_measurement)
        self.cmdElements = [self.cmd_list.item(n).text() for n in range(self.cmd_list.count())]
#_______________________________________________________________________________
#   Add/Remove a command to the protocol

    # Add a command to protocol
    def add_measurement(self):

        row = self.protocol.rowCount()
        self.protocol.setRowCount(row)
        self.protocol.insertRow(row)

        def t1(self):
            self.cmdList.append("T1 Measurement")
            self.protocol.setItem(row, 0, items.start())
            self.protocol.setItem(row, 1, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 2, items.stop())
            self.protocol.setItem(row, 3, QTableWidgetItem(str(500)))
            self.protocol.setItem(row, 4, items.steps())
            self.protocol.setItem(row, 5, QTableWidgetItem(str(5)))
            self.protocol.setItem(row, 6, items.recover())
            self.protocol.setItem(row, 7, QTableWidgetItem(str(1000)))
            self.protocol.setItem(row, 8, items.avgm())
            self.protocol.setItem(row, 9, QTableWidgetItem(str(1)))
            self.protocol.setItem(row, 10, items.avgd())
            self.protocol.setItem(row, 11, QTableWidgetItem(str(1)))
        def t2(self):
            self.cmdList.append("T2 Measurement")
            self.protocol.setItem(row, 0, items.start())
            self.protocol.setItem(row, 1, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 2, items.stop())
            self.protocol.setItem(row, 3, QTableWidgetItem(str(250)))
            self.protocol.setItem(row, 4, items.steps())
            self.protocol.setItem(row, 5, QTableWidgetItem(str(5)))
            self.protocol.setItem(row, 6, items.recover())
            self.protocol.setItem(row, 7, QTableWidgetItem(str(500)))
            self.protocol.setItem(row, 8, items.avgm())
            self.protocol.setItem(row, 9, QTableWidgetItem(str(1)))
            self.protocol.setItem(row, 10, items.avgd())
            self.protocol.setItem(row, 11, QTableWidgetItem(str(1)))
        def temp(self):
            self.cmdList.append("Set Temperature")
        def pause(self):
            self.cmdList.append("Pause")
            self.protocol.setItem(row, 0, items.dur())
            self.protocol.setItem(row, 1, QTableWidgetItem(str(60)))
        def sample(self):
            self.cmdList.append("Change Sample")
        def calib(self):
            self.cmdList.append("Calibrate Frequency")

        try:
            idx = self.cmd_list.currentRow()
            if idx == -1: idx = 0
        except: return

        measures = {
            0: t1,
            1: t2,
            2: pause,
            3: temp,
            4: sample,
            5: calib
        }
        measures[idx](self)
        self.protocol.resizeColumnsToContents()
        self.protocol.setVerticalHeaderLabels(self.cmdList)
        self.stepsCount = len(self.cmdList)

    # Remove a cmd from protocol
    def remove_measurement(self):
        row = self.protocol.currentRow()
        if row >= 0:
            del self.cmdList[row]
            self.protocol.removeRow(row)

#_______________________________________________________________________________
#   Handle execution of commands

    # Init protocol execution
    def init_protocol_exec(self):
        if self.cmdList == []: return
        print("Commands:\t {}".format(self.cmdList))

        self.disable_prot()
        self.protocolCC.update()

        dur, self.progVals = self.estimate_duration()
        self.protocolCC.execProgress.setValue(0)
        self.protocolCC.set_constant_output_params(dur, params.freq, params.at)

        self.protocol_exec()

    # Execute protocol loop
    def protocol_exec(self):
        '''
        # Implement switch-case for protocol execution
        def measurement(): # Measure T1 or T2
            start = int(self.protocol.item(0,1).text())
            stop = int(self.protocol.item(0,3).text())
            steps = int(self.protocol.item(0,5).text())
            tVals = np.rint(np.logspace(np.log10(start), np.log10(stop), steps))
            recovery = int(self.protocol.item(0,7).text())
            self.fitPlottedFlag = False

            if int(self.protocol.item(0,9).text()) < 1 or \
                int(self.protocol.item(0,11).text()) < 1:
                avgm = 1; avgp = 1
            else:
                avgm = int(self.protocol.item(0,9).text())
                avgp = int(self.protocol.item(0,11).text())

            self.clear_fig()
            self.call_update.emit()
            if self.cmd == self.cmdElements[0]:
                t1, t1_Rsq = self.data.T1_measurement(tVals, params.freq, recovery, avgM=avgm, avgP=avgp)
                logger.add('T1', res=t1, err=t1_Rsq, val=tVals, seq='SIR', avgM=avgm, avgP=avgp)
                self.protocolCC.update_output_params(t1Res=t1, t1Err=t1_Rsq)
            else:
                t2, t2_Rsq = self.data.T2_measurement(tVals, params.freq, recovery, avgM=avgm, avgP=avgp)
                logger.add('T2', res=t2, err=t2_Rsq, val=tVals, avgM=avgm, avgP=avgp)
                self.protocolCC.update_output_params(t2Res=t2, t2Err=t2_Rsq)
        def pause(): # Pause execution
            print('Pause.')
            ptime = int(self.protocol.item(0,1).text())
            logger.add('PAUSE', dur=ptime)
            self.popup.show()
            self.popup.set(ptime, 'Pause protocol execution for {} seconds.'.format(ptime), progress=True)
            break
        def temperature(): # Set temperature
            print('Wait for temperature set.')
            logger.add('TEMP')
            self.popup.show()
            self.popup.set(-1, 'Set the chiller temperature and confirm!', btnTxt='Confirm')
            break
        def sample(): # Exchange sample
            print('Wait for sample exchange.')
            logger.add('CHNG')
            self.popup.show()
            self.popup.set(-1, 'Change the sample and confirmed!', btnTxt='Confirm')
            break
        def calibration(): # Calibrate the system
            self.protocolCC.update()
            print("Calibrate Frequency.")
            self.sys_calibrate()
            if self.data.peak_value < 50:
                self.popup.show()
                self.popup.set(-1, 'Calibration was not successful!\n Please calibrate manually.', btnTxt='Ok')
                logger.add('CAL', status=False)
                self.enable_prot()
                break
            else: logger.add('CAL')
        '''
        while self.cmdList != []: # while cmd list is not empty
            self.cmd = self.cmdList[0] # Get actual command
            self.protocolCC.update_output_params(step=str(self.stepsCount+1-len(self.cmdList))+'/'+str(self.stepsCount))
            self.protocolCC.execProgress.setValue(sum(self.progVals\
                [0:self.stepsCount-len(self.cmdList)])*100/sum(self.progVals))

            # T1 or T2 measurement
            if self.cmd == self.cmdElements[0] or self.cmd == self.cmdElements[1]:

                start = int(float(self.protocol.item(0,1).text()))
                stop = int(float(self.protocol.item(0,3).text()))
                steps = int(float(self.protocol.item(0,5).text()))
                tVals = np.rint(np.logspace(np.log10(start), np.log10(stop), steps))

                recovery = int(float(self.protocol.item(0,7).text()))

                self.fitPlottedFlag = False

                if int(float(self.protocol.item(0,9).text())) < 1 or \
                    int(float(self.protocol.item(0,11).text())) < 1:
                    avgm = 1; avgp = 1
                else:
                    avgm = int(float(self.protocol.item(0,9).text()))
                    avgp = int(float(self.protocol.item(0,11).text()))

                self.clear_fig()
                self.call_update.emit()

                if self.cmd == self.cmdElements[0]:
                    t1, t1_Rsq = self.data.T1_measurement(tVals, params.freq, recovery, avgM=avgm, avgP=avgp)
                    logger.add('T1', res=t1, err=t1_Rsq, val=tVals, seq='SIR', avgM=avgm, avgP=avgp)
                    self.protocolCC.update_output_params(t1Res=t1, t1Err=t1_Rsq)
                else:
                    t2, t2_Rsq = self.data.T2_measurement(tVals, params.freq, recovery, avgM=avgm, avgP=avgp)
                    logger.add('T2', res=t2, err=t2_Rsq, val=tVals, avgM=avgm, avgP=avgp)
                    self.protocolCC.update_output_params(t2Res=t2, t2Err=t2_Rsq)

            # Pause, Temperature, Change Sample
            else: # Not T1 or T2
                self.popup = protocol_popup(parent=self)
                self.popup.event_finished.connect(self.continue_protocol_exec)
                # Pause
                if self.cmd == self.cmdElements[2]:
                    print('Pause.')
                    pause = int(float(self.protocol.item(0,1).text()))
                    logger.add('PAUSE', dur=pause)
                    self.popup.show()
                    self.popup.set(pause, 'Pause protocol execution for {} seconds.'.format(pause), progress=True)
                    break
                # Change Temperature
                elif self.cmd == self.cmdElements[3]:
                    print('Wait for temperature set.')
                    logger.add('TEMP')
                    self.popup.show()
                    self.popup.set(-1, 'Set the chiller temperature and confirm!', btnTxt='Confirm')
                    break
                # Sample Exchange
                elif self.cmd == self.cmdElements[4]:
                    print('Wait for sample exchange.')
                    logger.add('CHNG')
                    self.popup.show()
                    self.popup.set(-1, 'Change the sample and confirmed!', btnTxt='Confirm')
                    break
                # Frequency Calibration
                elif self.cmd == self.cmdElements[5]:
                    self.protocolCC.update()
                    print("Calibrate Frequency.")
                    self.sys_calibrate()
                    if self.data.peak_value < 50:
                        self.popup.show()
                        self.popup.set(-1, 'Calibration was not successful!\n Please calibrate manually.', btnTxt='Ok')
                        logger.add('CAL', status=False)
                        self.enable_prot()
                        break
                    else: logger.add('CAL')

            '''
            if not self.cmd == self.cmdElements[0] and not self.cmdElements[1]:
                self.popup = protocol_popup(parent=self)
                self.popup.event_finished.connect(self.continue_protocol_exec)

            tasks = {
                0: measurement,
                1: measurement,
                2: pause,
                3: temperature,
                4: sample,
                5: calibration
            }

            tasks[self.cmd]()
            '''

            # Remove executed command
            self.protocol.removeRow(0)
            del self.cmdList[0]
            self.call_update.emit()

        # Protocol execution finished
        if self.cmdList == []:
            self.protocolCC.execProgress.setValue(sum(self.progVals\
                [0:self.stepsCount-len(self.cmdList)])*100/sum(self.progVals))
            self.enable_prot()
            print("Finished protocol execution. \n")

    # System calibration
    def sys_calibrate(self):
        peaks = []; freqs = []
        self.data.set_FID()
        self.data.readout_finished.disconnect()
        for freq in self.freqCalib:
            self.clear_fig()
            self.data.set_freq(freq)
            self.data.acquire()
            peaks.append(self.data.peak_value)
            freqs.append(self.data.center_freq)
        params.freq = freqs[np.argmax(peaks)]
        self.clear_fig()
        self.data.readout_finished.connect(self.plot_data)
        self.data.set_freq(params.freq)
        self.data.acquire()

    # Continue protocol after pause, temperature set or sample change
    def continue_protocol_exec(self):
        self.popup.event_finished.disconnect()
        self.popup.close()
        self.call_update.emit()
        if not self.cmd == self.cmdElements[5]:
            self.protocol.removeRow(0)
            del self.cmdList[0]
            time.sleep(0.5)
            self.protocol_exec()

    # Function to disable protocol controls
    def disable_prot(self):
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.protocolCC.start_btn.setEnabled(False)
        self.protocolCC.save_btn.setEnabled(False)
        self.protocolCC.load_btn.setEnabled(False)

    # Function to enable protocol controls
    def enable_prot(self):
        self.add_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        self.protocolCC.start_btn.setEnabled(True)
        self.protocolCC.save_btn.setEnabled(True)
        self.protocolCC.load_btn.setEnabled(True)

    # Function to estimate duration of protocol execution
    def estimate_duration(self):
        dur = 0
        progressValues = []
        for n in range(len(self.cmdList)):
            cmd = self.cmdList[n]
            if cmd == self.cmdElements[0] or cmd == self.cmdElements[1]:
                start = int(float(self.protocol.item(n,1).text()))
                stop = int(float(self.protocol.item(n,3).text()))
                steps = int(float(self.protocol.item(n,5).text()))
                tVals = np.rint(np.logspace(np.log10(start), np.log10(stop), steps))
                recovery = int(float(self.protocol.item(n,7).text()))
                if int(float(self.protocol.item(n,9).text())) < 1 or \
                    int(float(self.protocol.item(n,11).text())) < 1: avgm = 1; avgp = 1
                else:
                    avgm = int(float(self.protocol.item(n,9).text()))
                    avgp = int(float(self.protocol.item(n,11).text()))
                progressValues.append(2*(sum(tVals)+len(tVals)*recovery)*avgp*avgp/1000)
            elif cmd == self.cmdElements[2]: progressValues.append(int(float(self.protocol.item(n,1).text())))
            elif cmd == self.cmdElements[5]: progressValues.append(7) # 7s for calibration
            else: progressValues.append(10) # 10s default for temperature or sample change
            dur += progressValues[-1]
        dur += len(self.cmdList) # add additional 1.0s for every command -> computation time
        return round(dur,2), progressValues

#_______________________________________________________________________________
#   Plot Data from Acquisitions

    def plot_data(self):
        if self.fitPlottedFlag == True:
            self.clear_fig()
            self.fitPlottedFlag = False
        if self.cmd == "T1 Measurement": self.protocolCC.ax.plot(self.data.ti, self.data.peaks[-1], 'x', color='#33A4DF')
        elif self.cmd == "T2 Measurement": self.protocolCC.ax.plot(self.data.te, self.data.peaks[-1], 'x', color='#33A4DF')
        else: self.protocolCC.ax.plot(self.data.freqaxis[int(self.data.data_idx/2 - self.data.data_idx/10):int(self.data.data_idx/2 + self.data.data_idx/10)],\
            self.data.fft_mag[int(self.data.data_idx/2 - self.data.data_idx/10):int(self.data.data_idx/2 + self.data.data_idx/10)])
        self.protocolCC.fig_canvas.draw(); self.call_update.emit()
        self.call_update.emit()

    def plot_fit(self):
        self.protocolCC.ax.plot(self.data.x_fit, self.data.y_fit, color='#4260FF')
        self.protocolCC.fig_canvas.draw(); self.call_update.emit()
        self.call_update.emit()
        self.fitPlottedFlag = True

    def clear_fig(self):
        self.protocolCC.ax.clear()
        self.protocolCC.ax.set_ylabel('RX signal amplitude [mV]')
        if self.cmd == 'T1 Measurement': self.protocolCC.ax.set_xlabel('time of inversion (TI) [ms]')
        elif self.cmd == 'T2 Measurement': self.protocolCC.ax.set_xlabel('echo time (TE) [ms]')
        else: self.protocolCC.ax.set_xlabel('frequency [Hz]')

#_______________________________________________________________________________
#   Save and Load Protocol

    def save_protocol(self):
        print('Saving protocol.')
        colIdx = [1,3,5,7,9,11]
        values = []
            #print("row: {}, col: {}".format(row, col))
        for row in range(self.protocol.rowCount()):
            if not any([self.protocol.item(row,col) is None for col in colIdx]):
                rowVals = [int(self.protocol.item(row,col).text()) for col in colIdx]
            elif not self.protocol.item(row,1) is None:
                rowVals = [int(self.protocol.item(row,1).text())] + [None]*len(colIdx[1:-1])
            else: rowVals = [None]*len(colIdx)
            values.append(rowVals)
        if values == []:
            print("Empty protocol.")
            return
        else:
            dataframe = pd.DataFrame(data=values, index=self.cmdList, columns=['t_start','t_stop','steps','recovery','avg_datp','avg_meas'])
            print(dataframe)
            path = QFileDialog.getSaveFileName(self, 'Save Acquisitiondata', QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), 'csv (*.csv)')
            if not path[0] == '':
                with open(path[0],'w') as file:
                    file.write('Relax Measurement Protocol \n key=00 \n\n' + dataframe.to_csv())

    def load_protocol(self):
        print('Load protocol.')
        colIdx = [1,3,5,7,9,11]
        path = QFileDialog.getOpenFileName(self, "Load Protocol", "/home", "csv (*.csv)")
        try:
            if not path[0] == '':
                with open(path[0]) as file:
                    csvread = csv.reader(file)
                    for row in csvread:
                        if row!=[] and row[0] in self.cmdElements:
                            self.cmdList.append(row[0])
                            prow = self.protocol.rowCount()
                            self.protocol.insertRow(prow)
                            if row[0] == self.cmdElements[0] or row[0] == self.cmdElements[1]:
                                self.protocol.setItem(prow, 0, items.start())
                                self.protocol.setItem(prow, 2, items.stop())
                                self.protocol.setItem(prow, 4, items.steps())
                                self.protocol.setItem(prow, 6, items.recover())
                                self.protocol.setItem(prow, 8, items.avgm())
                                self.protocol.setItem(prow, 10, items.avgd())
                            elif row[0] == self.cmdElements[2]: self.protocol.setItem(prow, 0, items.dur())
                            for n in range(len(row[:])-1):
                                self.protocol.setItem(prow, colIdx[n], QTableWidgetItem(str(row[n+1])))
                    self.protocol.setVerticalHeaderLabels(self.cmdList)
                    self.stepsCount = len(self.cmdList)
                    #print(self.cmdList)
        except: print('Protocol not readable.')

#_______________________________________________________________________________
#   Protocol control widget: emit signals for protocol execution

class CCProtocolWidget(CC_Protocol_Base, CC_Protocol_Form):

    execute = pyqtSignal()

    def __init__(self):
        super(CCProtocolWidget, self).__init__()
        self.setupUi(self)

        self.init_figure()
        self.data = data()

        self.protocol = parent

        self.start_btn.clicked.connect(self.run_protocol)
        self.save_btn.clicked.connect(self.protocol.save_protocol)
        self.load_btn.clicked.connect(self.protocol.load_protocol)

    def init_figure(self):
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

    def run_protocol(self):
        print('Start measurement protocol.')
        self.execute.emit()

    def set_constant_output_params(self, dur, freq, at):
        self.dur_output.setText(str(dur)+' s')
        self.freq_output.setText(str(freq))
        self.at_output.setText(str(at))

    def update_output_params(self, **kwargs):
        step = kwargs.get('step', None)
        temp = kwargs.get('temp', None)
        t1 = kwargs.get('t1Res', None)
        t1r2 = kwargs.get('t1Err', None)
        t2 = kwargs.get('t2Res', None)
        t2r2 = kwargs.get('t2Err', None)

        if not step == None: self.step_output.setText(step)
        #if not temp == None: self.temp_output.setText(str(temp)+' °C')
        self.temp_output.setText(str(temp)+' °C')
        if not t1 == None: self.t1_output.setText(str(round(t1,2)))
        if not t1r2 == None: self.t1r2_output.setText(str(t1r2))
        if not t2 == None: self.t2_output.setText(str(round(t2,2)))
        if not t2r2 == None: self.t2r2_output.setText(str(t2r2))
#_______________________________________________________________________________
#   Protocol popup widget: set temperature, change sample or pause dialog

class protocol_popup(Popup_Dialog_Base, Popup_Dialog_Form):

    event_finished = pyqtSignal()

    def __init__(self, parent=None):
        super(protocol_popup, self).__init__(parent, Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setupUi(self)
        self.setStyleSheet(params.stylesheet)
        self.popup_btn.clicked.connect(self.closeEvent)
        self.popup_btn.setVisible(False)
        # Center window on screen
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

    def closeEvent(self, event):
        self.event_finished.emit()

    def set(self, dur, text, **kwargs):
        progFlag = kwargs.get('progress', False)
        btn = kwargs.get('btnTxt')

        self.popup_label.setText(text)
        self.progressWidget.setVisible(progFlag)

        if btn:
            self.popup_btn.setText(btn)
            self.popup_btn.setVisible(True)

        QApplication.processEvents()

        if not dur == -1:
            dur = dur*1000 # transform: ms -> s
            T = 0
            while (T <= dur):
                if progFlag == True: self.popup_progress.setValue((T*100/(dur)))
                QApplication.processEvents()
                self.update()
                time.sleep(1)
                T += 1000

            self.closeEvent(True)

#_______________________________________________________________________________
#   Protocol item class

class Items:

    def start(self):
        item = QTableWidgetItem('Start [ms] :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def stop(self):
        item = QTableWidgetItem('Stop [ms] :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def steps(self):
        item = QTableWidgetItem('Steps :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def recover(self):
        item = QTableWidgetItem('self.recoveryery [ms] :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def avgm(self):
        item = QTableWidgetItem('Avg/Meas :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def avgd(self):
        item = QTableWidgetItem('Avg/Data :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def deg(self):
        item = QTableWidgetItem('Degrees [°C] :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def dur(self):
        item = QTableWidgetItem('Duration [s] :')
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

items = Items()

    # Function to start Acquisition, load/save protocol and output parameters
