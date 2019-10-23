# import general packages
import sys
import struct

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QTableWidgetItem
from PyQt5.uic import loadUiType, loadUi
#from PyQt5.QtCore import QCoreApplication, QRegExp, QObject, pyqtSignal
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket

# import calculation and plot packages
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from globalsocket import gsocket
from parameters import params
from dataprocessing import data

CC_Protocol_Form, CC_Protocol_Base = loadUiType('ui/ccProtocol.ui')

class CCProtocolWidget(CC_Protocol_Base, CC_Protocol_Form):
    def __init__(self):
        super(CCProtocolWidget, self).__init__()
        self.setupUi(self)

        self.data = data()
        self.init_figure()

        self.add_btn.clicked.connect(self.add_measurement)
        self.remove_btn.clicked.connect(self.remove_measurement)



    def init_figure(self):
        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

    def add_measurement(self, meas="T1-measurement", start=10, stop=1000, step=10, rec=1000, avg=0):

        row = self.protocol.rowCount()
        self.protocol.setRowCount(row)
        self.protocol.insertRow(row)
        print("Add row: ", row)

        print(type, start, stop, step, rec, avg)

        self.protocol.setItem(0, 0, QTableWidgetItem(str(meas)))
        self.protocol.setItem(1, 1, QTableWidgetItem(str(10)))
        self.protocol.setItem(2, 2, QTableWidgetItem(str(10)))
        self.protocol.setItem(3, 3, QTableWidgetItem(str(20)))
        self.protocol.setItem(4, 4, QTableWidgetItem(str(30)))
        self.protocol.setItem(5, 5, QTableWidgetItem(str(40)))
        #self.protocol.show()

    def remove_measurement(self):
        row = self.protocol.currentRow()
        self.protocol.removeRow(row)
