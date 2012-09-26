# Agilent_34410A.py class, for commucation with an Agilent 34410A multimeter
# Joonas Govenius <joonas.govenius@aalto.fi>, 2012
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
import numpy

class Agilent_34410A(Instrument):
    '''
    This is the driver for the Agilent 34410A multimeter

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'Agilent_34410A', address='<GBIP address>, reset=<bool>')
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the Agilent_34410A, and communicates with the wrapper.

        Input:
          name (string)    : name of the instrument
          address (string) : GPIB address
          reset (bool)     : resets to default values, default=False
        '''
        logging.info(__name__ + ' : Initializing instrument Agilent_34410A')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants
        self._address = address
        self._visainstrument = visa.instrument(self._address)

        self.add_parameter('measurement_function',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, type=types.StringType)
        self.add_parameter('res_nplc',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='', minval=0.006, maxval=100, type=types.FloatType)
        self.add_parameter('res_autorange',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='bool', type=types.BooleanType)
        self.add_parameter('res_range',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='Ohm', minval=100., maxval=1e9, type=types.FloatType)
        self.add_parameter('v_nplc',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='', minval=0.006, maxval=100, type=types.FloatType)
        self.add_parameter('v_autorange',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='bool', type=types.BooleanType)
        self.add_parameter('v_range',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='V', minval=0.1, maxval=1e3, type=types.FloatType)
        self.add_parameter('offset_compensation',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='bool', type=types.BooleanType)
        self.add_parameter('res_null_value',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='Ohm', minval=-1e-20, maxval=1e-20, type=types.FloatType)
        self.add_parameter('subtract_res_null_value',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, units='bool', type=types.BooleanType)

        self.add_function('reset')
        self.add_function ('get_all')
        self.add_function('get_reading')


        if (reset):
            self.reset()
        else:
            self.get_all()

    def reset(self):
        '''
        Resets the instrument to default values

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : resetting instrument')
        self._visainstrument.write('*RST')
        self.get_all()

    def get_reading(self):
        '''
        Gets the current reading.

        Input:
            None

        Output:
            resistance in Ohms or voltage in Volts
        '''
        logging.debug(__name__ + ' : getting current reading')
        p = self._visainstrument.ask('READ?')
        try:
            return float(p)
        except ValueError:
            print "Could not convert {0} to float.".format(p)
            return float('nan')
		
    def get_all(self):
        '''
        Reads all implemented parameters from the instrument,
        and updates the wrapper.

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : get all')
        self.get_measurement_function()
        self.get_res_nplc()
        self.get_res_autorange()
        self.get_res_range()
        self.get_v_nplc()
        self.get_v_autorange()
        self.get_v_range()
        self.get_offset_compensation()
        self.get_subtract_res_null_value()
        self.get_res_null_value()

    def do_get_measurement_function(self):
        '''
	Ask what is being measured.

        Input:
            None

        Output:
            function (string) : what is being measured ('RES', 'VOLT:DC')
        '''
	r = self._visainstrument.ask('SENS:FUNC?')
        logging.debug(__name__ + ' : get measurement function: ' + r)
	r = r.replace('"','')
	if r == 'VOLT': r = 'VOLT:DC'
        return r

    def do_set_measurement_function(self, val):
        '''
	Set what is being measured.

        Input:
            function (string) : what is being measured ('RES', 'VOLT:DC')

        Output:
            None
        '''
	if val == 'VOLT': val = 'VOLT:DC'
        logging.debug(__name__ + ' : set measurement_function to %s' % val)
	if val not in ['RES', 'VOLT:DC']:
		raise Exception('Unknown measurement function: %s' % val)
        self._visainstrument.write('SENS:FUNC "%s"' % val)
	
    def do_get_res_nplc(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get res_nplc')
        return float(self._visainstrument.ask('SENS:RES:NPLC?'))

    def do_set_res_nplc(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set res_nplc to %f' % val)
        self._visainstrument.write('SENS:RES:NPLC %s' % val)

    def do_get_v_nplc(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get v_nplc')
        return float(self._visainstrument.ask('SENS:VOLT:DC:NPLC?'))

    def do_set_v_nplc(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set v_nplc to %f' % val)
        self._visainstrument.write('SENS:VOLT:DC:NPLC %s' % val)

    def do_get_res_range(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get res_range')
        return float(self._visainstrument.ask('SENS:RES:RANG?'))

    def do_set_res_range(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set res_range to %f' % val)
        self._visainstrument.write('SENS:RES:RANG %s' % val)

    def do_get_v_range(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get v_range')
        return float(self._visainstrument.ask('SENS:VOLT:DC:RANG?'))

    def do_set_v_range(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set v_range to %f' % val)
        self._visainstrument.write('SENS:VOLT:DC:RANG %s' % val)

    def do_get_res_null_value(self):
        '''
        Null value is subtracted from the measurement (if option turned on).

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get res_null value')
        return float(self._visainstrument.ask('SENS:RES:NULL:VAL?'))

    def do_set_res_null_value(self, val):
        '''
        Null value is subtracted from the measurement (if option turned on).

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set res_null value to %f' % val)
        self._visainstrument.write('SENS:RES:NULL:VAL %s' % val)

    def do_get_res_autorange(self):
        '''
        Is res_autorange on?

        Input:
            None

        Output:
            len (int) : averaging length
        '''
	r = self._visainstrument.ask('SENS:RES:RANG:AUTO?')
        logging.debug(__name__ + ' : get res_autorange: ' + r)
        return bool(int(r))

    def do_set_res_autorange(self, val):
        '''
        Sets res_autorange on/off.

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set res_autorange to %f' % val)
        self._visainstrument.write('SENS:RES:RANG:AUTO %s' % int(val))

    def do_get_v_autorange(self):
        '''
        Is v_autorange on?

        Input:
            None

        Output:
            len (int) : averaging length
        '''
	r = self._visainstrument.ask('SENS:VOLT:DC:RANG:AUTO?')
        logging.debug(__name__ + ' : get v_autorange: ' + r)
        return bool(int(r))

    def do_set_v_autorange(self, val):
        '''
        Sets v_autorange on/off.

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set v_autorange to %f' % val)
        self._visainstrument.write('SENS:VOLT:DC:RANG:AUTO %s' % int(val))
        
    def do_get_offset_compensation(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
	r = self._visainstrument.ask('SENS:RES:OCOM?')
        logging.debug(__name__ + ' : get offset_compensation: ' + r)
        return bool(int(r))

    def do_set_offset_compensation(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set offset_compensation to %f' % val)
        self._visainstrument.write('SENS:RES:OCOM %s' % int(val))
        
    def do_get_subtract_res_null_value(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
	r = self._visainstrument.ask('SENS:RES:NULL?')
        logging.debug(__name__ + ' : get res_null value subtraction: ' + r)
        return bool(int(r))

    def do_set_subtract_res_null_value(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set subtract_res_null_value to %f' % val)
        self._visainstrument.write('SENS:RES:NULL %s' % int(val))
