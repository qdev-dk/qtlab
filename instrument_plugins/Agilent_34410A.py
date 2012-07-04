# Agilent_34410A.py class, to perform the communication between the Wrapper and the device
# Pieter de Groot <pieterdegroot@gmail.com>, 2008
# Martijn Schaafsma <qtlab@mcschaafsma.nl>, 2008
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
    This is the driver for the Agilent 34410A Signal Genarator

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

        self.add_parameter('aperture',
            flags=Instrument.FLAG_GETSET, units='s', minval=100e-6, maxval=1, type=types.FloatType)
        self.add_parameter('autorange',
            flags=Instrument.FLAG_GETSET, units='bool', type=types.BooleanType)
        self.add_parameter('range',
            flags=Instrument.FLAG_GETSET, units='Ohm', minval=100., maxval=1e9, type=types.FloatType)
        self.add_parameter('offset_compensation',
            flags=Instrument.FLAG_GETSET, units='bool', type=types.BooleanType)
        self.add_parameter('null_value',
            flags=Instrument.FLAG_GETSET, units='Ohm', minval=-1e-20, maxval=1e-20, type=types.FloatType)
        self.add_parameter('subtract_null_value',
            flags=Instrument.FLAG_GETSET, units='bool', type=types.BooleanType)

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
        Gets the current resistance reading.

        Input:
            None

        Output:
            resistance in Ohms
        '''
        logging.debug(__name__ + ' : getting current resistance reading')
        p = self._visainstrument.ask('READ?')
        try:
            return float(p)
        except ValueError:
            print "Could not convert {0} to float.".format(p)
            return 0.
		
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
        self.get_aperture()
        self.get_autorange()
        self.get_range()
        self.get_offset_compensation()
        self.get_subtract_null_value()
        self.get_null_value()

    def do_get_aperture(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get aperture')
        return float(self._visainstrument.ask('SENS:RES:APER?'))

    def do_set_aperture(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set aperture to %f' % val)
        self._visainstrument.write('SENS:RES:APER %s' % val)

    def do_get_range(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get range')
        return float(self._visainstrument.ask('SENS:RES:RANG?'))

    def do_set_range(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set range to %f' % val)
        self._visainstrument.write('SENS:RES:RANG %s' % val)

    def do_get_null_value(self):
        '''
        Null value is subtracted from the measurement (if option turned on).

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get null value')
        return float(self._visainstrument.ask('SENS:RES:NULL:VAL?'))

    def do_set_null_value(self, val):
        '''
        Null value is subtracted from the measurement (if option turned on).

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set null value to %f' % val)
        self._visainstrument.write('SENS:RES:NULL:VAL %s' % val)

    def do_get_autorange(self):
        '''
        Is autorange on?

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get autorange.')
        return bool(self._visainstrument.ask('SENS:RES:RANG:AUTO?'))

    def do_set_autorange(self, val):
        '''
        Sets autorange on/off.

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set autorange to %f' % val)
        self._visainstrument.write('SENS:RES:RANG:AUTO %s' % int(val))
        

    def do_get_offset_compensation(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get offset_compensation')
        return bool(self._visainstrument.ask('SENS:RES:OCOM?'))

    def do_set_offset_compensation(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set offset_compensation to %f' % val)
        self._visainstrument.write('SENS:RES:OCOM %s' % int(val))
        
    def do_get_subtract_null_value(self):
        '''

        Input:
            None

        Output:
            len (int) : averaging length
        '''
        logging.debug(__name__ + ' : get ')
        return bool(self._visainstrument.ask('SENS:RES:NULL?'))

    def do_set_subtract_null_value(self, val):
        '''

        Input:
            len (int) : averaging length

        Output:
            None
        '''
        logging.debug(__name__ + ' : set subtract_null_value to %f' % val)
        self._visainstrument.write('SENS:RES:NULL %s' % int(val))
