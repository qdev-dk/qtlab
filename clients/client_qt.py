# Script to start a Qt-based QTLab client
#
# Author: Wolfgang Pfaff <w.pfaff@tudelft.nl>
# Author: Reinier Heeres <reinier@heeres.eu>

import os
import sys
import socket
import logging

import client_shared
args, pargs = client_shared.process_args()

# Reinier: I need to comment this out...
# we need this for ETS to work properly with pyqt
#os.environ['ETS_TOOLKIT'] = 'qt4'
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
from PyQt4 import QtGui, QtCore

from lib.network.tcpserverqt import QtQtlabHandler
from lib.network import object_sharer as objsh

def close_client(self):
    app.exit()
    app.quit()
    sys.exit()

# here we go...
if __name__ == "__main__":
    global app
    app = QtGui.QApplication.instance()
    if app is None:
        app = QtGui.QApplication([sys.argv[0],])

    # open the socket and start the client.
    # will fail if no connection to qtlab is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', args.port))
    handler = QtQtlabHandler(sock, 'client', 'server')

    # Be sure to talk to the qtlab instance that we just connected to
    flow = objsh.helper.find_object('%s:flow' % handler.client.get_instance_name())
    flow.connect('close-gui', close_client)

    if args.module:
        logging.info('Importing %s', args.module)
        __import__(args.module, globals())

    app.exec_()
