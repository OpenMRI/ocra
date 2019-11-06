# import general packages
import sys
import struct
import time

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QTableWidgetItem, QProgressDialog
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# import calculation and plot packages
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from globalsocket import gsocket
from parameters import params
from dataHandler import data

Protocol_Form, Protocol_Base = loadUiType('ui/protocol.ui')
CC_Protocol_Form, CC_Protocol_Base = loadUiType('ui/ccProtocol.ui')

class ProtocolWidget(Protocol_Base, Protocol_Form):
    def __init__(self):
        super(ProtocolWidget, self).__init__()
        self.setupUi(self)

        self.data = data()

        self.add_btn.clicked.connect(self.add_measurement)
        self.remove_btn.clicked.connect(self.remove_measurement)

        self.init_meas_list()

    def init_meas_list(self):

        self.meas_type = []
        self.measures_list.addItems(['T1 Measurement',\
            'T2 Measurement',\
            'Set Temperature',\
            'Pause',\
            'Change Sample'])
        self.measures_list.itemDoubleClicked.connect(self.add_measurement)

    def add_measurement(self):

        row = self.protocol.rowCount()
        self.protocol.setRowCount(row)
        self.protocol.insertRow(row)

        def t1(self):
            self.meas_type.append("T1 Measurement")
            self.protocol.setItem(row, 0, items.start())
            self.protocol.setItem(row, 1, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 2, items.stop())
            self.protocol.setItem(row, 3, QTableWidgetItem(str(600)))
            self.protocol.setItem(row, 4, items.steps())
            self.protocol.setItem(row, 5, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 6, items.recover())
            self.protocol.setItem(row, 7, QTableWidgetItem(str(1000)))
            self.protocol.setItem(row, 6, items.avgm())
            self.protocol.setItem(row, 7, QTableWidgetItem(str(5)))
            self.protocol.setItem(row, 8, items.avgd())
            self.protocol.setItem(row, 9, QTableWidgetItem(str(5)))
        def t2(self):
            self.meas_type.append("T2 Measurement")
            self.protocol.setItem(row, 0, items.start)
            self.protocol.setItem(row, 1, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 2, items.stop())
            self.protocol.setItem(row, 3, QTableWidgetItem(str(600)))
            self.protocol.setItem(row, 4, items.steps())
            self.protocol.setItem(row, 5, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 6, items.recover())
            self.protocol.setItem(row, 7, QTableWidgetItem(str(1000)))
            self.protocol.setItem(row, 6, items.avgm())
            self.protocol.setItem(row, 7, QTableWidgetItem(str(5)))
            self.protocol.setItem(row, 8, items.avgd())
            self.protocol.setItem(row, 9, QTableWidgetItem(str(5)))
        def temp(self):
            self.meas_type.append("Set Temperature")
            self.protocol.setItem(row, 0, items.deg())
            self.protocol.setItem(row, 1, QTableWidgetItem(str(37)))
        def pause(self):
            self.meas_type.append("Pause")
            self.protocol.setItem(row, 0, items.dur())
            self.protocol.setItem(row, 1, QTableWidgetItem(str(60)))
        def sample(self):
            self.meas_type.append("Change Sample")

        try: idx = self.measures_list.currentRow()
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

    def remove_measurement(self):
        try:
            row = self.protocol.currentRow()
            del self.meas_type[row]
            self.protocol.removeRow(row)
        except: return

    # Function for value changed:
        # update column linewidth
        # save value
    # Start Button

class CCProtocolWidget(CC_Protocol_Base, CC_Protocol_Form):
    def __init__(self):
        super(CCProtocolWidget, self).__init__()
        self.setupUi(self)

        self.init_figure()
        self.data = data()

        #self.start_btn.clicked.connect(self.start_protocol)

        ### Idee: ###
        # Emit signal, when start button clicked -> save table to parameters-class
        # Excess table parameters from parameters-class

    def init_figure(self):
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

    def waiting_popup(self, dur, label):
        status = QProgressDialog('Status', 'Cancel', 0, 100, self)
        status.setLabelText(label)
        status.setWindowModality(Qt.ApplicationModal)
        status.show()
        t=0
        while t < dur:
            time.sleep(1)
            t += 1000
            status.setValue(t*100/dur)

    def start_protocol(self):
        cycle = 0
        #exec = protocol.rowCount()

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
