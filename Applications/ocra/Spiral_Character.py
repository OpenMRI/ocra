# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Spiral_Character.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class Ui_spiral_Dialog(QDialog):
    def __init__(self,parent=None):
        super(Ui_spiral_Dialog,self).__init__()
        self.setupUi(self)
    def setupUi(self, spiral_Dialog):
        spiral_Dialog.setObjectName("spiral_Dialog")
        spiral_Dialog.resize(400, 148)
        self.buttonBox = QtWidgets.QDialogButtonBox(spiral_Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(30, 100, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.widget = QtWidgets.QWidget(spiral_Dialog)
        self.widget.setGeometry(QtCore.QRect(23, 12, 351, 79))
        self.widget.setObjectName("widget")
        self.formLayout = QtWidgets.QFormLayout(self.widget)
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.formLayout.setObjectName("formLayout")
        self.lineEdit = QtWidgets.QLineEdit(self.widget)
        self.lineEdit.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.lineEdit.setReadOnly(True)
        self.lineEdit.setObjectName("lineEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.lineEdit)
        self.AmplEdit = QtWidgets.QLineEdit(self.widget)
        self.AmplEdit.setObjectName("AmplEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.AmplEdit)
        self.lineEdit_2 = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_2.setReadOnly(True)
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.lineEdit_2)
        self.omegaEdit = QtWidgets.QLineEdit(self.widget)
        self.omegaEdit.setObjectName("omegaEdit")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.omegaEdit)
        self.lineEdit_3 = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_3.setObjectName("lineEdit_3")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.lineEdit_3)
        self.durationEdit = QtWidgets.QLineEdit(self.widget)
        self.durationEdit.setObjectName("durationEdit")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.durationEdit)

        self.retranslateUi(spiral_Dialog)
        self.buttonBox.accepted.connect(self.SpiralMade)
        self.buttonBox.rejected.connect(spiral_Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(spiral_Dialog)
        spiral_Dialog.show()

    def retranslateUi(self, spiral_Dialog):
        _translate = QtCore.QCoreApplication.translate
        spiral_Dialog.setWindowTitle(_translate("spiral_Dialog", "Dialog"))
        self.lineEdit.setText(_translate("spiral_Dialog", "Amplitude/(T/s)"))
        self.lineEdit_2.setText(_translate("spiral_Dialog", "angular velocity/us"))
        self.lineEdit_3.setText(_translate("spiral_Dialog", "duration/us"))

    def SpiralMade(self):
        if self.AmplEdit.text()=="" or self.omegaEdit.text()=="" or self.durationEdit.text()==""\
         or self.AmplEdit.text()=="0" or self.omegaEdit.text()=="0" or self.durationEdit.text()=="0":
            reply=QMessageBox.information(self,"inform","zero or blank is not allowed!")
        else:
            self.string=str()
            self.string=u'SpiralAmplitude:%s Angular velocity:%s Duration:%s The END' %(self.AmplEdit.text(),
                                                                                        self.omegaEdit.text(),
                                                                                        self.durationEdit.text())
            self.accept()