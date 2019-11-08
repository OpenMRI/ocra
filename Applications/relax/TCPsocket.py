# create global TCP socket

from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket

socket = QTcpSocket()

connected = QAbstractSocket.ConnectedState
unconnected = QAbstractSocket.UnconnectedState
