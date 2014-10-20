# This file contains user-specific settings for qtlab.
# It is run as a regular python script.
import os, sys

# Do not change the following line unless you know what you are doing
config.remove([
            'datadir',
            'startdir',
            'scriptdirs',
            'user_ins_dir',
            'startgui',
            'gnuplot_terminal',
            ])

# QTLab instance name and port for networked operation
config['instance_name'] = 'qtlab_n1'
config['port'] = 12002

# A list of allowed IP ranges for remote connections
config['allowed_ips'] = (
#    '130.161.*.*',
#    '145.94.*.*',
)

# Start instrument server to share with instruments with remote QTLab?
config['instrument_server'] = False

## This sets a default location for data-storage
# If you want to store your data relative the qtlab folder Use s
# config['datadir'] = os.path.join(config['execdir'], 'YOUR-RELATIVE-PATH-HERE')
config['datadir'] = 'C:\YOUR-DATA-DIRECTORY-PATH'

## This sets a default directory for qtlab to start in
#config['startdir'] = 'd:/scripts'

## A default script (or list of scripts) to run after qtlab started
config['startscript'] = []      #e.g. 'initscript1.py'

## A default script (or list of scripts) to run when qtlab closes
config['exitscript'] = []       #e.g. ['closescript1.py', 'closescript2.py']

# Add directories containing scripts here. All scripts will be added to the
# global namespace as functions.
config['scriptdirs'] = [
        'examples/scripts',
]

## This sets a user instrument directory
## Any instrument drivers placed here will take
## preference over the general instrument drivers
#config['user_insdir'] = 'd:/instruments'

## For adding additional folders to the 'systm path'
## so python can find your modules
sys.path.append(os.path.join(config['execdir'], 'modules'))
sys.path.append(os.path.join(config['execdir'], 'examples'))


# Whether to start the GUI automatically
config['startgui'] = True

# Default gnuplot terminal
#config['gnuplot_terminal'] = 'x11'
#config['gnuplot_terminal'] = 'wxt'
#config['gnuplot_terminal'] = 'windows'

# Enter a filename here to log all IPython commands
config['ipython_logfile'] = ''      #e.g. 'command.log'

## Data naming
# By defult the data is stored in the "datadir" folder in a subfolder with
# date of the measurement, and herein a subfolder with timestamp and name
# To set an auto-increment filename generator use the following:
import data, qt
gen = data.DataStorageGenerator(config['datadir'],datesubdir=True, timesubdir=True, incremental=True)
qt.Data.set_filename_generator(gen)
# For more data name generators, check out data.py