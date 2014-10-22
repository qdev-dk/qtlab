# Keithley_6487.py class, to perform the communication between the Wrapper and the device
# Guen Prawiroatmodjo <guen@nbi.dk>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from instrument import Instrument
import visa
import types
import logging
from time import sleep
import struct
import numpy
import qt

class Keithley_6487(Instrument):
    '''
    This is the python driver for the Keithley 6487
    Picoammeter

    Usage:
    Initialise with
    <name> = instruments.create('<name>', 'Keithley_6487', address='<GPIB address>',
        reset=<bool>)

    The last parameter is optional. Default is reset=False
    '''

    def __init__(self, name, address, current_limit=2.5e-3,  reset=False):
        '''
        Initializes the HP_3478A, and communicates with the wrapper

        Input:
            name (string)    : name of the instrument
            address (string) : GPIB address
            reset (bool)     : resets to default values, default=false
        '''
        logging.info(__name__ + ' : Initializing instrument Keithley_6487')
        Instrument.__init__(self, name)

        self._address = address
        self._visainstrument = visa.instrument(self._address)

        self._visainstrument.timeout = 30
    
        self.add_parameter('current_range', units='A', minval=-0.021, maxval=0.021, flags=Instrument.FLAG_GETSET, type=types.FloatType)
        self.add_parameter('current_limit',flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                1: '25e-6',
                2: '250e-6',
                3: '2.5e-3',
                4: '25e-3'
                })
        self.add_parameter('voltage_range', units='V',flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                10: '10',
                50: '50',
                500: '500'
                })
        self.add_parameter('output_voltage', units='V', tags=['sweep'], minval=-505, maxval=505,flags=Instrument.FLAG_GETSET, type=types.FloatType)
        self.add_parameter('voltage_status', flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                0: 'OFF',
                1: 'ON'
                })
        self.add_parameter('autorange', flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                0: 'OFF',
                1: 'ON'
                })
        self.add_parameter('zero_check', flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                0: 'OFF',
                1: 'ON'
                })
        self.add_parameter('zero_correct', flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                0: 'OFF',
                1: 'ON'
                })
        self.add_parameter('function', 
                flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                0: 'Current',
                1: 'Resistance'
                })
        self.add_parameter('averaging', flags=Instrument.FLAG_GETSET, type=types.IntType,
        format_map={
                0: 'OFF',
                1: 'ON'
                })
        self.add_parameter('averaging_count', minval=2, maxval=100, flags=Instrument.FLAG_GETSET, type=types.IntType)
        self.add_parameter('readval', flags=Instrument.FLAG_GET, tags=['measure'], type=types.FloatType)
        self.add_parameter('nplc', flags=Instrument.FLAG_GETSET, type=types.FloatType)
    
        self.add_function('reset')
        self.add_function('read')
        
        self.get_all()
    
    def get_all(self):
        self.get_readval()
        self.get_autorange()
        self.get_current_limit()
        self.get_current_range()
        self.get_function()
        self.get_output_voltage()
        self.get_voltage_range()
        self.get_voltage_status()
        self.get_zero_check()
        self.get_zero_correct()
        self.get_averaging()
        self.get_averaging_count()
        
    def reset(self):
        '''
        Return to default settings
        '''
        self._visainstrument.write('*RST')
    
    def read(self):
        '''
        Trigger and read value
        '''
        return self.get_readval()
    
    def do_get_autorange(self):
        '''
        Get auto range
        Output:
            val(str or int): 'ON'/1 or 'OFF'/0
        '''
        return int(self._visainstrument.ask('RANG:AUTO?'))
    
    def do_set_autorange(self, val):
        '''
        Set auto range
        Input:
            val(str or int): 'ON'/1 or 'OFF'/0
        '''
        format_map={
            0: 'OFF',
            1: 'ON'
            }
        val = format_map.get(val)
        self._visainstrument.write('RANG:AUTO %s' %val)
    
    def do_get_zero_check(self):
        '''
        Get zero check
        Output:
            val(str or int): 'ON'/1 or 'OFF'/0
        '''
        return int(self._visainstrument.ask('SYST:ZCH?'))
    
    def do_set_zero_check(self, val):
        '''
        Enable or disable zero check
        Input:
            val(str or int): 'ON'/1 or 'OFF'/0
        '''
        format_map={
            0: 'OFF',
            1: 'ON'
            }
        val = format_map.get(val)
        self._visainstrument.write('SYST:ZCH %s' %val)

    def zero_correct(self):
        '''
        Perform zero correct
        *RST ' Return 6487 to GPIB defaults.
        FORM:ELEM READ,UNIT ' Measurement, units elements only.
        SYST:ZCH ON ' Enable zero check.
        RANG 2e-9 ' Select the 2nA range.
        INIT ' Trigger reading to be used as zero
        ' correction.
        SYST:ZCOR:ACQ ' Use last reading taken as zero 
        ' correct value.
        SYST:ZCOR ON
        '''
        self.reset()
        self._visainstrument.write('FORM:ELEM READ,UNIT')
        self.set_zero_check(1)
        self.set_current_range(2e-9)
        # Read a value to zero correct
        self._visainstrument.write('INIT')
        self._visainstrument.write('SYST:ZCOR:ACQ')
        # Set zero correct on
        self.set_zero_correct(1)
        self.set_autorange(1)
        
    def do_get_zero_correct(self):
        '''
        Get zero correct
        Output:
            val(str): 'ON' or 'OFF'
        '''
        return int(self._visainstrument.ask('SYST:ZCOR?'))

    def do_set_zero_correct(self, val):
        '''
        Enable or disable zero correct
        Input:
            val(str): 'ON' or 'OFF'
        '''
        format_map={
                0: 'OFF',
                1: 'ON'
                }
        val = format_map.get(val)
        self._visainstrument.write('SYST:ZCOR %s' %val)
    
    def do_get_current_range(self):
        '''
        Get current range (-0.021 to 0.021A)
        '''
        return float(self._visainstrument.ask('RANG?'))
    
    def do_set_current_range(self, val):
        '''
        Set range (-0.021 to 0.021A)
        '''
        val = str(val)
        self._visainstrument.write('RANG %s' %val)
    
    def do_get_current_limit(self):
        '''
        Get current limit (A)
            1: '25e-6',
            2: '250e-6',
            3: '2.5e-3',
            4: '25e-3'
        '''
        return float(self._visainstrument.ask('SOUR:VOLT:ILIM?'))
    
    def do_set_current_limit(self, val):
        '''
        Set current limit (A)
            1: '25e-6',
            2: '250e-6',
            3: '2.5e-3',
            4: '25e-3'
        '''
        if type(val) != types.IntType:
            val = str(val)
            format_map={
                    1: '25e-6',
                    2: '250e-6',
                    3: '2.5e-3',
                    4: '25e-3'
                    }
            val = format_map.get(val)
        self._visainstrument.write('SOUR:VOLT:ILIM %s' %val)
    
    def do_get_voltage_range(self):
        '''
        Get range (10, 50 or 500)
        '''
        return float(self._visainstrument.ask('SOUR:VOLT:RANG?'))
    
    def do_set_voltage_range(self, val):
        '''
        Set range (10, 50 or 500)
        '''
        val = str(val)
        self._visainstrument.write('SOUR:VOLT:RANG %s' %val)
    
    def do_get_voltage_status(self):
        '''
        Get voltage output status
        '''
        return int(self._visainstrument.ask('SOUR:VOLT:STAT?'))
    
    def do_set_voltage_status(self, val):
        '''
        Set voltage output status
        '''
        format_map={
                0: 'OFF',
                1: 'ON'
                }
        val = format_map.get(val)
        self._visainstrument.write('SOUR:VOLT:STAT %s' %val)
    
    def do_get_output_voltage(self):
        '''
        Get output voltage (-500 to 500 V)
        '''
        return float(self._visainstrument.ask('SOUR:VOLT?'))
    
    def do_set_output_voltage(self, val):
        '''
        Set output voltage (-500 to 500 V)
        '''
        val = str(val)
        self._visainstrument.write('SOUR:VOLT %s' %val)
    
    def do_get_function(self):
        '''
        Get read function
        Output:
            0: Current
            1: Resistance
        '''
        return int(self._visainstrument.ask('SENS:OHMS?'))
    
    def do_set_function(self, val):
        '''
        Set read function
        '''
        format_map={
                0: 'OFF',
                1: 'ON'
                }
        val = format_map.get(val)
        self._visainstrument.write('SENS:OHMS %s' %val)
    
    def do_get_averaging(self):
        '''
        Get averaging
        '''
        return int(self._visainstrument.ask('AVER?'))
    
    def do_set_averaging(self, val):
        '''
        Set averaging
        '''
        format_map={
                0: 'OFF',
                1: 'ON'
                }
        val = format_map.get(val)
        self._visainstrument.write('AVER %s' %val)
    
    def do_get_averaging_count(self):
        '''
        Get averaging count
        '''
        return float(self._visainstrument.ask('AVER:COUN?'))
    
    def do_set_averaging_count(self, val):
        '''
        Set averaging count
        '''
        val = str(val)
        self._visainstrument.write('AVER:COUN %s' %val)
    
    def do_get_readval(self):
        '''
        Trigger and return one reading
        '''
        self.set_zero_check(0)
        result = self._visainstrument.ask('READ?')
        if self.get_function() == 0:
            return float(result[:result.find('A')])
        elif self.get_function() == 1:
            return float(result[:result.find('OHMS')])
        else:
            return result
        
    def do_set_nplc(self, val):
        '''
        Set NPLC (averaging)
        '''
        self._visainstrument.write('SENS:CURR:DC:NPLC %s' %val)
        
    def do_get_nplc(self):
        '''
        Get NPLC (averaging)
        '''
        return self._visainstrument.ask('SENS:CURR:DC:NPLC?')