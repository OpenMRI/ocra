# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Square_Character.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
#from Main_Dialog import MainDialog

class Ui_square_Dialog(QDialog):
    def __init__(self,stringReceiver,parent=None):
        super(Ui_square_Dialog,self).__init__()
        self.setupUi(self)
        self.timeLimit=float(stringReceiver)
    def setupUi(self, square_Dialog):
        square_Dialog.setObjectName("square_Dialog")
        square_Dialog.resize(400, 175)
        self.buttonBox = QtWidgets.QDialogButtonBox(square_Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(30, 130, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.layoutWidget = QtWidgets.QWidget(square_Dialog)
        self.layoutWidget.setGeometry(QtCore.QRect(20, 10, 353, 109))
        self.layoutWidget.setObjectName("layoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.layoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.lineEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.lineEdit.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.lineEdit.setReadOnly(True)
        self.lineEdit.setObjectName("lineEdit")
        self.verticalLayout.addWidget(self.lineEdit)
        self.lineEdit_2 = QtWidgets.QLineEdit(self.layoutWidget)
        self.lineEdit_2.setReadOnly(True)
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.verticalLayout.addWidget(self.lineEdit_2)
        self.lineEdit_3 = QtWidgets.QLineEdit(self.layoutWidget)
        self.lineEdit_3.setReadOnly(True)
        self.lineEdit_3.setObjectName("lineEdit_3")
        self.verticalLayout.addWidget(self.lineEdit_3)
        self.lineEdit_4 = QtWidgets.QLineEdit(self.layoutWidget)
        self.lineEdit_4.setReadOnly(True)
        self.lineEdit_4.setObjectName("lineEdit_4")
        self.verticalLayout.addWidget(self.lineEdit_4)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 4, 1)
        self.AmplEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.AmplEdit.setObjectName("AmplEdit")
        self.gridLayout.addWidget(self.AmplEdit, 0, 1, 1, 1)
        self.IncreaseEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.IncreaseEdit.setObjectName("IncreaseEdit")
        self.gridLayout.addWidget(self.IncreaseEdit, 1, 1, 1, 1)
        self.HoldingEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.HoldingEdit.setObjectName("HoldingEdit")
        self.gridLayout.addWidget(self.HoldingEdit, 2, 1, 1, 1)
        self.DecreaseEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.DecreaseEdit.setObjectName("DecreaseEdit")
        self.gridLayout.addWidget(self.DecreaseEdit, 3, 1, 1, 1)

        self.retranslateUi(square_Dialog)
        self.buttonBox.accepted.connect(self.SquareMade)
        self.buttonBox.rejected.connect(square_Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(square_Dialog)
        square_Dialog.show()

    def retranslateUi(self, square_Dialog):
        _translate = QtCore.QCoreApplication.translate
        square_Dialog.setWindowTitle(_translate("square_Dialog", "Dialog"))
        self.lineEdit.setText(_translate("square_Dialog", "Amplitude/(T/s)"))
        self.lineEdit_2.setText(_translate("square_Dialog", "Increase duration/us"))
        self.lineEdit_3.setText(_translate("square_Dialog", "holding duration/us"))
        self.lineEdit_4.setText(_translate("square_Dialog", "Decrease duration/us"))
        
    def SquareMade(self):
        if self.AmplEdit.text()=="" or self.IncreaseEdit.text()=="" or self.HoldingEdit.text()=="" or self.DecreaseEdit.text()==""\
         or self.AmplEdit.text()=="0" or self.IncreaseEdit.text()=="0" or self.HoldingEdit.text()=="0" or self.DecreaseEdit.text()=="0":
             reply=QMessageBox.information(self,"inform","zero or blank is not allowed!")
        else:
            if(abs(float(self.IncreaseEdit.text())+float(self.HoldingEdit.text())+float(self.DecreaseEdit.text())-self.timeLimit)<1e-1):
                self.string=str()
                self.string=u'Amplitude:%s Increase duration:%s Holding duration:%s Decrease duration:%s The END' %(self.AmplEdit.text(),
                                                                                                   self.IncreaseEdit.text(),
                                                                                                   self.HoldingEdit.text(),
                                                                                                   self.DecreaseEdit.text())
                self.accept()
            else:
                reply=QMessageBox.information(self,"warning","Set the time and make sure that you design matches time!")


if __name__=="__main__":
    app = QApplication(sys.argv)
    main = Ui_square_Dialog()
    main.show()
    sys.exit(app.exec_())
