# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Pulse_Character.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class Ui_pulse_Dialog(QDialog):
    def __init__(self,parent=None):
        super(Ui_pulse_Dialog,self).__init__()
        self.setupUi(self)
    def setupUi(self, pulse_Dialog):
        pulse_Dialog.setObjectName("pulse_Dialog")
        pulse_Dialog.resize(400, 175)
        self.buttonBox = QtWidgets.QDialogButtonBox(pulse_Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(30, 130, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.layoutWidget = QtWidgets.QWidget(pulse_Dialog)
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
        self.orderEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.orderEdit.setObjectName("orderEdit")
        self.gridLayout.addWidget(self.orderEdit, 0, 1, 1, 1)
        self.centerFreqEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.centerFreqEdit.setObjectName("centerFreqEdit")
        self.gridLayout.addWidget(self.centerFreqEdit, 1, 1, 1, 1)
        self.BWEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.BWEdit.setObjectName("BWEdit")
        self.gridLayout.addWidget(self.BWEdit, 2, 1, 1, 1)
        self.durationEdit = QtWidgets.QLineEdit(self.layoutWidget)
        self.durationEdit.setObjectName("durationEdit")
        self.gridLayout.addWidget(self.durationEdit, 3, 1, 1, 1)

        self.retranslateUi(pulse_Dialog)
        self.buttonBox.accepted.connect(self.pulseMade)
        self.buttonBox.rejected.connect(pulse_Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(pulse_Dialog)
        pulse_Dialog.show()

    def retranslateUi(self, pulse_Dialog):
        _translate = QtCore.QCoreApplication.translate
        pulse_Dialog.setWindowTitle(_translate("pulse_Dialog", "Dialog"))
        self.lineEdit.setText(_translate("pulse_Dialog", "order of envelop"))
        self.lineEdit_2.setText(_translate("pulse_Dialog", "center frequency/kHz"))
        self.lineEdit_3.setText(_translate("pulse_Dialog", "pulse Bandwidth/kHz"))
        self.lineEdit_4.setText(_translate("pulse_Dialog", "pulse duration/ms"))
        
    def pulseMade(self):
        if self.orderEdit.text()=="" or self.centerFreqEdit.text()=="" or self.BWEdit.text()=="" or self.durationEdit.text()==""\
         or self.orderEdit.text()=="0" or self.centerFreqEdit.text()=="0" or self.BWEdit.text()=="0" or self.durationEdit.text()=="0":
             reply=QMessageBox.information(self,"inform","zero or blank is not allowed!")
        else:
            self.string=str()
            self.string=u'order:%s Center frequency:%s Bandwidth:%s Pulse duration:%s The END' %(self.orderEdit.text(),
                                                                                                 self.centerFreqEdit.text(),
                                                                                                 self.BWEdit.text(),
                                                                                                 self.durationEdit.text())
            self.accept()

'''
if __name__=="__main__":
    app = QApplication(sys.argv)
    main = Ui_pulse_Dialog()
    main.show()
    sys.exit(app.exec_())
'''