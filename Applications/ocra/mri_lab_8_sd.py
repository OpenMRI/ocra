# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'tableWidget_1.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

import sys
import re

import numpy as np
import matplotlib.pyplot as plt

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from Function_Canvas import ShowFunction
from MyFunctions import myFunctions
from Square_Character import Ui_square_Dialog
from Pulse_Character import Ui_pulse_Dialog
from Spiral_Character import Ui_spiral_Dialog



class MRI_SD_Widget(QDialog):

    def __init__(self,parent=None):
        super(MRI_SD_Widget,self).__init__()
    
        self.setObjectName("Dialog")
        #self.resize(900,600)
        QtCore.QMetaObject.connectSlotsByName(self)

        _translate = QtCore.QCoreApplication.translate
        self.tableWidget_set()
        #create buttons
        self.AddColumnBtn=QPushButton("Add column",self)
        self.AddColumnBtn.setToolTip("Add a Column to Pulse")
        self.AddColumnBtn.move(1230,173)
        self.AddColumnBtn.resize(180,40)
        self.AddColumnBtn.clicked.connect(self.AddColumnBtnClicked)
        self.ResetBtn=QPushButton("Reset",self)
        self.ResetBtn.setToolTip("Reset the selected Pulse Sequence")
        self.ResetBtn.move(1230,323)
        self.ResetBtn.resize(180,40)
        self.ResetBtn.clicked.connect(self.ResetBtnClicked)
        self.SaveBtn=QPushButton("Save",self)
        self.SaveBtn.setToolTip("Save pulse sequence")
        self.SaveBtn.move(1230,473)
        self.SaveBtn.resize(180,40)
        self.SaveBtn.clicked.connect(self.SaveBtnClicked)
        self.CreateBtn=QPushButton("Create",self)
        self.CreateBtn.setToolTip("Create pulse sequence backyard")
        self.CreateBtn.move(1230,623)
        self.CreateBtn.resize(180,40)
        self.CreateBtn.clicked.connect(self.CreateBtnClicked)
        #menu
        self.createGradMenu()
        self.createPulseMenu()
        self.createLoopMenu()
        '''
        self.createAmplMenu()
        self.createAttenMenu()
        self.createGateMenu()
        self.createPhModMenu()
        '''


    def tableWidget_set(self):
        
        #open file
        fileObject=open('Pulse_Design/data.txt','r')
        #design size
        self.CountColumn=int(fileObject.readline())
        self.CountRow=int(fileObject.readline())
        self.rangeMax=int(fileObject.readline()) #最大列数
        self.ColumnWidth=150 #添加时默认列宽
        self.RowWidth=120 #打开时默认行宽
        self.tableWidget = QtWidgets.QTableWidget(self)
        self.tableWidget.setGeometry(QtCore.QRect(50,100,1130,723))
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(self.CountColumn)
        self.tableWidget.setRowCount(self.CountRow)
        self.tableWidget.setShowGrid(False)
        self.RowSelected=int()
        self.ColumnSelected=int()
        self.tableWidget.setShowGrid(False)
        self.tableWidget.setStyleSheet("QTableView{ selection-background-color: rgb(180,250,195)}")

        self.headerVertical=["Time Delay /us",
                             "Pulse Sequence",
                        "Gradient X",
                        "Gradient Y",
                        "Gradient Z",
                        "Loop structure"]
        self.tableWidget.setVerticalHeaderLabels(self.headerVertical)
        self.tableWidget.verticalHeader().setFixedWidth(140)
        
        self.tableWidget.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        self.tableWidget.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        
        self.zero=QPixmap('Pulse_Design/zero.png')
        self.zeroSize=QSize(self.ColumnWidth,self.RowWidth)
        self.zeroScaled=self.zero.scaled(self.zeroSize)
        self.zeroIcon=QIcon(self.zero)
        self.high=QPixmap('Pulse_Design/high.png')
        self.highSize=QSize(self.ColumnWidth,self.RowWidth)
        self.highScaled=self.high.scaled(self.highSize)
        self.highIcon=QIcon(self.highScaled)
        self.low=QPixmap('Pulse_Design/low.png')
        self.lowSize=QSize(self.ColumnWidth,self.RowWidth)
        self.lowScaled=self.low.scaled(self.lowSize)
        self.lowIcon=QIcon(self.lowScaled)
        self.func=QPixmap('Pulse_Design/func.png')
        self.funcSize=QSize(self.ColumnWidth,self.RowWidth)
        self.funcScaled=self.func.scaled(self.funcSize)
        self.funcIcon=QIcon(self.funcScaled)
        self.pulse90=QPixmap('Pulse_Design/pulse90.png')
        self.pulse90Size=QSize(self.ColumnWidth,self.RowWidth)
        self.pulse90Scaled=self.pulse90.scaled(self.pulse90Size)
        self.pulse90Icon=QIcon(self.pulse90Scaled)
        self.pulse180=QPixmap('Pulse_Design/pulse180.png')
        self.pulse180Size=QSize(self.ColumnWidth,self.RowWidth)
        self.pulse180Scaled=self.pulse180.scaled(self.pulse180Size)
        self.pulse180Icon=QIcon(self.pulse180Scaled)
        self.loopStart=QPixmap('Pulse_Design/loopStart.png')
        self.loopStartSize=QSize(self.ColumnWidth,self.RowWidth)
        self.loopStartScaled=self.loopStart.scaled(self.loopStartSize)
        self.loopStartIcon=QIcon(self.loopStartScaled)
        self.loopEnd=QPixmap('Pulse_Design/loopEnd.png')
        self.loopEndSize=QSize(self.ColumnWidth,self.RowWidth)
        self.loopEndScaled=self.loopEnd.scaled(self.loopEndSize)
        self.loopEndIcon=QIcon(self.loopEndScaled)
        
        '''
        self.highX=QPixmap('high+X.png')
        self.highXSize=QSize(self.ColumnWidth,self.RowWidth)
        self.highXScaled=self.highX.scaled(self.highXSize)
        self.highXIcon=QIcon(self.highXScaled)
        self.highY=QPixmap('high+Y.png')
        self.highYSize=QSize(self.ColumnWidth,self.RowWidth)
        self.highYScaled=self.highY.scaled(self.highYSize)
        self.highYIcon=QIcon(self.highYScaled)
        self.highXminus=QPixmap('high-X.png')
        self.highXminusSize=QSize(self.ColumnWidth,self.RowWidth)
        self.highXminusScaled=self.highXminus.scaled(self.highXminusSize)
        self.highXminusIcon=QIcon(self.highXminusScaled)
        self.highYminus=QPixmap('high-Y.png')
        self.highYminusSize=QSize(self.ColumnWidth,self.RowWidth)
        self.highYminusScaled=self.highYminus.scaled(self.highYminusSize)
        self.highYminusIcon=QIcon(self.highYminusScaled)
        '''

        #创建labels数组
        #与labels对应的flags标识
        #0 means low
        #1 means high
        #string means function
        self.labels=[[QLabel() for i in range(self.rangeMax)]for k in range(self.CountRow)]
        self.flags=[[str() for i in range(self.rangeMax)]for k in range(self.CountRow)]
        self.loopStartPos=-1
        self.loopEndPos=-1
        self.LoopTime = 1
        for i in range(0,self.CountColumn):
            self.tableWidget.setColumnWidth(i,int(fileObject.readline()))
            self.tableWidget.setItem(0,i,QTableWidgetItem(fileObject.readline().rstrip('\n')))
            self.tableWidget.item(0,i).setTextAlignment(QtCore.Qt.AlignCenter)
            for k in range(1,self.CountRow):
                self.flags[k][i]=fileObject.readline().rstrip('\n')
            if self.flags[5][i][0:9]=="loopStart":
                self.loopStartPos=i
            elif self.flags[5][i]=="loopEnd":
                self.loopEndPos=i
        
        fileObject.close()
        
        self.tableWidget.setRowHeight(0,70)
        for i in range(1,self.CountRow):
            self.tableWidget.setRowHeight(i,self.RowWidth)
        
        for i in range(self.CountColumn):
            for k in range(1,self.CountRow):
                self.labels[k][i].setMinimumSize(3,3)
                self.labels[k][i].setScaledContents(True)
                self.tableWidget.setItem(k,i,QTableWidgetItem(" "))
                if self.flags[k][i][0]=='0':
                    self.labels[k][i].setPixmap(self.zeroScaled)
                elif self.flags[k][i][0]=='+':
                    self.labels[k][i].setPixmap(self.highScaled)
                elif self.flags[k][i][0]=='-':
                    self.labels[k][i].setPixmap(self.lowScaled)
                elif self.flags[k][i][0]=='?' or self.flags[k][i][0:6]=="Spiral":
                    self.labels[k][i].setPixmap(self.funcScaled)
                elif self.flags[k][i]=="pulse90":
                    self.labels[k][i].setPixmap(self.pulse90Scaled)
                    self.tableWidget.setItem(k,i,QTableWidgetItem("90°"))
                    self.tableWidget.item(k,i).setTextAlignment(QtCore.Qt.AlignCenter)
                elif self.flags[k][i]=="pulse180X+":
                    self.labels[k][i].setPixmap(self.pulse180Scaled)
                    self.tableWidget.setItem(k,i,QTableWidgetItem("180°X+"))
                    self.tableWidget.item(k,i).setTextAlignment(QtCore.Qt.AlignCenter)
                elif self.flags[k][i]=="pulse180X-":
                    self.labels[k][i].setPixmap(self.pulse180Scaled)
                    self.tableWidget.setItem(k,i,QTableWidgetItem("180°X-"))
                    self.tableWidget.item(k,i).setTextAlignment(QtCore.Qt.AlignCenter)
                elif self.flags[k][i]=="pulse180Y+":
                    self.labels[k][i].setPixmap(self.pulse180Scaled)
                    self.tableWidget.setItem(k,i,QTableWidgetItem("180°Y+"))
                    self.tableWidget.item(k,i).setTextAlignment(QtCore.Qt.AlignCenter)
                elif self.flags[k][i]=="pulse180Y-":
                    self.labels[k][i].setPixmap(self.pulse180Scaled)
                    self.tableWidget.setItem(k,i,QTableWidgetItem("180°Y-"))
                    self.tableWidget.item(k,i).setTextAlignment(QtCore.Qt.AlignCenter)
                elif self.flags[k][i][0:9]=="loopStart":
                    self.labels[k][i].setPixmap(self.loopStartScaled)
                    self.tableWidget.setItem(k,i,QTableWidgetItem(self.flags[k][i][9:]))
                    self.LoopTime=self.flags[k][i][9:]
                    self.tableWidget.item(k,i).setTextAlignment(QtCore.Qt.AlignCenter)
                elif self.flags[k][i]=="loopEnd":
                    self.labels[k][i].setPixmap(self.loopEndScaled)
                    self.tableWidget.item(k,i).setTextAlignment(QtCore.Qt.AlignCenter)
                else:
                    self.labels[k][i].setPixmap(self.funcScaled)
                    
        for i in range(self.CountColumn):
            for k in range(1,self.CountRow):
                self.tableWidget.setCellWidget(k,i,self.labels[k][i])

        self.tableWidget.setMouseTracking(True)
        
        self.MouseCount=0
        
        self.tableWidget.clicked.connect(self.showContextMenu)

    #menu
    def createGradMenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.GradMenu=QMenu(self)
        self.GradactionHigh=self.GradMenu.addAction(self.highIcon,u'|    High')
        self.GradactionZero=self.GradMenu.addAction(self.zeroIcon,u'|    Zero')
        self.GradactionLow=self.GradMenu.addAction(self.lowIcon,u'|     Low')
        self.GradactionSpiral=self.GradMenu.addAction(self.funcIcon,u'|    Spiral')
        self.GradactionShow=self.GradMenu.addAction(QIcon(""),u'|   Show')
        self.GradactionHigh.triggered.connect(self.GradactionHighHandler)
        self.GradactionZero.triggered.connect(self.GradactionZeroHandler)
        self.GradactionLow.triggered.connect(self.GradactionLowHandler)
        self.GradactionSpiral.triggered.connect(self.GradactionSpiralHandler)
        self.GradactionShow.triggered.connect(self.GradactionShowHandler)
    def createPulseMenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.PulseMenu=QMenu(self)
        self.Pulseaction90=self.PulseMenu.addAction(self.pulse90Icon,u'| 90 Pulse')
        self.Pulseaction180X=self.PulseMenu.addAction(self.pulse180Icon,u'|180X+ Pulse')
        self.Pulseaction180Xminus=self.PulseMenu.addAction(self.pulse180Icon,u'|180X- Pulse')
        self.Pulseaction180Y=self.PulseMenu.addAction(self.pulse180Icon,u'|180Y+ Pulse')
        self.Pulseaction180Yminus=self.PulseMenu.addAction(self.pulse180Icon,u'|180Y- Pulse')
        self.PulseactionDesign=self.PulseMenu.addAction(u'|Design Pulse')
        self.PulseactionZero=self.PulseMenu.addAction(self.zeroIcon,u'|     zero')
        self.PulseactionShow=self.PulseMenu.addAction(u'|      show')
        self.Pulseaction90.triggered.connect(self.Pulseaction90Handler)
        self.Pulseaction180X.triggered.connect(self.Pulseaction180XHandler)
        self.Pulseaction180Xminus.triggered.connect(self.Pulseaction180XminusHandler)
        self.Pulseaction180Y.triggered.connect(self.Pulseaction180YHandler)
        self.Pulseaction180Yminus.triggered.connect(self.Pulseaction180YminusHandler)
        self.PulseactionDesign.triggered.connect(self.PulseactionDesignHandler)
        self.PulseactionZero.triggered.connect(self.PulseactionZeroHandler)
        self.PulseactionShow.triggered.connect(self.PulseactionShowHandler)
    def createLoopMenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.LoopMenu=QMenu(self)
        self.LoopactionStart=self.LoopMenu.addAction(self.loopStartIcon,u'| set Start')
        self.LoopactionEnd=self.LoopMenu.addAction(self.loopEndIcon,u'|   set End')
        self.LoopactionDelete=self.LoopMenu.addAction(self.zeroIcon,u'|  delete')
        self.LoopactionStart.triggered.connect(self.LoopactionStartHandler)
        self.LoopactionEnd.triggered.connect(self.LoopactionEndHandler)
        self.LoopactionDelete.triggered.connect(self.LoopactionDeleteHandler)
        
    '''
    def createAmplMenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.AmplMenu = QMenu(self)
        self.AmplactionFunc = self.AmplMenu.addAction(self.funcIcon,u'| Function')
        self.AmplactionZero = self.AmplMenu.addAction(self.zeroIcon,u'|    Zero')
        self.AmplactionFunc.triggered.connect(self.AmplactionFuncHandler)
        self.AmplactionZero.triggered.connect(self.AmplactionZeroHandler)
  
    def createPhModMenu(self):  #Phase Cycle use the same thing
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.PhModMenu = QMenu(self)
        self.PhModactionEdit = self.PhModMenu.addAction(u'|  Edit..')
        self.PhModactionHighX = self.PhModMenu.addAction(u'|      +X')
        self.PhModactionHighY = self.PhModMenu.addAction(u'|      +Y')
        self.PhModactionHighXminus = self.PhModMenu.addAction(u'|      -X')
        self.PhModactionHighYminus = self.PhModMenu.addAction(u'|      -Y')
        self.PhModactionZero = self.PhModMenu.addAction(self.zeroIcon,u'|    Zero')
        self.PhModactionHighX.triggered.connect(self.PhModactionHighXHandler)
        self.PhModactionHighY.triggered.connect(self.PhModactionHighYHandler)
        self.PhModactionHighXminus.triggered.connect(self.PhModactionHighXminusHandler)
        self.PhModactionHighYminus.triggered.connect(self.PhModactionHighYminusHandler)
        self.PhModactionZero.triggered.connect(self.PhModadtionZeroHandler)
    
    def createAttenMenu(self):  #Phase Cycle use the same thing
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.AttenMenu = QMenu(self)
        self.AttenactionEdit = self.AttenMenu.addAction(u'|  Edit..')
        self.AttenactionZero = self.AttenMenu.addAction(self.zeroIcon,u'|    Zero')
     
    def createGateMenu(self): 
        self.setContextMenuPolicy(Qt.CustomContextMenu)  
        self.GateMenu = QMenu(self)
        self.GateactionZero = self.GateMenu.addAction(self.zeroIcon,u'|    Zero')
        self.GateactionHigh = self.GateMenu.addAction(self.highIcon,u'|    High')
        self.GateactionFunc = self.GateMenu.addAction(self.funcIcon,u'|Function')
        self.GateactionZero.triggered.connect(self.GateactionZeroHandler)
        self.GateactionHigh.triggered.connect(self.GateactionHighHandler)
        self.GateactionFunc.triggered.connect(self.GateactionFuncHandler)
    '''
    #menu functions
    def showContextMenu(self, pos):
        self.MouseCount+=1
        if ((self.MouseCount)%2):
            self.RowSelected=self.tableWidget.currentRow()
            self.ColumnSelected=self.tableWidget.currentColumn()
            if self.RowSelected==2 or self.RowSelected==3 or self.RowSelected==4:
                self.GradMenu.exec_(QCursor.pos())
            elif self.RowSelected==1:
                self.PulseMenu.exec_(QCursor.pos())
            elif self.RowSelected==5:
                self.LoopMenu.exec_(QCursor.pos())
                
    def GradactionHighHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        Square=Ui_square_Dialog(self.tableWidget.item(0,y).text())
        if self.flags[x][y][0]=="+":
            regex1=r'Amplitude:([\s\S]*) Increase duration:'
            regex2=r' Increase duration:([\s\S]*) Holding duration:'
            regex3=r' Holding duration:([\s\S]*) Decrease duration:'
            regex4=r' Decrease duration:([\s\S]*) The END'
            Square.AmplEdit.setText(re.findall(regex1, self.flags[x][y])[0])
            Square.IncreaseEdit.setText(re.findall(regex2, self.flags[x][y])[0])
            Square.HoldingEdit.setText(re.findall(regex3, self.flags[x][y])[0])
            Square.DecreaseEdit.setText(re.findall(regex4, self.flags[x][y])[0])
        if Square.exec_()==QDialog.Accepted:
            self.flags[x][y]="+"+Square.string
            self.labels[x][y].setPixmap(self.highScaled)
            self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def GradactionZeroHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.zeroScaled)
        self.flags[x][y]="0"
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def GradactionLowHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        Square=Ui_square_Dialog(self.tableWidget.item(0,y).text())
        if self.flags[x][y][0]=="-":
            regex1=r'Amplitude:([\s\S]*) Increase duration:'
            regex2=r' Increase duration:([\s\S]*) Holding duration:'
            regex3=r' Holding duration:([\s\S]*) Decrease duration:'
            regex4=r' Decrease duration:([\s\S]*) The END'
            Square.AmplEdit.setText(re.findall(regex1, self.flags[x][y])[0])
            Square.IncreaseEdit.setText(re.findall(regex2, self.flags[x][y])[0])
            Square.HoldingEdit.setText(re.findall(regex3, self.flags[x][y])[0])
            Square.DecreaseEdit.setText(re.findall(regex4, self.flags[x][y])[0])
        if Square.exec_()==QDialog.Accepted:
            self.flags[x][y]="-"+Square.string
            self.labels[x][y].setPixmap(self.lowScaled)
            self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def GradactionSpiralHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        if x!=2 and x!=3:
            reply=QMessageBox.information(self,"inform","Spiral Trajectory can only be used on x and y axis!")
        else:
            Spiral=Ui_spiral_Dialog()
            if self.flags[x][y][0:6]=="Spiral":
                regex1=r'Amplitude:([\s\S]*) Angular velocity:'
                regex2=r' Angular velocity:([\s\S]*) Duration:'
                regex3=r' Duration:([\s\S]*) The END'
                Spiral.AmplEdit.setText(re.findall(regex1, self.flags[x][y])[0])
                Spiral.omegaEdit.setText(re.findall(regex2, self.flags[x][y])[0])
                Spiral.durationEdit.setText(re.findall(regex3, self.flags[x][y])[0])
            if Spiral.exec_()==QDialog.Accepted:
                self.flags[2][y]=Spiral.string
                self.labels[2][y].setPixmap(self.funcScaled)
                self.tableWidget.setCellWidget(2,y,self.labels[2][y])
                self.flags[3][y]=Spiral.string
                self.labels[3][y].setPixmap(self.funcScaled)
                self.tableWidget.setCellWidget(3,y,self.labels[3][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def GradactionShowHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        ShowSquare=ShowFunction(self.flags[x][y])
        ShowSquare.exec_()
        #脉冲右键菜单
    def Pulseaction90Handler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.pulse90Scaled)
        self.flags[x][y]="pulse90"
        self.tableWidget.setItem(x,y,QTableWidgetItem("90°"))
        self.tableWidget.item(x,y).setTextAlignment(QtCore.Qt.AlignCenter)
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def Pulseaction180XHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.pulse180Scaled)
        self.flags[x][y]="pulse180X+"
        self.tableWidget.setItem(x,y,QTableWidgetItem("180°X+"))
        self.tableWidget.item(x,y).setTextAlignment(QtCore.Qt.AlignCenter)
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def Pulseaction180YHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.pulse180Scaled)
        self.flags[x][y]="pulse180X-"
        self.tableWidget.setItem(x,y,QTableWidgetItem("180°X-"))
        self.tableWidget.item(x,y).setTextAlignment(QtCore.Qt.AlignCenter)
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def Pulseaction180XminusHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.pulse180Scaled)
        self.flags[x][y]="pulse180Y+"
        self.tableWidget.setItem(x,y,QTableWidgetItem("180°Y+"))
        self.tableWidget.item(x,y).setTextAlignment(QtCore.Qt.AlignCenter)
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def Pulseaction180YminusHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.pulse180Scaled)
        self.flags[x][y]="pulse180Y-"
        self.tableWidget.setItem(x,y,QTableWidgetItem("180°Y-"))
        self.tableWidget.item(x,y).setTextAlignment(QtCore.Qt.AlignCenter)
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def PulseactionDesignHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        Pulse=Ui_pulse_Dialog()
        print(self.flags[x][y])
        regex1=r'order:([\s\S]*) Center frequency:'
        regex2=r' Center frequency:([\s\S]*) Bandwidth:'
        regex3=r' Bandwidth:([\s\S]*) Pulse duration:'
        regex4=r' Pulse duration:([\s\S]*) The END'
        if len(re.findall(regex1, self.flags[x][y])) !=0:
            Pulse.orderEdit.setText(re.findall(regex1, self.flags[x][y])[0])
            Pulse.centerFreqEdit.setText(re.findall(regex2, self.flags[x][y])[0])
            Pulse.BWEdit.setText(re.findall(regex3, self.flags[x][y])[0])
            Pulse.durationEdit.setText(re.findall(regex4, self.flags[x][y])[0])
        if Pulse.exec_()==QDialog.Accepted:
            self.flags[x][y]="?"+Pulse.string
            self.labels[x][y].setPixmap(self.funcScaled)
            self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        print(self.flags[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def PulseactionZeroHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.zeroScaled)
        self.flags[x][y]="0"
        self.tableWidget.setItem(x,y,QTableWidgetItem(" "))
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def PulseactionShowHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        ShowPulse=ShowFunction(self.flags[x][y])
        ShowPulse.exec_()
    def LoopactionStartHandler(self):
        self.MouseCount+=1
        if self.loopStartPos!=-1:
            reply=QMessageBox.information(self,"Warning","there can only be one loop!")
        else:
            x=self.RowSelected
            y=self.ColumnSelected
            self.labels[x][y].setPixmap(self.loopStartScaled)
            value,ok=QInputDialog.getInt(self,"Loop Time", "please enter an integer:", 1, 1, 10000, 1)
            self.flags[x][y]="loopStart"+str(value)
            self.LoopTime=value
            self.tableWidget.setItem(x,y,QTableWidgetItem(str(value)))
            self.tableWidget.item(x,y).setTextAlignment(QtCore.Qt.AlignCenter)
            self.tableWidget.setCellWidget(x,y,self.labels[x][y])
            self.loopStartPos=y
    def LoopactionEndHandler(self):
        self.MouseCount+=1
        if self.loopEndPos!=-1:
            reply=QMessageBox.information(self,"Warning","there can only be one loop!")
        else:
            x=self.RowSelected
            y=self.ColumnSelected
            if y<=self.loopStartPos:
                reply=QMessageBox.information(self,"Warning","Please design the loop in correct way!")
            else:
                self.loopEndPos=y
                self.labels[x][y].setPixmap(self.loopEndScaled)
                self.flags[x][y]="loopEnd"
                self.tableWidget.setItem(x,y,QTableWidgetItem(" "))
                self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    def LoopactionDeleteHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        if y==self.loopEndPos:
            self.loopEndPos=-1
        elif y==self.loopStartPos:
            self.loopStartPos=-1
        self.labels[x][y].setPixmap(self.zeroScaled)
        self.flags[x][y]="0"
        self.tableWidget.setItem(x,y,QTableWidgetItem(" "))
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
    '''
    def AmplactionFuncHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.funcScaled)
        while True:
            value, ok=QInputDialog.getText(self,"Function input",
                                           "Please call the Function name:\n(e.g.: mySin)\n",
                                           QLineEdit.Normal,self.flags[x][y])
            if value!="" and value!="0":
                break
            reply=QMessageBox.information(self,"Warning","The function cannot be BLANK or ZERO!")
        self.flags[x][y]=value
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def AmplactionZeroHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.zeroScaled)
        self.flags[x][y]="0"
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        
    def PhModactionHighXHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.highXScaled)
        self.flags[x][y]="+X"
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def PhModactionHighYHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.highYScaled)
        self.flags[x][y]="+Y"
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def PhModactionHighXminusHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.highXminusScaled)
        self.flags[x][y]="-X"
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def PhModactionHighYminusHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.highYminusScaled)
        self.flags[x][y]="-Y"
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def PhModadtionZeroHandler(self):
        self.AmplactionZeroHandler()
    
    
    def GateactionZeroHandler(self):
        self.AmplactionZeroHandler()
    def GateactionHighHandler(self):
        self.MouseCount+=1
        x=self.RowSelected
        y=self.ColumnSelected
        self.labels[x][y].setPixmap(self.highScaled)
        self.flags[x][y]="1"
        self.tableWidget.setCellWidget(x,y,self.labels[x][y])
        if y==self.CountColumn-1:
            self.AddColumnBtnClicked()
    def GateactionFuncHandler(self):
        self.AmplactionFuncHandler()
    '''
        
    def AddColumnBtnClicked(self):
        self.CountColumn+=1
        y=self.CountColumn-1
        self.tableWidget.setColumnCount(self.CountColumn)
        self.tableWidget.setColumnWidth(y,self.ColumnWidth)
        self.tableWidget.setItem(0,y,QTableWidgetItem("5"))
        self.tableWidget.item(0,y).setTextAlignment(QtCore.Qt.AlignCenter)
        for i in range(1,self.CountRow):
            self.labels[i][y].setPixmap(self.zeroScaled)
            self.flags[i][y]="0"
            self.tableWidget.setCellWidget(i,y,self.labels[i][y])
            self.labels[i][y].setScaledContents(True)

    def ResetBtnClicked(self):
        for currentQTableWidgetItem in self.tableWidget.selectedItems():
            x=currentQTableWidgetItem.row()
            y=currentQTableWidgetItem.column()
            if x>0:
                if self.flags[x][y][0:6]=="Spiral":
                    self.labels[2][y].setPixmap(self.zeroScaled)
                    self.flags[2][y]="0"
                    self.tableWidget.setCellWidget(2,y,self.labels[2][y])
                    self.tableWidget.setItem(2,y,QTableWidgetItem(" "))
                    self.labels[3][y].setPixmap(self.zeroScaled)
                    self.flags[3][y]="0"
                    self.tableWidget.setCellWidget(3,y,self.labels[3][y])
                    self.tableWidget.setItem(3,y,QTableWidgetItem(" "))
                self.labels[x][y].setPixmap(self.zeroScaled)
                self.flags[x][y]="0"
                self.tableWidget.setCellWidget(x,y,self.labels[x][y])
                self.tableWidget.setItem(x,y,QTableWidgetItem(" "))
    def SaveBtnClicked(self):
        fileObject=open('Pulse_Design/data.txt','w')
        fileObject.write(str(self.CountColumn))
        fileObject.write('\n')
        fileObject.write(str(self.CountRow))
        fileObject.write('\n')
        fileObject.write(str(self.rangeMax))
        fileObject.write('\n')
        for i in range(self.CountColumn):
            fileObject.write(str(self.tableWidget.columnWidth(i)))
            fileObject.write('\n')
            fileObject.write(self.tableWidget.item(0,i).text())
            fileObject.write('\n')
            for k in range(1,self.CountRow):
                fileObject.write(self.flags[k][i])
                fileObject.write('\n')
        fileObject.close()
        
    def CreateBtnClicked(self):
        #create time and xyz program
        fileObject=open('sequence/sig/myPulse.txt','w')
        print("creating TimePulse")
        fileObject.write("J C"+'\n')
        fileObject.write("LOOP_CTR = "+hex(int(self.LoopTime))+'\n')  # no LOOP now
        fileObject.write("CMD1 = 0x0"+'\n')
        fileObject.write("CMD2 = 0x0"+'\n')
        fileObject.write("CMD3 = 0x2"+'\n')
        fileObject.write("CMD4 = 0x0"+'\n')
        fileObject.write("CMD5 = TX_GATE | TX_PULSE | RX_PULSE"+'\n')
        fileObject.write("CMD6 = TX_GATE | TX_PULSE"+'\n')
        fileObject.write("CMD7 = GRAD_PULSE | RX_PULSE"+'\n')
        fileObject.write("CMD8 = GRAD_PULSE"+'\n')
        fileObject.write("CMD9 = TX_GATE | TX_PULSE | RX_PULSE | GRAD_PULSE"+'\n')
        fileObject.write("CMD10 = TX_GATE | TX_PULSE | GRAD_PULSE"+'\n')
        fileObject.write("LD64 2, LOOP_CTR"+'\n')
        fileObject.write("LD64 3, CMD3"+'\n')
        fileObject.write("LD64 4, CMD4"+'\n')
        fileObject.write("LD64 5, CMD5"+'\n')
        fileObject.write("LD64 6, CMD6"+'\n')
        fileObject.write("LD64 7, CMD7"+'\n')
        fileObject.write("LD64 8, CMD8"+'\n')
        fileObject.write("LD64 9, CMD9"+'\n')
        fileObject.write("LD64 10, CMD10"+'\n')
        #遍历
        timing=0
        for i in range(self.CountColumn):
            timing+=int(self.tableWidget.item(0,i).text())

        pulsRecord=[0 for i in range(timing)]
        gradRecord=[0 for i in range(timing)]
        loopRecord=[0 for i in range(timing)]
        LoopCondition=0
        timing=0
        record90=0
        recordEcho=[]
        NowLine=23
        LoopStartLine=0
        recordStay=1 
        recordCondition=0
        recordCal=0
        pulsing=0
        for i in range(self.CountColumn):
            if self.tableWidget.item(1,i).text()=="90°":
                for k in range(timing,timing+120):
                    pulsRecord[k]=1
                record90=timing
            elif self.tableWidget.item(1,i).text()=="180°X+":
                for k in range(timing,timing+180):
                    pulsRecord[k]=2
                recordEcho.append(timing*2-record90)
            elif self.tableWidget.item(1,i).text()=="180°X-":
                for k in range(timing,timing+180):
                    pulsRecord[k]=3
                recordEcho.append(timing*2-record90)
            elif self.tableWidget.item(1,i).text()=="180°Y+":
                for k in range(timing,timing+180):
                    pulsRecord[k]=4
                recordEcho.append(timing*2-record90)
            elif self.tableWidget.item(1,i).text()=="180°Y-":
                for k in range(timing,timing+180):
                    pulsRecord[k]=5
                recordEcho.append(timing*2-record90)
            if self.flags[2][i]!="0" or self.flags[3][i]!="0" or self.flags[4][i]!="0":
                for k in range(timing,timing+int(self.tableWidget.item(0,i).text())):
                    gradRecord[k]=1
            if self.flags[5][i][0:9]=="loopStart":
                for k in range(timing,timing+int(self.tableWidget.item(0,i).text())):
                    loopRecord[k]=1
            elif self.flags[5][i]=="loopEnd":
                for k in range(timing,timing+int(self.tableWidget.item(0,i).text())):
                    loopRecord[k]=-1
            timing+=int(self.tableWidget.item(0,i).text())
        for i in range(1,timing):
            if loopRecord[i]==1:
                LoopCondition=1
            elif loopRecord[i]==-1:
                LoopCondition=-1
            if pulsRecord[i]==1 or pulsRecord[i]==2 or pulsRecord[i]==3 or pulsRecord[i]==4 or pulsRecord[i]==5:
                if gradRecord[i]==1:
                    if i>=(recordEcho[0]-100):
                        if loopRecord[i]==0:
                            recordCal=111
                        else:
                            recordCal=1111
                    else:
                        if loopRecord[i]==0:
                            recordCal=110
                        else:
                            recordCal=1110
                else:
                    if i>=(recordEcho[0]-100):
                        if loopRecord[i]==0:
                            recordCal=101
                        else:
                            recordCal=1101
                    else:
                        if loopRecord[i]==0:
                            recordCal=100
                        else:
                            recordCal=1100
            else:
                if gradRecord[i]==1:
                    if i>=(recordEcho[0]-100):
                        if loopRecord[i]==0:
                            recordCal=11
                        else:
                            recordCal=1011
                    else:
                        if loopRecord[i]==0:
                            recordCal=10
                        else:
                            recordCal=1010
                else:
                    if i>=(recordEcho[0]-100):
                        if loopRecord[i]==0:
                            recordCal=1
                        else:
                            recordCal=1001
                    else:
                        if loopRecord[i]==0:
                            recordCal=0
                        else:
                            recordCal=1000
            if recordCal==recordCondition:
                recordStay+=1
            else:
                if loopRecord[i-1]==1 and LoopCondition==1:
                    print("loop start")
                    LoopStartLine=NowLine
                    LoopCondition=0
                if recordCondition%1000>99 and pulsing==0:
                    if pulsRecord[i-1]==1:
                        fileObject.write("TXOFFSET 0"+'\n')
                        NowLine+=1
                    elif pulsRecord[i-1]==2:
                        fileObject.write("TXOFFSET 1000"+'\n')
                        NowLine+=1
                    elif pulsRecord[i-1]==3:
                        fileObject.write("TXOFFSET 1000"+'\n')
                        NowLine+=1
                    elif pulsRecord[i-1]==4:
                        fileObject.write("TXOFFSET 2000"+'\n')
                        NowLine+=1
                    elif pulsRecord[i-1]==5:
                        fileObject.write("TXOFFSET 3000"+'\n')
                        NowLine+=1
                    pulsing=1
                else:
                    pulsing=0
                if recordCondition%1000==0:
                    fileObject.write("PR 3, "+str(recordStay)+'\n')
                    NowLine+=1
                elif recordCondition%1000==1:
                    fileObject.write("PR 4, "+str(recordStay)+'\n')
                    NowLine+=1
                elif recordCondition%1000==10:
                    fileObject.write("PR 7, "+str(recordStay)+'\n')
                    NowLine+=1
                elif recordCondition%1000==11:
                    fileObject.write("PR 8, "+str(recordStay)+'\n')
                    NowLine+=1
                elif recordCondition%1000==100:
                    fileObject.write("PR 5, "+str(recordStay)+'\n')
                    NowLine+=1
                elif recordCondition%1000==101:
                    fileObject.write("PR 6, "+str(recordStay)+'\n')
                    NowLine+=1
                elif recordCondition%1000==110:
                    fileObject.write("PR 9, "+str(recordStay)+'\n')
                    NowLine+=1
                elif recordCondition%1000==111:
                    fileObject.write("PR 10, "+str(recordStay)+'\n')
                    NowLine+=1
                recordCondition=recordCal
                recordStay=1
                if LoopCondition==-1 and loopRecord[i-1]==-1:
                    print("loop end")
                    fileObject.write("DEC 2"+'\n')
                    fileObject.write("JNZ 2, "+hex(LoopStartLine)+'\n')
                    LoopCondition=0
        fileObject.write("HALT"+'\n')
        fileObject.close()
        
        #X Y Z design的cpp
        fileObject=open("server/PulseProgram.cpp","w")
        fileObject.write("#include <stdio.h>"+'\n')
        fileObject.write("#include <stdlib.h>"+'\n')
        fileObject.write("#include <stdint.h>"+'\n')
        fileObject.write("#include <string.h>"+'\n')
        fileObject.write("#include <unistd.h>"+'\n')
        fileObject.write("#include <fcntl.h>"+'\n')
        fileObject.write("#include <math.h>"+'\n')
        fileObject.write("#include <sys/mman.h>"+'\n')
        fileObject.write("#include <sys/socket.h>"+'\n')
        fileObject.write("#include <netinet/in.h>"+'\n')
        fileObject.write("#include <arpa/inet.h>"+'\n')
        fileObject.write("#define PI 3.14159265"+'\n')
        fileObject.write("typedef struct"+'\n')
        fileObject.write("{"+'\n')
        fileObject.write("  float gradient_x;"+'\n')
        fileObject.write("  float gradient_y;"+'\n')
        fileObject.write("  float gradient_z;"+'\n')
        fileObject.write("} gradient_offset_t;"+'\n')
        fileObject.write(""+'\n')
        fileObject.write(""+'\n')
        fileObject.write("void generate_gradient_waveforms(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, gradient_offset_t offset)"+'\n')
        fileObject.write("{"+'\n')
        fileObject.write("  uint32_t i;"+'\n')
        fileObject.write("  int32_t ival;"+'\n')
        fileObject.write("  float fLSB = 10.0/((1<<15)-1);"+'\n')
        fileObject.write("  "+'\n')
        fileObject.write("  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;"+'\n')
        fileObject.write("  gx[0] = 0x001fffff & (ival | 0x00100000);"+'\n')
        fileObject.write("  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;"+'\n')
        fileObject.write("  gy[0] = 0x001fffff & (ival | 0x00100000);"+'\n')
        fileObject.write("  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;"+'\n')
        fileObject.write("  gz[0] = 0x001fffff & (ival | 0x00100000);"+'\n')
        fileObject.write("  gx[1] = 0x00200002;"+'\n')
        fileObject.write("  gy[1] = 0x00200002;"+'\n')
        fileObject.write("  gz[1] = 0x00200002;"+'\n')
        fileObject.write("  float fRO = offset.gradient_x;"+'\n')
        fileObject.write("  //Design the X gradient"+'\n')
        timing=int(0)
        for i in range(self.CountColumn):
            timing2=timing+int(self.tableWidget.item(0,i).text())
            if self.flags[2][i]=="0":
                fileObject.write("  for(i="+str(timing)+"; i<"+str(timing2)+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')   #fRO还没偶定义**************
                fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
            elif self.flags[2][i][0]=='+':
                regex1=r'Amplitude:([\s\S]*) Increase duration:'
                regex2=r' Increase duration:([\s\S]*) Holding duration:'
                regex3=r' Holding duration:([\s\S]*) Decrease duration:'
                regex4=r' Decrease duration:([\s\S]*) The END'
                x1=float((re.findall(regex1, self.flags[2][i])[0]))
                x2=float((re.findall(regex2, self.flags[2][i])[0]))
                x3=float((re.findall(regex3, self.flags[2][i])[0]))
                x4=float((re.findall(regex4, self.flags[2][i])[0]))
                if x2!=0:
                    fileObject.write("  for(i="+str(timing)+"; i<"+str(timing+int(x2))+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO += "+str(x1/x2)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
                fileObject.write("  for(i="+str(timing+int(x2))+"; i<"+str(timing+int(x2)+int(x3))+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
                if x4!=0:
                    fileObject.write("  for(i="+str(timing+int(x2)+int(x3))+"; i<"+str(timing2)+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO -= "+str(x1/x4)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
            elif self.flags[2][i][0]=='-':
                regex1=r'Amplitude:([\s\S]*) Increase duration:'
                regex2=r' Increase duration:([\s\S]*) Holding duration:'
                regex3=r' Holding duration:([\s\S]*) Decrease duration:'
                regex4=r' Decrease duration:([\s\S]*) The END'
                x1=float((re.findall(regex1, self.flags[2][i])[0]))
                x2=float((re.findall(regex2, self.flags[2][i])[0]))
                x3=float((re.findall(regex3, self.flags[2][i])[0]))
                x4=float((re.findall(regex4, self.flags[2][i])[0]))
                if x2!=0:
                    fileObject.write("  for(i="+str(timing)+"; i<"+str(timing+int(x2))+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO -= "+str(x1/x2)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
                fileObject.write("  for(i="+str(timing+int(x2))+"; i<"+str(timing+int(x2)+int(x3))+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
                if x4!=0:
                    fileObject.write("  for(i="+str(timing+int(x2)+int(x3))+"; i<"+str(timing2)+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO += "+str(x1/x4)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
            else:
                pass
            timing=timing2
        fileObject.write("  for(i="+str(timing)+"; i<200000; i++)"+'\n')
        fileObject.write("  {"+'\n')
        fileObject.write("    ival=(int32_t)floor(offset.gradient_x/fLSB)*16;"+'\n')
        fileObject.write("    gx[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
        fileObject.write("  }"+'\n')
        fileObject.write("\n\n  //Design the Y gradient"+'\n')
        timing=0
        for i in range(self.CountColumn):
            timing2=timing+int(self.tableWidget.item(0,i).text())
            if self.flags[3][i]=="0":
                fileObject.write("  for(i="+str(timing)+"; i<"+str(timing2)+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')   #fRO还没偶定义**************
                fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
            elif self.flags[3][i][0]=='+':
                regex1=r'Amplitude:([\s\S]*) Increase duration:'
                regex2=r' Increase duration:([\s\S]*) Holding duration:'
                regex3=r' Holding duration:([\s\S]*) Decrease duration:'
                regex4=r' Decrease duration:([\s\S]*) The END'
                x1=float((re.findall(regex1, self.flags[3][i])[0]))
                x2=float((re.findall(regex2, self.flags[3][i])[0]))
                x3=float((re.findall(regex3, self.flags[3][i])[0]))
                x4=float((re.findall(regex4, self.flags[3][i])[0]))
                if x2!=0:
                    fileObject.write("  for(i="+str(timing)+"; i<"+str(timing+int(x2))+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO += "+str(x1/x2)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
                fileObject.write("  for(i="+str(timing+int(x2))+"; i<"+str(timing+int(x2)+int(x3))+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
                if x4!=0:
                    fileObject.write("  for(i="+str(timing+int(x2)+int(x3))+"; i<"+str(timing2)+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO -= "+str(x1/x4)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
            elif self.flags[3][i][0]=='-':
                regex1=r'Amplitude:([\s\S]*) Increase duration:'
                regex2=r' Increase duration:([\s\S]*) Holding duration:'
                regex3=r' Holding duration:([\s\S]*) Decrease duration:'
                regex4=r' Decrease duration:([\s\S]*) The END'
                x1=float((re.findall(regex1, self.flags[3][i])[0]))
                x2=float((re.findall(regex2, self.flags[3][i])[0]))
                x3=float((re.findall(regex3, self.flags[3][i])[0]))
                x4=float((re.findall(regex4, self.flags[3][i])[0]))
                if x2!=0:
                    fileObject.write("  for(i="+str(timing)+"; i<"+str(timing+int(x2))+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO -= "+str(x1/x2)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
                fileObject.write("  for(i="+str(timing+int(x2))+"; i<"+str(timing+int(x2)+int(x3))+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
                if x4!=0:
                    fileObject.write("  for(i="+str(timing+int(x2)+int(x3))+"; i<"+str(timing2)+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO += "+str(x1/x4)+";"+'\n')
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
            else:
                pass
            timing=timing2
        fileObject.write("  for(i="+str(timing)+"; i<200000; i++)"+'\n')
        fileObject.write("  {"+'\n')
        fileObject.write("    ival=(int32_t)floor(offset.gradient_y/fLSB)*16;"+'\n')
        fileObject.write("    gy[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
        fileObject.write("  }"+'\n')
        fileObject.write("\n\n  //Design the Z gradient"+'\n')
        timing=int(0)
        for i in range(self.CountColumn):
            timing2=timing+int(self.tableWidget.item(0,i).text())
            if self.flags[4][i]=="0":
                fileObject.write("  for(i="+str(timing)+"; i<"+str(timing2)+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
            elif self.flags[4][i][0]=='+':
                regex1=r'Amplitude:([\s\S]*) Increase duration:'
                regex2=r' Increase duration:([\s\S]*) Holding duration:'
                regex3=r' Holding duration:([\s\S]*) Decrease duration:'
                regex4=r' Decrease duration:([\s\S]*) The END'
                x1=float((re.findall(regex1, self.flags[4][i])[0]))
                x2=float((re.findall(regex2, self.flags[4][i])[0]))
                x3=float((re.findall(regex3, self.flags[4][i])[0]))
                x4=float((re.findall(regex4, self.flags[4][i])[0]))
                if x2!=0:
                    fileObject.write("  for(i="+str(timing)+"; i<"+str(timing+int(x2))+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO += "+str(x1/x2)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
                fileObject.write("  for(i="+str(timing+int(x2))+"; i<"+str(timing+int(x2)+int(x3))+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
                if x4!=0:
                    fileObject.write("  for(i="+str(timing+int(x2)+int(x3))+"; i<"+str(timing2)+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO -= "+str(x1/x4)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
            elif self.flags[4][i][0]=='-':
                regex1=r'Amplitude:([\s\S]*) Increase duration:'
                regex2=r' Increase duration:([\s\S]*) Holding duration:'
                regex3=r' Holding duration:([\s\S]*) Decrease duration:'
                regex4=r' Decrease duration:([\s\S]*) The END'
                x1=float((re.findall(regex1, self.flags[4][i])[0]))
                x2=float((re.findall(regex2, self.flags[4][i])[0]))
                x3=float((re.findall(regex3, self.flags[4][i])[0]))
                x4=float((re.findall(regex4, self.flags[4][i])[0]))
                if x2!=0:
                    fileObject.write("  for(i="+str(timing)+"; i<"+str(timing+int(x2))+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO -= "+str(x1/x2)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
                fileObject.write("  for(i="+str(timing+int(x2))+"; i<"+str(timing+int(x2)+int(x3))+"; i++)"+'\n')
                fileObject.write("  {"+'\n')
                fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                fileObject.write("  }"+'\n')
                if x4!=0:
                    fileObject.write("  for(i="+str(timing+int(x2)+int(x3))+"; i<"+str(timing2)+"; i++)"+'\n')
                    fileObject.write("  {"+'\n')
                    fileObject.write("    fRO += "+str(x1/x4)+";"+'\n')  #fROprestep还没有定义****************************
                    fileObject.write("    ival = (int32_t)floor(fRO/fLSB)*16;"+'\n')
                    fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
                    fileObject.write("  }"+'\n')
            else:
                timing=timing2
        fileObject.write("  for(i="+str(timing)+"; i<200000; i++)"+'\n')
        fileObject.write("  {"+'\n')
        fileObject.write("    ival=(int32_t)floor(offset.gradient_z/fLSB)*16;"+'\n')
        fileObject.write("    gz[i] = 0x001fffff & (ival | 0x00100000);"+'\n')
        fileObject.write("  }"+'\n')
        fileObject.write("}"+'\n')
        fileObject.close()
            

if __name__=="__main__":
    app=QApplication(sys.argv)
    myWindow=MRI_SD_Widget()
    myWindow.show()
    sys.exit(app.exec_())
