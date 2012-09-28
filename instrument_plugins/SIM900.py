# SIM_900.py, Stanford Research 900 Mainframe (mainly for SIM928 voltage sources) driver
# KYT
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
import time
import numpy as np

class SIM900(Instrument):
    '''
    This is the python driver for the Lock-In SR830 from Stanford Research Systems.

    Usage:
    Initialize with
    <name> = instruments.create('name', 'SR830', address='<GPIB address>',
        reset=<bool>)
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the SIM900.

        Input:
            name (string)    : name of the instrument
            address (string) : GPIB address
            reset (bool)     : resets to default values, default=false

        Output:
            None
        '''
        logging.info(__name__ + ' : Initializing instrument SIM900')
        Instrument.__init__(self, name, tags=['physical'])
        self._address = address
        self._visainstrument = visa.instrument(self._address)

        self.add_parameter('port1_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port1_on', type=types.BooleanType)

        self.add_parameter('port2_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port2_on', type=types.BooleanType)

        self.add_parameter('port3_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port3_on', type=types.BooleanType)

        self.add_parameter('port4_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port4_on', type=types.BooleanType)

        self.add_parameter('port5_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port5_on', type=types.BooleanType)

        self.add_parameter('port6_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port6_on', type=types.BooleanType)

        self.add_parameter('port7_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port7_on', type=types.BooleanType)

        self.add_parameter('port8_voltage', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=-20., maxval=20.,
            units='V', format='%.04e')
        self.add_parameter('port8_on', type=types.BooleanType)

        self._ramp_stepsize = 0.02
        self._ramp_delaytime = 0.1
        self.add_parameter('ramp_stepsize', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=0., maxval=50., units='V', format='%.04e')
        self.add_parameter('ramp_delaytime', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            minval=0., maxval=100., units='s', format='%.04e')

        self.add_function('reset')
        self.add_function('get_all')
        self.add_function('set_port_voltage')
        self.add_function('get_port_voltage')
        self.add_function('set_port_on')
        self.add_function('get_port_on')

        if reset:
            self.reset()
        else:
            self.get_all()

    # Functions
    def reset(self):
        '''
        Resets the instrument to default values

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : Resetting instrument')
        self._visainstrument.write('*RST')
        self.get_all()

    def get_all(self):
        '''
        Reads all implemented parameters from the instrument,
        and updates the wrapper.

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : reading all settings from instrument')
        self.get_port1_voltage()
        self.get_port1_on()
        self.get_port2_voltage()
        self.get_port2_on()
        self.get_port3_voltage()
        self.get_port3_on()
        self.get_port4_voltage()
        self.get_port4_on()
        self.get_port5_voltage()
        self.get_port5_on()
        self.get_port6_voltage()
        self.get_port6_on()
        self.get_port7_voltage()
        self.get_port7_on()
        self.get_port8_voltage()
        self.get_port8_on()
        self.get_ramp_stepsize()
        self.get_ramp_delaytime()

        
    def clear_output_buffer(self, port):
        for j in range(30):
            bytes_waiting = self._visainstrument.ask('NOUT? %s' % port)

            if int(bytes_waiting) == 0:
                return
            else:
                self._visainstrument.ask('GETN? %s,80' % port)
                self._visainstrument.write('FLSO %s' % port)
                if j%10 == 0: logging.debug(__name__ + ' : output bytes waiting for port %s: %s' % (port, bytes_waiting))
        
        assert(False)

    def wait_until_input_read(self, port):
        for j in range(30):
            bytes_waiting = self._visainstrument.ask('NINP? %s' % port)
            if int(bytes_waiting) == 0:
                return
            else:
                if j%10 == 0: logging.debug(__name__ + ' : input bytes waiting for port %s: %s' % (port, bytes_waiting))
                time.sleep(0.01 * (1+j))

        
        assert(False)

    def _set_voltage(self, port, voltage):
        logging.debug(__name__ + ' : setting port %s voltage to %s V' % (port, voltage))
        
        stepsize = self.get_ramp_stepsize()
        delay = self.get_ramp_delaytime()
        
        old = self._get_voltage(port)
        if np.isnan(old): old = voltage
        
        for v in np.linspace(old, voltage, 2 + int(np.abs(voltage-old)/stepsize)):
            self._visainstrument.write('SNDT %s,"VOLT %s"' % (port, v))
            time.sleep(delay)  # wait time between steps

    def _get_voltage(self, port):
        self.clear_output_buffer(port)
        
        self._visainstrument.write('SNDT %s,"VOLT?"' % port)
        #self.wait_until_input_read(port)
        time.sleep(0.1)
        r = self._visainstrument.ask('GETN? %s,80' % port)
        logging.debug(__name__ + ' : getting port %s voltage: %s' % (port, r))
        
        assert(r[:2]=="#3")
        nbytes = int(r[2:5])

        if (nbytes < 1):
            return float('nan')
        else:
            bytes = r[5:5+nbytes].replace("\n","").replace("\r","")
            logging.debug(__name__ + ' : parsed voltage response: %s' % bytes)
            return float(bytes)

    def _set_on(self, port, val):
        logging.debug(__name__ + ' : setting port %s output to %s' % (port, val))
        self._visainstrument.write('SNDT %s,"EXON %s"' % (port, int(val)))

    def _get_on(self, port):
        self.clear_output_buffer(port)

        self._visainstrument.write('SNDT %s,"EXON?"' % port)
        #self.wait_until_input_read(port)
        time.sleep(0.1)
        r = self._visainstrument.ask('GETN? %s,80' % port)
        logging.debug(__name__ + ' : getting port %s output state: %s' % (port, r))
        
        assert(r[:2]=="#3")
        nbytes = int(r[2:5])

        if (nbytes < 1):
            return None
        else:
            bytes = r[5:5+nbytes].replace("\n","").replace("\r","")
            logging.debug(__name__ + ' : parsed output on response: %s' % bytes)
            return bool(bytes)

    def set_port_voltage(self, port, voltage):
        if not isinstance(port, int):
          raise Exception('port must be specified as an integer, not %s.' % str(port))
        if port < 1 or port > 8:
          raise Exception('port must be between 1 and 8, not %s.' % str(port))
        getattr(self, 'set_port%s_voltage' % str(port))(voltage)

    def get_port_voltage(self, port):
        if not isinstance(port, int):
          raise Exception('port must be specified as an integer, not %s.' % str(port))
        if port < 1 or port > 8:
          raise Exception('port must be between 1 and 8, not %s.' % str(port))
        return getattr(self, 'get_port%s_voltage' % str(port))()

    def set_port_on(self, port, val):
        if not isinstance(port, int):
          raise Exception('port must be specified as an integer, not %s.' % str(port))
        if port < 1 or port > 8:
          raise Exception('port must be between 1 and 8, not %s.' % str(port))
        getattr(self, 'set_port%s_on' % str(port))(val)

    def get_port_on(self, port):
        if not isinstance(port, int):
          raise Exception('port must be specified as an integer, not %s.' % str(port))
        if port < 1 or port > 8:
          raise Exception('port must be between 1 and 8, not %s.' % str(port))
        return getattr(self, 'get_port%s_on' % str(port))()

    def do_set_ramp_stepsize(self, stepsize):
        self._ramp_stepsize = stepsize
    def do_get_ramp_stepsize(self):
        return self._ramp_stepsize

    def do_set_ramp_delaytime(self, delay):
        self._ramp_delaytime = delay
    def do_get_ramp_delaytime(self):
        return self._ramp_delaytime

    def do_set_port1_voltage(self, voltage):
        self._set_voltage(1, voltage)
    def do_get_port1_voltage(self):
        return self._get_voltage(1)
    def do_set_port2_voltage(self, voltage):
        self._set_voltage(2, voltage)
    def do_get_port2_voltage(self):
        return self._get_voltage(2)
    def do_set_port3_voltage(self, voltage):
        self._set_voltage(3, voltage)
    def do_get_port3_voltage(self):
        return self._get_voltage(3)
    def do_set_port4_voltage(self, voltage):
        self._set_voltage(4, voltage)
    def do_get_port4_voltage(self):
        return self._get_voltage(4)
    def do_set_port5_voltage(self, voltage):
        self._set_voltage(5, voltage)
    def do_get_port5_voltage(self):
        return self._get_voltage(5)
    def do_set_port6_voltage(self, voltage):
        self._set_voltage(6, voltage)
    def do_get_port6_voltage(self):
        return self._get_voltage(6)
    def do_set_port7_voltage(self, voltage):
        self._set_voltage(7, voltage)
    def do_get_port7_voltage(self):
        return self._get_voltage(7)
    def do_set_port8_voltage(self, voltage):
        self._set_voltage(8, voltage)
    def do_get_port8_voltage(self):
        return self._get_voltage(8)


    def do_set_port1_on(self, val):
        self._set_on(1, val)
    def do_get_port1_on(self):
        return self._get_on(1)
    def do_set_port2_on(self, val):
        self._set_on(2, val)
    def do_get_port2_on(self):
        return self._get_on(2)
    def do_set_port3_on(self, val):
        self._set_on(3, val)
    def do_get_port3_on(self):
        return self._get_on(3)
    def do_set_port4_on(self, val):
        self._set_on(4, val)
    def do_get_port4_on(self):
        return self._get_on(4)
    def do_set_port5_on(self, val):
        self._set_on(5, val)
    def do_get_port5_on(self):
        return self._get_on(5)
    def do_set_port6_on(self, val):
        self._set_on(6, val)
    def do_get_port6_on(self):
        return self._get_on(6)
    def do_set_port7_on(self, val):
        self._set_on(7, val)
    def do_get_port7_on(self):
        return self._get_on(7)
    def do_set_port8_on(self, val):
        self._set_on(8, val)
    def do_get_port8_on(self):
        return self._get_on(8)
