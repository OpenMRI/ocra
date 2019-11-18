# import general packages
import sys
import struct
import time

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget, \
    QLabel, QMessageBox, QCheckBox, QFileDialog
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QCoreApplication, QRegExp, QObject, pyqtSignal

# import calculation and plot packages
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from parameters import params
from dataHandler import data
from dataLogger import logger

CC_2DImag_Form, CC_2DImag_Base = loadUiType('ui/cc2DImag.ui')

class CC2DImagWidget(CC_2DImag_Base, CC_2DImag_Form):

    call_update = pyqtSignal()

    def __init__(self):
        super(CC2DImagWidget, self).__init__()
        self.setupUi(self)

        self.data = data()

        self.fig = Figure()
        self.fig.set_facecolor("None")
        self.fig_canvas = FigureCanvas(self.fig)

        gs = GridSpec(3, 2, figure=self.fig)

        self.reco_ax = self.fig.add_subplot(gs[0:2,:])
        self.signals_ax = self.fig.add_subplot(gs[2,0])
        self.kspace_ax = self.fig.add_subplot(gs[2,1])
        # self.data.readout_finished.connect(self.update_dataplot)

        # self.imagStart_btn.clicked.connect(self.measureT1)
