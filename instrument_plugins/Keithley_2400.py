# Keithley_2400.py driver for Keithley 2400 Source Meter
# Arjan Verduijn <a.verduijn@unsw.edu.au>
# Gabriele de Boo <g.deboo@student.unsw.edu.au>
#
# Merlin von Soosten <merlin@nbi.dk> changed to pyvisa==1.6 driver
#       (http://pyvisa.readthedocs.org/en/1.6/migrating.html)
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
import qt

class Keithley_2400(Instrument):
    '''
    This is the driver for the Keithley 2400 Source Meter

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'Keithley_2400',
        address='<GBIP address>',
        reset=<bool>)
    '''

    def __init__(self, name, address, reset=True):
        '''
        Initializes the Keithley_2400, and communicates with the wrapper.

        Input:
            name (string)           : name of the instrument
            address (string)        : GPIB address
            reset (bool)            : resets to default values
        Output:
            None
        '''
        # Initialize wrapper functions
        logging.info('Initializing instrument Keithley_2400')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants and set up visa instrument
        self._address = address
        self._visarm = visa.ResourceManager()
        self._visainstrument = self._visarm.open_resource(self._address)
        self._visainstrument.clear()

        self.add_parameter('source_voltage',
            type=types.FloatType,
            tags=['sweep'],
            maxstep=0.100, stepdelay=100,
            flags=Instrument.FLAG_GETSET, minval=-210, maxval=210, units='V')
        self.add_parameter('source_voltage_range',
            type=types.FloatType,
            flags=Instrument.FLAG_GETSET, minval=-210, maxval=210, units='V')
#        self.add_parameter('source_current',
#            type=types.FloatType,
#            tags=['sweep'],
#            maxstep=1e-6, stepdelay=100,
#            flags=Instrument.FLAG_GETSET, minval=-105e-6, maxval=105e-6, units='A')
        self.add_parameter('current_compliance',
            type=types.FloatType,
            flags=Instrument.FLAG_GETSET, minval=-1.05, maxval=1.05, units='A')
        self.add_parameter('voltage_compliance',
            type=types.FloatType,
            flags=Instrument.FLAG_GETSET, minval=-210, maxval=210, units='V')
        self.add_parameter('output_state',
            type=types.BooleanType,
            flags=Instrument.FLAG_GETSET)
        self.add_parameter('terminals',
            type=types.StringType,
            flags=Instrument.FLAG_GETSET,
            option_list=(
                'FRONT',
                'REAR'))
        self.add_parameter('source_function',
            type=types.StringType,
            flags=Instrument.FLAG_GETSET,
            option_list=(
                'voltage',
                'current',
                'memory'))
        self.add_parameter('voltage_source_mode',
            type=types.StringType,
            flags=Instrument.FLAG_GETSET,
            option_list=(
                'fixed',
                'list',
                'sweep'))
        self.add_parameter('current_source_mode',
            type=types.StringType,
            flags=Instrument.FLAG_GETSET,
            option_list=(
                'fixed',
                'list',
                'sweep'))
        self.add_parameter('current_reading',
            type=types.FloatType,
            units='A',
            flags=Instrument.FLAG_GET)

        self.add_function('beep')

        if reset:
            if (self.get_output_state()):
                print 'Performing instrument reset, ramping voltage to zero...'
                self.get_source_voltage()
                self.set_source_voltage(0)
                self.reset()
            else:
                self.reset()

        self.get_all()

# --------------------------------------
#           functions
# --------------------------------------

    def _query(self, query, **kwargs):
        '''
        Simplifies Queries and strips trailing spaces/newline characters, since
        they are not remove in pyvisa >= 1.6
        '''
        return self._visainstrument.query(query, **kwargs).rstrip()

    def _write(self, write, **kwargs):
        return self._visainstrument.write(write, **kwargs)

    def get_all(self):
        self.get_source_voltage()
        self.get_source_voltage_range()
        self.get_current_compliance()
        self.get_voltage_compliance()
        self.get_output_state()
        self.get_terminals()
        self.get_source_function()
        self.get_voltage_source_mode()
        self.get_current_source_mode()


    def reset(self):
        '''
        Resets instrument to default setting for GPIB operation, i.e. manual trigger mode

        Input:
            None

        Output:
            None
        '''
        logging.debug('Resetting instrument to default GPIB operation')
        self._write('*RST')

    def do_get_terminals(self):
        '''
        Get terminals that are used.

        Input:
            None
        Output:
            'FRONT'
            'REAR'
        '''
        logging.debug('Getting the terminal used by %s.' %self.get_name())
        reply = self._query(':ROUT:TERM?')
        if reply == 'FRON': # The source meter responds with 'FRON'
            logging.info('The terminal used by %s is FRONT.' %(self.get_name()))
            return 'FRONT'
        elif reply == 'REAR':
            logging.info('The terminal used by %s is %s.' %(self.get_name(),reply))
            return reply
        else:
            logging.warning('Received unexpected response from %s.' %self.get_name())
            raise Warning('Instrument %s responded with an unexpected response: %s.' %(self.get_name(),reply))

    def do_set_terminals(self, terminal):
        '''
        Set terminals to be used

        Input:
            'FRONT'
            'REAR'
        Output:
            None
        '''
        logging.debug('Setting the terminal used by %s.' %self.get_name())
        logging.info('Setting the terminal used by %s to %s.' %(self.get_name(), terminal))
        self._write(':ROUT:TERM %s' %terminal)

    def do_get_source_function(self):
        '''
        Get source function

        Input:
            None
        Output:
            'voltage'
            'current'
            'memory'
        '''
        logging.debug('Getting source function mode.')
        reply = self._query(':SOUR:FUNC:MODE?').rstrip()
        if reply == 'VOLT':
            logging.info('Source function of %s is voltage.' % self.get_name())
            return 'voltage'
        elif reply == 'CURR':
            logging.info('Source function of %s is current.' % self.get_name())
            return 'current'
        elif reply == 'MEM':
            logging.info('Source function of %s is memory.' % self.get_name())
            return 'memory'
        else:
            logging.warning('get_source_function: Received unexpected response from %s.' %self.get_name())
            raise Warning('Instrument %s responded with an unexpected response: %s.' %(self.get_name(),reply))

    def do_set_source_function(self, function):
        '''
        Set source function

        Input:
            'voltage'
            'current'
            'memory'
        Output:
            None
        '''
        logging.debug('Setting source function mode to %s.' %function)
        self._write(':SOUR:FUNC:MODE %s' %function)

    def do_get_voltage_source_mode(self):
        '''
        Get voltage sourcing mode

        Input:
            None
        Output:
            'fixed'
            'list'
            'sweep'
        '''
        logging.debug('Getting voltage sourcing mode.')
        reply = self._query('SOUR:VOLT:MODE?').rstrip()
        if reply == 'FIX':
            logging.info('Voltage sourcing mode of %s is fixed.' % self.get_name())
            return 'fixed'
        elif reply == 'LIST':
            logging.info('Voltage sourcing mode of %s is list.' % self.get_name())
            return 'list'
        elif reply == 'SWE':
            logging.info('Voltage sourcing mode of %s is sweep.' % self.get_name())
            return 'sweep'
        else:
            logging.warning('get_source_function: Received unexpected response from %s.' %self.get_name())
            raise Warning('Instrument %s responded with an unexpected response: %s.' %(self.get_name(),reply))

    def do_set_voltage_source_mode(self, mode):
        '''
        Set voltage sourcing mode

        Input:
            'fixed'
            'list'
            'sweep'
        Output:
            None
        '''
        logging.debug('Setting voltage sourcing mdoe to %s.' %mode)
        self._write(':SOUR:VOLT:MODE %s' %mode)

    def do_get_current_source_mode(self):
        '''
        Get current sourcing mode

        Input:
            None
        Output:
            'fixed'
            'list'
            'sweep'
        '''
        logging.debug('Getting current sourcing mode.')
        reply = self._query('SOUR:CURR:MODE?').rstrip()
        if reply == 'FIX':
            logging.info('Current sourcing mode of %s is fixed.' % self.get_name())
            return 'fixed'
        elif reply == 'LIST':
            logging.info('Current sourcing mode of %s is list.' % self.get_name())
            return 'list'
        elif reply == 'SWE':
            logging.info('Current sourcing mode of %s is sweep.' % self.get_name())
            return 'sweep'
        else:
            logging.warning('get_source_function: Received unexpected response from %s.' %self.get_name())
            raise Warning('Instrument %s responded with an unexpected response: %s.' %(self.get_name(),reply))

    def do_set_current_source_mode(self, mode):
        '''
        Set current sourcing mode

        Input:
            'fixed'
            'list'
            'sweep'
        Output:
            None
        '''
        logging.debug('Setting current sourcing mdoe to %s.' %mode)
        self._write(':SOUR:CURR:MODE %s' %mode)

    def set_measure_range(self, function, range):
        '''
        Set measurement range in volts or amps

        Input:
            1     : voltage mode
            2     : current mode
            range : range in volts or amps
        Output:
            None
        '''
        flib = {
            1: 'VOLT',
            2: 'CURR'}
        logging.debug('Select measurement range: ' + str(range) + flib[function])
        self._write(':SOUR:' + flib[function] +':RANG ' + str(range))

    def set_source_amplitude(self, function, amplitude):
        '''
        Set source amplitude in volts or amps

        Input:
            1           : voltage mode
            2           : current mode
            amplitude   : range in volts or amps
        Output:
            None
        '''
        flib = {
            1: 'VOLT',
            2: 'CURR'}
        logging.debug('Set source amplitude to ' + str(amplitude))
        self._write(':SOUR:' + flib[function] + ':LEV ' + str(amplitude))

    def set_measure_function(self, function):
        '''
        Set measure function

        Input:
            1: voltage function
            2: current function
        Output:
            None
        '''
        flib = {
            1: 'VOLT',
            2: 'CURR'}
        logging.debug('Set measure function to' + flib[function])
        self._write(':SENS:FUNC ' + flib[function])

    def do_set_current_compliance(self, compliance):
        '''
        Set current compliance in amps

        Input:
            compliance : compliance in amps
        Output:
            None
        '''
        logging.debug('Set current compliance to ' + str(compliance))
        self._write(':SENS:CURR:PROT:LEV '+ str(compliance))

    def do_get_current_compliance(self):
        '''
        Get current compliance in amps
        '''
        logging.debug('Get current compliance.')
        return self._query(':SENS:CURR:PROT:LEV?').rstrip()

    def do_set_voltage_compliance(self, compliance):
        '''
        Set voltage compliance in volts

        Input:
            compliance : compliance in volts
        Output:
            None
        '''
        logging.debug('Set voltage compliance to ' + str(compliance))
        self._write(':SENS:VOLT:PROT:LEV ' + str(compliance))

    def do_get_voltage_compliance(self):
        '''
        Get voltage compliance in volts
        '''
        logging.debug('Get voltage compliance.')
        return self._query(':SENS:VOLT:PROT:LEV?').rstrip()

    def do_get_source_voltage(self):
        '''
        Get the voltage for the voltage source mode.
        '''
        logging.debug('Get source voltage.')
        return float(self._query(':SOUR:VOLT:LEV:AMPL?'))

    def do_set_source_voltage(self, V):
        '''
        Set the voltage for the voltage source mode.
        Input:
            Voltage in V
        Output:
            None
        '''
        logging.info("Set source voltage of %s to %f V." %(self.get_name(), V))
        self._write(':SOUR:VOLT:LEV %f' % V)

    def do_get_source_voltage_range(self):
        '''
        Get the voltage range for the voltage source mode.
        '''
        logging.debug('Getting the source voltage range of %s.' % self.get_name())
        return self._query(':SOUR:VOLT:RANG?').rstrip()

    def do_set_source_voltage_range(self, voltage_range):
        '''
        Set the voltage range for the voltage source mode.
        '''
        logging.debug('Setting the source voltage range of %s to %f.' % (self.get_name(), voltage_range))
	if abs(self.get_source_voltage()) > abs(voltage_range):
            logging.warning('Can not change the voltage range because the source voltage is larger than the voltage range.')
            raise Warning('Source voltage is larger than the given voltage range. Change the source voltage first.')
        self._write(':SOUR:VOLT:RANG %f' %voltage_range)
        self.get_source_voltage_range() # Query the range that the source meter chose.

    def do_get_output_state(self):
        '''
        Get output status

        Instrument responds with 1 or 0
        Function returns True or False
        '''
        status = self._query(':OUTP:STAT?').rstrip()
        logging.debug('Get output status: ' + status)
        return bool(int(status))

    def do_set_output_state(self, state):
        '''
        Set output status

        Input:
            On: True
            Off: False
        Output:
            None
        '''
        logging.info('Turn output ' + str(state))
        self._write(':OUTP ' + str(int(state)))

    def get_value(self, value):
        '''
        Measure one or more of the following from the  from buffer

        Input:
            None

        Output:
            voltage or current in volt or amps
        '''
        readmode = {
            1 :	'voltage',
            2 :	'current',
            3 :	'resistance',
            4 :	'timestamp',
            5 :	'statusword'}
        data = self._query(':READ?').split(',')
        logging.debug(__name__ + ' : Read output values from instrument')
        if type(value) == int:
            if data[value-1][-4:] == 'E+37':
                print 'warning: cannot read ' + readmode[value] + ', parameter not available...'
                return 'NA'
            elif value <= 3:
                return float(data[value-1])
            else:
                return int(float(data[value-1]))
        else:
            result = []
            for v in value:
                if data[v-1][-4:] == 'E+37':
                    result.append('NA')
                    print 'warning: cannot read ' + readmode[v] + ', parameter not available...'
                elif v <= 3:
                    result.append(float(data[v-1]))
                else:
                    result.append(int(float(data[v-1])))
            return result

    def do_get_current_reading(self):
        '''
        Get the latest current reading.
        '''
        logging.debug('Getting the current reading of %s.' % self.get_name())
        if self.get_output_state():
            return self._visainstrument.query(':READ?')
        else:
            logging.warning('Trying to read current of %s while the output is off.' % self.get_name())
            return False

    def beep(self, freq=500, length=1):
        '''
        Make a beep with specified frequency and length.
        '''
        logging.debug('Making a beep with %s.' %self.get_name())
        self._write('SYST:BEEP %f, %f' % (freq, length))
