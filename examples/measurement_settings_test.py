# Author: Pierre Barthelemy <P.J.C.Barthelemy@tudelft.nl>
# Make sure the modules folder is in your sys.path (should be done in userconfig.py)
import measurement_classes
reload(measurement_classes)
from measurement_classes import *
settings=qt.instruments.get('measurement_settings')
settings.set_filename_script(inspect.getfile(inspect.currentframe()))

#Runnable Example
#Creating Value Instruments:
#keithley1={'instrument':'keithley','parameter':'readlastval','multiplication_factor':1,'description':'QPC current','units':'mV'}
#settings.set_values([keithley1,keithley2])
#Creating Coordinates
#settings.set_coordinates_x([('gates','LS',10,20)])
#settings.set_coordinates_y([('gates','LP',30,50)])
#settings.set_npoints_x(10)
#settings.set_npoints_y(5)
#launch3Dmeasurement('runned_example')


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

settings.set_npoints_x(10)
settings.set_npoints_y(5)
launch3Dmeasurement('example_init')

