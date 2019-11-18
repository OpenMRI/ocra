# import general packages
import sys
import struct
import time

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QTableWidgetItem, QProgressDialog, QDialog
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import Qt, pyqtSignal

# import calculation and plot packages
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from parameters import params
from dataHandler import data

Protocol_Form, Protocol_Base = loadUiType('ui/protocol.ui')
CC_Protocol_Form, CC_Protocol_Base = loadUiType('ui/ccProtocol.ui')
Popup_Dialog_Form, Popup_Dialog_Base = loadUiType('ui/prot_popup.ui')

class ProtocolWidget(Protocol_Base, Protocol_Form):

    call_update = pyqtSignal()

    def __init__(self):
        super(ProtocolWidget, self).__init__()
        self.setupUi(self)

        self.data = data()
        self.prot_ctrl = CCProtocolWidget()

        self.add_btn.clicked.connect(self.add_measurement)
        self.remove_btn.clicked.connect(self.remove_measurement)

        self.init_meas_list()

        self.prot_ctrl.execute.connect(self.start_meas)
        self.data.t1_finished.connect(self.plot_fit)
        self.data.t2_finished.connect(self.plot_fit)
        self.data.readout_finished.connect(self.plot_data)
        self.protocol.itemChanged.connect(self.protocol.resizeColumnsToContents)

        self.prot_ctrl.popup.event_finished.connect(self.continue_meas)

    def init_meas_list(self):

        self.meas_type = []
        self.measures_list.addItems(['T1 Measurement',\
            'T2 Measurement',\
            'Set Temperature',\
            'Pause',\
            'Change Sample'])
        self.measures_list.itemDoubleClicked.connect(self.add_measurement)
        self.ctrl_elements = [self.measures_list.item(n).text() for n in range(self.measures_list.count())]
#_______________________________________________________________________________
#   Add/Remove a command to the protocol

    def add_measurement(self):

        row = self.protocol.rowCount()
        self.protocol.setRowCount(row)
        self.protocol.insertRow(row)

        def t1(self):
            self.meas_type.append("T1 Measurement")
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
            self.meas_type.append("T2 Measurement")
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
            self.meas_type.append("Set Temperature")
            #self.protocol.setItem(row, 0, items.deg())
            #self.protocol.setItem(row, 1, QTableWidgetItem(str(37)))
        def pause(self):
            self.meas_type.append("Pause")
            self.protocol.setItem(row, 0, items.dur())
            self.protocol.setItem(row, 1, QTableWidgetItem(str(60)))
        def sample(self):
            self.meas_type.append("Change Sample")

        try:
            idx = self.measures_list.currentRow()
            if idx == -1: idx = 0
        except: return

        measures = {
            0: t1,
            1: t2,
            2: temp,
            3: pause,
            4: sample
        }
        measures[idx](self)
        self.protocol.resizeColumnsToContents()
        self.protocol.setVerticalHeaderLabels(self.meas_type)

        print(self.meas_type)

    def remove_measurement(self):
        try:
            row = self.protocol.currentRow()
            del self.meas_type[row]
            self.protocol.removeRow(row)
        except: return
#_______________________________________________________________________________
#   Handle execution of commands

    def start_meas(self):
        # Try to disable gui
        try: self.disable_prot()
        except: pass

        while self.meas_type != []:

            self.cmd = self.meas_type[0]

            # T1 or T2 measurement
            if self.cmd == self.ctrl_elements[0] or self.cmd == self.ctrl_elements[1]:

                start = int(self.protocol.item(0,1).text())
                stop = int(self.protocol.item(0,3).text())
                steps = int(self.protocol.item(0,5).text())
                t_vals = np.rint(np.logspace(np.log10(start), np.log10(stop), steps))

                recov = int(self.protocol.item(0,7).text())

                if int(self.protocol.item(0,9).text()) < 1 or \
                    int(self.protocol.item(0,11).text()) < 1:
                    avgm = 1; avgp = 1
                else:
                    avgm = int(self.protocol.item(0,9).text())
                    avgp = int(self.protocol.item(0,11).text())

                if self.cmd == self.ctrl_elements[0]:
                    self.clear_fig()
                    self.call_update.emit()
                    t1, t1_Rsq = self.data.T1_measurement(t_vals, params.freq, recov, avgM=avgm, avgP=avgp)
                    print("T1 is {} ms".format(t1))
                else:
                    self.clear_fig()
                    self.call_update.emit()
                    t2, t2_Tsq = self.data.T2_measurement(t_vals, params.freq, recov, avgM=avgm, avgP=avgp)
                    print("T2 is {} ms".format(t2))



            # Temperature
            elif self.cmd == self.ctrl_elements[2]:
                print('Wait for temperature set.')
                #print(self.protocol.item(0,1).text())
                self.prot_ctrl.popup.set('Temperature', 'inf', 'Set the chiller temperature and confirm!')
                #return

            # Pause
            elif self.cmd == self.ctrl_elements[3]:
                print('Pause.')
                dur = int(self.protocol.item(0,1).text())
                self.prot_ctrl.popup.set('Pause', dur, 'Pause protocol execution for {} seconds.'.format(dur/1000), progress=True)

            # Sample Exchange
            elif self.cmd == self.ctrl_elements[4]:
                print('Wait for sample exchange.')
                self.prot_ctrl.popup.set('Change Sample', 'inf', 'Change the sample and confirmed!')
                #return

            self.protocol.removeRow(0)
            del self.meas_type[0]
            self.call_update.emit()

            time.sleep(1)

    # Make protocol loop pause until popup closed !!!
    def continue_meas(self):
        self.protocol.removeRow(0)
        del self.meas_type[0]
        self.call_update.emit()

        if self.measures_list.count() == 0: self.enable_prot()
        else:
            time.sleep(1)
            self.start_meas()


    def disable_prot(self):
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)

    def enable_prot(self):
        self.add_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)

    # Function for value changed:
        # update column linewidth
        # save value
    # Start Button

#_______________________________________________________________________________
#   Handle execution of commands

    def plot_data(self):

        if self.cmd == "T1 Measurement": self.prot_ctrl.ax.plot(self.data.ti, self.data.peaks[-1], 'x', color='#33A4DF')
        elif self.cmd == "T2 Measurement": self.prot_ctrl.ax.plot(self.data.te, self.data.peaks[-1], 'x', color='#33A4DF')
        self.prot_ctrl.fig_canvas.draw(); self.call_update.emit()
        self.call_update.emit()
        print("Lines in plot: {}".format(self.prot_ctrl.ax.lines))

    def plot_fit(self):
        #if not len(self.prot_ctrl.ax.lines) == 0: self.prot_ctrl.ax.lines.remove(0)
        self.prot_ctrl.ax.plot(self.data.x_fit, self.data.y_fit, color='#4260FF')
        self.prot_ctrl.fig_canvas.draw(); self.call_update.emit()
        self.call_update.emit()

    def clear_fig(self):
        self.prot_ctrl.ax.clear()
        self.prot_ctrl.ax.set_ylabel('RX signal peak [mV]')
        if self.cmd == 'T1 Measurement': self.prot_ctrl.ax.set_xlabel('time of inversion (TI) [ms]')
        elif self.cmd == 'T2 Measurement': self.prot_ctrl.ax.set_xlabel('echo time (TE) [ms]')
        else: self.prot_ctrl.ax.set_xlabel('time [ms]')

#_______________________________________________________________________________
#   Protocol control widget: emit signals for protocol execution

class CCProtocolWidget(CC_Protocol_Base, CC_Protocol_Form):

    execute = pyqtSignal()

    def __init__(self, parent=None):
        super(CCProtocolWidget, self).__init__(parent)
        self.setupUi(self)

        self.init_figure()
        self.data = data()
        self.popup = protocol_popup()

        self.start_btn.clicked.connect(self.run_protocol)
        self.save_btn.clicked.connect(self.save_protocol)
        self.load_btn.clicked.connect(self.load_protocol)

    def init_figure(self):
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

    def save_protocol(self):
        print("Save protocol.")
        # Implementation...
        self.popup.set('Pause', 5000, 'This is a simple Pause of 5s.',progress=True)

    def load_protocol(self):
        print("Load protocol.")
        # Implementation...
        self.popup.set('Temperature', 'inf', 'Set the chiller temperature.')

    def run_protocol(self):
        print('Start measurement protocol.')
        self.execute.emit()

class protocol_popup(Popup_Dialog_Base, Popup_Dialog_Form):

    event_finished = pyqtSignal()

    def __init__(self, parent=None):
        super(protocol_popup, self).__init__(parent)
        self.setupUi(self)
        self.setStyleSheet(params.stylesheet)

        self.popup_btn.clicked.connect(self.close)

    def closeEvent(self, event):
        self.event_finished.emit()
        event.accept()

    def set(self, type, dur, text, **kwargs):
        progFlag = kwargs.get('progress', False)

        self.setWindowTitle(type)
        self.popup_label.setText(text)
        self.progressWidget.setVisible(progFlag)
        self.popup_btn.setVisible(not progFlag)

        self.show()

        if not dur == 'inf':
            T = 0
            while (T <= dur):
                if progFlag == True: self.popup_progress.setValue((T*100/(dur)))
                while QApplication.hasPendingEvents():
                    QApplication.processEvents()
                self.update()
                time.sleep(1)
                T += 1000
            self.close()
#_______________________________________________________________________________
#   Protocol item class

class items:

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
        item = QTableWidgetItem('Recovery [ms] :')
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

items = items()

    # Function to start Acquisition, load/save protocol and output parameters
