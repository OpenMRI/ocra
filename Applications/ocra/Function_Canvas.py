
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import re
import math
import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class Canvas_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(718, 515)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(370, 470, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.widget = QtWidgets.QWidget(Dialog)
        self.widget.setGeometry(QtCore.QRect(10, 10, 691, 451))
        self.widget.setObjectName("widget")
        self.groupBox = QtWidgets.QGroupBox(self.widget)
        self.groupBox.setGeometry(QtCore.QRect(0, 0, 691, 451))
        self.groupBox.setObjectName("groupBox")

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.groupBox.setTitle(_translate("Dialog", "Function Drawing Out:"))

#创建一个matplotlib图形绘制类
class MyFigure(FigureCanvas):
    def __init__(self,width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MyFigure,self).__init__(self.fig) #此句必不可少，否则不能显示图形
        self.axes = self.fig.add_subplot(111)
                    
    def plotfunc(self,flagReceiver):
        if flagReceiver[0]=='+':
            regex1=r'Amplitude:([\s\S]*) Increase duration:'
            regex2=r' Increase duration:([\s\S]*) Holding duration:'
            regex3=r' Holding duration:([\s\S]*) Decrease duration:'
            regex4=r' Decrease duration:([\s\S]*) The END'
            x1=float((re.findall(regex1, flagReceiver)[0]))
            x2=float((re.findall(regex2, flagReceiver)[0]))
            x3=float((re.findall(regex3, flagReceiver)[0]))
            x4=float((re.findall(regex4, flagReceiver)[0]))
            x=[0,50,50+x2,50+x2+x3,50+x2+x3+x4,100+x2+x3+x4]
            y=[0,0,x1,x1,0,0]
            self.axes.plot(x,y,c='red')
            del x[0],x[-1]
            del y[0],y[-1]
            for a,b in zip(x,y):
                self.axes.text(a,b,(a,b),ha='center',va='bottom',fontsize=10)
        elif flagReceiver[0]=='-':
            regex1=r'Amplitude:([\s\S]*) Increase duration:'
            regex2=r' Increase duration:([\s\S]*) Holding duration:'
            regex3=r' Holding duration:([\s\S]*) Decrease duration:'
            regex4=r' Decrease duration:([\s\S]*) The END'
            x1=(-1.0)*float((re.findall(regex1, flagReceiver)[0]))
            x2=float((re.findall(regex2, flagReceiver)[0]))
            x3=float((re.findall(regex3, flagReceiver)[0]))
            x4=float((re.findall(regex4, flagReceiver)[0]))
            x=[0,50,50+x2,50+x2+x3,50+x2+x3+x4,100+x2+x3+x4]
            y=[0,0,x1,x1,0,0]
            self.axes.plot(x,y,c='red')
            del x[0],x[-1]
            del y[0],y[-1]
            for a,b in zip(x,y):
                self.axes.text(a,b,(a,b),ha='center',va='bottom',fontsize=10)
        elif flagReceiver[0]=='0':
            self.axes.plot([0,50],[0,0])
        elif flagReceiver[0]=='?':
            regex1=r'order:([\s\S]*) Center frequency:'
            regex2=r' Center frequency:([\s\S]*) Bandwidth:'
            regex3=r' Bandwidth:([\s\S]*) Pulse duration:'
            regex4=r' Pulse duration:([\s\S]*) The END'
            n=int((re.findall(regex1, flagReceiver)[0]))
            fc=int((re.findall(regex2, flagReceiver)[0]))
            BW=int((re.findall(regex3, flagReceiver)[0]))
            dur=int(1000*float((re.findall(regex4, flagReceiver)[0])))
            Time = np.linspace(0,dur,10*dur)
            V = [ ((1-math.pow((abs(np.cos((np.pi)*t/dur))),n)) \
            * complex(np.cos(fc*t*2*np.pi),np.sin(fc*t*2*np.pi)) \
            * complex(np.cos((-2)*np.pi*(BW/2*t - (BW/2/dur)*t*t)),np.sin((-2)*np.pi*(BW/2*t - (BW/2/dur)*t*t)))).real \
            for t in Time]
            print("ploting...")
            self.axes.plot(Time,V,c='red',lw=0.15)
        elif flagReceiver[0:6]=="Spiral":
            regex1=r'Amplitude:([\s\S]*) Angular velocity:'
            regex2=r' Angular velocity:([\s\S]*) Duration:'
            regex3=r' Duration:([\s\S]*) The END'
            A=float(re.findall(regex1, flagReceiver)[0])
            w=float(re.findall(regex2, flagReceiver)[0])
            dur=int(re.findall(regex3, flagReceiver)[0])
            Time = np.linspace(0,dur,10*dur)
            Gx = [A*w*(np.cos(w*t)-t*w*np.sin(w*t))for t in Time]
            Gy = [A*w*(np.sin(w*t)+t*w*np.cos(w*t))for t in Time]
            print("ploting...")
            self.axes.plot(Time,Gx,
                           Time,Gy)
        else:#此处为function 暂定
            pass
        '''
    def plotother(self):
        F1 = MyFigure(width=5, height=4, dpi=100)
        F1.fig.suptitle("Figuer_4")
        F1.axes1 = F1.fig.add_subplot(221)
        x = np.arange(0, 50)
        y = np.random.rand(50)
        F1.axes1.hist(y, bins=50)
        F1.axes1.plot(x, y)
        F1.axes1.bar(x, y)
        F1.axes1.set_title("hist")
        F1.axes2 = F1.fig.add_subplot(222)

        ## 调用figure下面的add_subplot方法，类似于matplotlib.pyplot下面的subplot方法
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        y = [23, 21, 32, 13, 3, 132, 13, 3, 1]
        F1.axes2.plot(x, y)
        F1.axes2.set_title("line")
        # 散点图
        F1.axes3 = F1.fig.add_subplot(223)
        F1.axes3.scatter(np.random.rand(20), np.random.rand(20))
        F1.axes3.set_title("scatter")
        # 折线图
        F1.axes4 = F1.fig.add_subplot(224)
        x = np.arange(0, 5, 0.1)
        F1.axes4.plot(x, np.sin(x), x, np.cos(x))
        F1.axes4.set_title("sincos")
        self.gridlayout.addWidget(F1, 0, 2)
        '''

class ShowFunction(QDialog,Canvas_Dialog):
    def __init__(self,flag):
        super(ShowFunction,self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Pulse Sequence Design")
        self.setMinimumSize(0,0)
        self.F = MyFigure(width=3, height=2, dpi=100)
        self.flagReceiver=flag
        self.F.plotfunc(self.flagReceiver)
        self.gridlayout = QGridLayout(self.groupBox)  # 继承容器groupBox
        self.gridlayout.addWidget(self.F,0,1)

        #补充：另创建一个实例绘图并显示
        #self.plotother()
            

'''
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = ShowFunction()
    main.show()
    sys.exit(app.exec_())
'''