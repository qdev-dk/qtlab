# Global namespace

import os
import sys
from qtflow import get_flowcontrol
from instruments import get_instruments
from lib import config as _config
from scripts import Scripts, Script

config = _config.get_config()
# We cannot import Data here, Data import qt, this is a circular import!
# from data import Data
# data = Data.get_named_list()
instruments = get_instruments()
frontpanels = {}
sliders = {}
scripts = Scripts()

flow = get_flowcontrol()
msleep = flow.measurement_idle
mstart = flow.measurement_start
mend = flow.measurement_end

def version():
    version_file = os.path.join(config['execdir'], 'VERSION')
    try:
        f = file(version_file,'r')
        str = f.readline()
        str = str.rstrip('\n\r')
        f.close()
    except:
        str = 'NO VERSION FILE'
    return str

class qApp:
    '''Class to fix a bug in matplotlib.pyplot back-end detection.'''
    @staticmethod
    def startingUp():
        return True

