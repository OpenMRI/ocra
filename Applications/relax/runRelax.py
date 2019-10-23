
#from matplotlib.figure import Figure
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import sys
import struct

# import PyQt5 packages
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget, \
    QLabel, QMessageBox, QCheckBox, QFileDialog, QShortcut
from PyQt5.uic import loadUiType, loadUi
from PyQt5.QtCore import QCoreApplication, QRegExp, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QRegExpValidator, QKeySequence
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket

# import calculation and plot packages
#import scipy.io as sp
#import matplotlib
#from math import pi
#matplotlib.use('Qt5Agg')

from ccSpectrometer import CCSpecWidget
from ccT2Relaxometer import CCRelaxT2Widget
from ccT1Relaxometer import CCRelaxT1Widget
from ccProtocol import CCProtocolWidget

from globalsocket import gsocket
from parameters import params
from assembler import Assembler
from dataprocessing import data

plt.rc('axes', prop_cycle=params.cycler)
plt.rcParams['lines.linewidth'] = 1
plt.rcParams['axes.grid'] = True
plt.rcParams['figure.autolayout'] = True
plt.rcParams['figure.dpi'] = 75


# load .ui files for different pages
Main_Window_Form, Main_Window_Base = loadUiType('ui/mainwindow.ui')

# main window
class MainWindow(Main_Window_Base, Main_Window_Form):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.ui = loadUi('ui/mainWindow.ui')
        self.setWindowTitle('Relax')

        params.loadParam()
        params.dispVars()

        self.setStyleSheet(params.stylesheet)
        self.plotTabWidget.setStyleSheet("border: 0.5px solid #BAB9B8; ")

        self.data = data()
        self.data.connectToHost()

        #self.quit = QShortcut(QKeySequence("Ctrl+Q"), self)
        #self.quit.activated.connect(self.quick_quit)

        self.plotTabWidget.setCurrentIndex(0)
        self.plotTabWidget.currentChanged.connect(self.switchView)

        self.switchView()

    def switchView(self):

        try: self.environment.update_params
        except: print("Could not update params.")
        try: self.environment.data.readout_finished.disconnect
        except: print("Finished readout signal not disconnected.")

        params.saveFile()
        self.resetLayout(self.ccLayout)

        idx = self.plotTabWidget.currentIndex()
        views = {
            0: self.setupSpectrometer,
            1: self.setupT1Relaxometer,
            2: self.setupT2Relaxometer,
            3: self.setupProtocol,
            4: self.setupLogbook
        }
        views[idx]()

    def resetLayout(self, layout):
        for i in range(layout.count()):
            layout.itemAt(0).widget().close()
            layout.takeAt(0)

    def setupSpectrometer(self):
        print("\n---Spectrometer---\n")

        self.resetLayout(self.spectrometerLayout)
        self.environment = CCSpecWidget()

        self.spectrometerLayout.addWidget(self.environment.fig_canvas)
        self.ccLayout.addWidget(self.environment)

    def setupT1Relaxometer(self):
        print("\n---T1 Relaxometer---\n")

        self.resetLayout(self.T1relaxLayout)
        self.environment = CCRelaxT1Widget()

        self.T1relaxLayout.addWidget(self.environment.fig_canvas)
        self.ccLayout.addWidget(self.environment)

    def setupT2Relaxometer(self):
        print("\n---T2 Relaxometer---\n")

        self.resetLayout(self.T2relaxLayout)
        self.environment = CCRelaxT2Widget()

        self.T2relaxLayout.addWidget(self.environment.fig_canvas)
        self.ccLayout.addWidget(self.environment)

    def setupProtocol(self):
        print("\n---Measurement Protocol---\n")

        self.resetLayout(self.spectrometerLayout)
        self.environment = CCProtocolWidget()
        #self.output = ... set output parameters on right side (CCLayout)

        self.ccProtocolLayout.addWidget(self.environment)
        self.protocolPlotLayout.addWidget(self.environment.fig_canvas)
        #self.ccLayout.addWidget(self.environment.CCoutput)

    def setupLogbook(self):
        print("\n---Logbook---\n")

    def closeEvent(self, event):
        params.saveFile()
        choice = QMessageBox.question(self, 'Close Relaxo', 'Are you sure that you want to quit Relax?',\
            QMessageBox.Cancel | QMessageBox.Close, QMessageBox.Cancel)
        if choice == QMessageBox.Close:
            params.dispVars()
            self.data.exit_host()
            event.accept()
        else: event.ignore()

# run
def run():

    print("\n________________________________________________________\n",\
    "Graphical user interface for relaxometry and spectroscopy. \n",\
    "Programmed by David Schote, OvGU Magdeburg, 2019\n",\
    "Stable build version 1.0",\
    "\n________________________________________________________\n")

    app = QApplication(sys.argv)
    gui = MainWindow()
    gui.show()
    sys.exit(app.exec_())

# main function
if __name__ == '__main__':
    run()
