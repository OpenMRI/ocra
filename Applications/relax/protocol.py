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
matplotlib.use('Qt5Agg')
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
        # disable edit-function for even columns (0 included)

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
            self.protocol.setItem(row, 0, QTableWidgetItem('Start [ms] :'))
            self.protocol.setItem(row, 1, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 2, QTableWidgetItem('Stop [ms] :'))
            self.protocol.setItem(row, 3, QTableWidgetItem(str(600)))
            self.protocol.setItem(row, 4, QTableWidgetItem('Steps :'))
            self.protocol.setItem(row, 5, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 6, QTableWidgetItem('Recovery [ms] :'))
            self.protocol.setItem(row, 7, QTableWidgetItem(str(1000)))
            self.protocol.setItem(row, 6, QTableWidgetItem('Avg/Meas :'))
            self.protocol.setItem(row, 7, QTableWidgetItem(str(5)))
            self.protocol.setItem(row, 8, QTableWidgetItem('Avg/Data :'))
            self.protocol.setItem(row, 9, QTableWidgetItem(str(5)))
        def t2(self):
            self.meas_type.append("T2 Measurement")
            self.protocol.setItem(row, 0, QTableWidgetItem('Start [ms] :'))
            self.protocol.setItem(row, 1, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 2, QTableWidgetItem('Stop [ms] :'))
            self.protocol.setItem(row, 3, QTableWidgetItem(str(600)))
            self.protocol.setItem(row, 4, QTableWidgetItem('Steps :'))
            self.protocol.setItem(row, 5, QTableWidgetItem(str(10)))
            self.protocol.setItem(row, 6, QTableWidgetItem('Recovery [ms] :'))
            self.protocol.setItem(row, 7, QTableWidgetItem(str(1000)))
            self.protocol.setItem(row, 6, QTableWidgetItem('Avg/Meas :'))
            self.protocol.setItem(row, 7, QTableWidgetItem(str(5)))
            self.protocol.setItem(row, 8, QTableWidgetItem('Avg/Data :'))
            self.protocol.setItem(row, 9, QTableWidgetItem(str(5)))
        def temp(self):
            self.meas_type.append("Set Temperature")
            self.protocol.setItem(row, 0, QTableWidgetItem('Degrees [°C] :'))
            self.protocol.setItem(row, 1, QTableWidgetItem(str(37)))
        def pause(self):
            self.meas_type.append("Pause")
            self.protocol.setItem(row, 0, QTableWidgetItem('Duration [s] :'))
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

        self.start_btn.clicked.connect(self.popup)


    def init_figure(self):
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

    def popup(self):
        timeValue = 5000
        label = 'Pause'
        status = QProgressDialog('Status', 'Cancel', 0, timeValue, self)
        status.setLabelText(label)
        status.setWindowModality(Qt.ApplicationModal)
        status.show()
        for i in range(10):
            time.sleep((timeValue/10)/1000)
            status.setValue((i+1)*timeValue/10)



    # Function to start Acquisition, load/save protocol and output parameters
