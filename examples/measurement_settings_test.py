# Author: Pierre Barthelemy <P.J.C.Barthelemy@tudelft.nl>
# Modification to runnable example by Rasmus Skytte Eriksen <zrm49@alumni.ku.dk>

# Make sure the modules folder is in your sys.path (should be done in userconfig.py)
import measurement_classes
reload(measurement_classes)
from measurement_classes import *
settings=qt.instruments.get('Measurement-Settings')

#Runnable Example
#Creating Value Instruments:
#dmm1={'instrument':'DMM1','parameter':'readval','multiplication_factor':1,'description':'DMM voltage','units':'V'}
#settings.set_values([dmm1])

#Creating Coordinates to sweep over
#settings.set_coordinates_x([('HP33210A','amplitude',10e-2,10e-1)])
#settings.set_npoints_x(10)

# Start the measurement
#launch2Dmeasurement('runned_example')





#Void Example for using init_scan and init_sweep

def example_init_scan_1():
    print 'This function runs at the beginning of each scan'
def example_init_scan_2():
    print 'This function also runs at the beginning of each scan'

def example_init_sweep_1():
    print 'This function runs at the beginning of each sweep'
def example_init_sweep_2():
    print 'This function also runs at the beginning of each sweep'

capacitance_bridge.set_CoarseAmplitude(value)
Sweep_Parameters['CoarseAmplitude']=value
    
settings.set_init_scan([example_init_scan_1,example_init_scan_2])    
settings.set_init_sweep([settings.dummy_function,example_init_sweep_1,example_init_sweep_2])
settings.set_values([])
settings.set_coordinates_x([])
settings.set_coordinates_y([])
#settings.set_coordinates_y([('gates','LP',30,50,'log')])

settings.set_npoints_y(5)
launch3Dmeasurement('example_init')