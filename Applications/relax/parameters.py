import sys
import pickle

from PyQt5.QtCore import QFile, QTextStream
from cycler import cycler

# Append stylesheetpath to library
sys.path.append('ui/breezeStylesheet')
import breeze_resources

class Parameters:
    def __init__(self):
        # Read stylesheet
        file = QFile(":/light.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)

        self.stylesheet = stream.readAll()
        self.cycler = cycler(color=['#33A4DF', '#4260FF', '#001529'])

        self.ip = []

    def var_init(self): # Init internal GUI parameter with defaults
        print("Setting default parameters.")
        self.hosts = ['172.20.125.84']
        self.freq = 20.10000
        self.at = 22
        self.avgFlag = False
        self.avgCyc = 5
        self.te = 10
        self.ti = 200
        self.autoSpan = 0.4
        self.autoStep = 6
        self.autoTimeout = 2000
        self.flipStart = 1
        self.flipEnd = 31
        self.flipStep = 15
        self.flipTimeout = 4000
        self.t2Start = 10
        self.t2End = 100
        self.t2Step = 10
        self.t2Recovery = 10
        self.t2avgM = 2
        self.t2avgP = 3
        self.t1Start = 50
        self.t1End = 5000
        self.t1Step = 10
        self.t1Recovery = 200
        self.t1avgM = 2
        self.t1avgP = 3
        self.temp = float('nan')
        self.freqaxis = []
        self.data = []
        self.fft = []
        self.dataTimestamp = ''

        # Add parameters: Last tool index, last tab widget index, (maybe) last aquired data/axes, averaging enabled

    def saveFile(self): # Save internal GUI parameter to pickle-file
        with open('parameters.pkl', 'wb') as file:
            pickle.dump([self.hosts,\
                self.freq,\
                self.at,\
                self.avgFlag,\
                self.avgCyc,\
                self.te,\
                self.ti,\
                self.autoSpan,\
                self.autoStep,\
                self.autoTimeout,\
                self.flipStart,\
                self.flipEnd,\
                self.flipStep,\
                self.flipTimeout,\
                self.t2Start,\
                self.t2End,\
                self.t2Step,\
                self.t2Recovery,\
                self.t2avgM,\
                self.t2avgP,\
                self.t1Start,\
                self.t1End,\
                self.t1Step,\
                self.t1Recovery,\
                self.t1avgM,\
                self.t1avgP,\
                self.temp,\
                self.freqaxis,\
                self.data,\
                self.fft,\
                self.dataTimestamp], file)
        print("Parameter saved.")
        #self.dispVars()

    def loadParam(self): # Load internal GUI parameter from pickle-file
        try:
            with open('parameters.pkl', 'rb') as file:
                self.hosts,\
                self.freq,\
                self.at,\
                self.avgFlag,\
                self.avgCyc,\
                self.te,\
                self.ti,\
                self.autoSpan,\
                self.autoStep,\
                self.autoTimeout,\
                self.flipStart,\
                self.flipEnd,\
                self.flipStep,\
                self.flipTimeout,\
                self.t2Start,\
                self.t2End,\
                self.t2Step,\
                self.t2Recovery,\
                self.t2avgM,\
                self.t2avgP,\
                self.t1Start,\
                self.t1End,\
                self.t1Step,\
                self.t1Recovery,\
                self.t1avgM,\
                self.t1avgP,\
                self.temp,\
                self.freqaxis,\
                self.data,\
                self.fft,\
                self.dataTimestamp = pickle.load(file)
                print("Internal GUI parameter successfully restored from file.")
                #self.dispVars()
        except:
            print("Parameter could not have been restored, setting default.")
            self.var_init()
            #self.dispVars()

    def dispVars(self): # Display current internal GUI parameter
        print("Internal GUI parameter:\n")
        print("Frequency:\t", self.freq, "\tMHz")
        print("Attenuation:\t", self.at, "\tdB")
        print("Avg. cycles:\t", self.avgCyc)
        print("Echo time TE:\t", self.te, "\tms")
        print("Time of inversion TI:\t", self.ti, "\tms")
        print("Autocenter span:\t", self.autoSpan, "\tMHz")
        print("Autocenter steps:\t", self.autoStep)
        print("Autocenter timeout:\t", self.autoTimeout, "\tms")
        print("Flipangletool start:\t", self.flipStart, "\tdB")
        print("Flipangletool stop:\t", self.flipEnd, "\tdB")
        print("Flipangletool step:\t", self.flipStep)
        print("Flipangletool timeout:\t", self.flipTimeout, "\tms")
        print("TE start value:\t", self.t2Start, "\tms")
        print("TE last value:\t", self.t2End, "\tms")
        print("t2 steps:\t", self.t2Step)
        print("t2 recovery:\t", self.t2Recovery, "\ts")
        print("t2 averages/meas:\t", self.t2avgM)
        print("t2 averages/data:\t", self.t2avgP)
        print("TI start value:\t", self.t1Start, "\tms")
        print("TI last value:\t", self.t1End, "\tms")
        print("t1 steps:\t", self.t1Step)
        print("t1 recovery:\t", self.t1Recovery, "\tms")
        print("t1 averages/meas:\t", self.t1avgM)
        print("t1 averages/data:\t", self.t1avgP)
        print("Temperature:\t", self.temp, "\t°C")
        print("\n")

params = Parameters()
