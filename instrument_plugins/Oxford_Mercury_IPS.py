# Oxford_Mercury_IPS.py class, to perform the communication between the Wrapper and the device
# Guenevere Prawiroatmodjo <guen@vvtp.tudelft.nl>, 2009
# Pieter de Groot <pieterdegroot@gmail.com>, 2009
# Joonas Govenius <joonas.govenius@aalto.fi>, 2012
# Russell Lake <russell.lake@aalto.fi>, 2012
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
from time import time, sleep
from lib import tcpinstrument
import types
import logging
import re

class Oxford_Mercury_IPS(Instrument):
    '''
    This is the python driver for the Oxford Instruments IPS 120 Magnet Power Supply

    Usage:
    Initialize with
    <name> = instruments.create('name', 'Oxford_Mercury_IPS', address='<Instrument address>')
    <Instrument address> = ASRL1::INSTR

    Note: Since the ISOBUS allows for several instruments to be managed in parallel, the command
    which is sent to the device starts with '@n', where n is the ISOBUS instrument number.

    '''
#TODO: auto update script
#TODO: get doesn't always update the wrapper! (e.g. when input is an int and output is a string)

    def __init__(self, name, address, number=2):
        '''
        Initializes the Oxford Instruments IPS 120 Magnet Power Supply.

        Input:
            name (string)    : name of the instrument
            address (string) : instrument address
            number (int)     : ISOBUS instrument number

        Output:
            None
        '''
        logging.debug(__name__ + ' : Initializing instrument')
        Instrument.__init__(self, name, tags=['physical'])


        self._address = address
        self._number = number
        #self._visainstrument = visa.SerialInstrument(self._address)
        self._visainstrument = tcpinstrument.TCPInstrument(address, tcp_inactive_period = 30., tcp_min_time_between_connections = 0.5)
        self._values = {}
        #self._visainstrument.stop_bits = 2

        #Add parameters
        self.add_parameter('activity', type=types.StringType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            format_map = {
            "HOLD" : "Hold",
            "RTOS" : "To set point",
            "RTOZ" : "To zero",
            "CLMP" : "Clamped"})

        self.add_parameter('current_setpoint', type=types.FloatType, units='A',
             flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
             minval=-126., maxval=126.)
        
        self.add_parameter('current', type=types.FloatType, units='A',
             flags=Instrument.FLAG_GET)

        self.add_parameter('voltage', type=types.FloatType, units='V',
             flags=Instrument.FLAG_GET)

        # self.add_parameter('ramp_rate', type=types.FloatType, units='A/min',
        #      flags=Instrument.FLAG_GET)

        self.add_parameter('ramp_rate_setpoint', type=types.FloatType, units='A/min',
             flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
             minval=0., maxval=1200.)



        # self.add_parameter('sweeprate_current', type=types.FloatType,
            # flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            # minval=0, maxval=240)
        # self.add_parameter('system_status', type=types.IntType,
            # flags=Instrument.FLAG_GET,
            # format_map = {
            # 0 : "Normal",
            # 1 : "Quenched",
            # 2 : "Over Heated",
            # 4 : "Warming Up",
            # 8 : "Fault"})
        # self.add_parameter('system_status2', type=types.IntType,
            # flags=Instrument.FLAG_GET,
            # format_map = {
            # 0 : "Normal",
            # 1 : "On positive voltage limit",
            # 2 : "On negative voltage limit",
            # 4 : "Outside negative current limit",
            # 8 : "Outside positive current limit"
            # })
        #self.add_parameter('current', type=types.FloatType,
        #    flags=Instrument.FLAG_GET)
        #self.add_parameter('voltage', type=types.FloatType,
        #    flags=Instrument.FLAG_GET)

        # Add functions
        self.add_function('get_all')
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
        #self.get_current()
        self.get_voltage()
        #self.get_magnet_current()
        self.get_current_setpoint()
        self.get_current()
        #self.get_sweeprate_current()
        self.get_activity()
        self.get_ramp_rate_setpoint()
#        self.get_ramp_rate()


    # Functions
    def _execute(self, message):
        '''
        Write a command to the device

        Input:
            message (str) : write command for the device

        Output:
            None
        '''
        logging.debug(__name__ + ' : Send the following command to the device: %s' % message)
        result = self._visainstrument.ask('%s\n' % (message), end_of_message='\n')
        if result.find('?') >= 0:
            print "Error: Command %s not recognized" % message
        else:
            return result

    def identify(self):
        '''
        Identify the device

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : Identify the device')
        return self._execute('*IDN?')

    def examine(self):
        '''
        Examine the status of the device

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : Examine status')

        #print 'Mode: '
        #print self.get_mode()

    # def do_get_current(self):
        # '''
        # Demand output current of device

        # Input:
            # None

        # Output:
            # result (float) : output current in Amp
        # '''
        # logging.info(__name__ + ' : Read output current')
        # result = self._execute('R0')
        # return float(result.replace('R',''))

    def do_get_current_setpoint(self):
        '''
        Return the set point (target current)

        Input:
            None

        Output:
            result (float) : Target current in Amp
        '''
        result = self._execute('READ:DEV:GRPZ:PSU:SIG:CSET')
        logging.debug(__name__ + ' : Read set point (target current): %s')

        m = re.match(r'STAT:DEV:GRPZ:PSU:SIG:CSET:(.+?)A', result)
        if m == None or len(m.groups()) != 1: raise Exception('Could not parse the reply: %s' % result)

        try:        
          return float(m.groups()[0])
        except Exception as e:
          raise e

    def do_set_current_setpoint(self, current):
        '''
        Set current setpoint (target current)
        Input:
            current (float) : target current in Amp

        Output:
            None
        '''
        logging.debug(__name__ + ' : Setting target current to %s' % current)
        cmd = 'SET:DEV:GRPZ:PSU:SIG:CSET:%s' % current
        result = self._execute(cmd)
        
        # verify that the command was correctly parsed
        m = re.match(r'STAT:SET:DEV:GRPZ:PSU:SIG:CSET:(.+?):VALID', result)
        if m == None or len(m.groups()) != 1: raise Exception('The IPS did not acknowledge parsing %s correctly, instead got: %s' % (cmd, result))


    def do_get_current(self):
        '''
        Return the current.

        Input:
            None

        Output:
            result (float) : Current in amp.
        '''
        result = self._execute('READ:DEV:GRPZ:PSU:SIG:CURR')
        logging.debug(__name__ + ' : Read current: %s')

        m = re.match(r'STAT:DEV:GRPZ:PSU:SIG:CURR:(.+?)A', result)
        if m == None or len(m.groups()) != 1: raise Exception('Could not parse the reply: %s' % result)

        try:        
          return float(m.groups()[0])
        except Exception as e:
          raise e



    def do_get_activity(self):
        '''
        Return the action status  (activity).

        Input:
            None

        Output:
            result (float) : action status.
        '''
        result = self._execute('READ:DEV:GRPZ:PSU:ACTN')
        logging.debug(__name__ + ' : Read activity: %s' % result)

        m = re.match(r'STAT:DEV:GRPZ:PSU:ACTN:(.+?)$', result)
        if m == None or len(m.groups()) != 1: raise Exception('Could not parse the reply: %s' % result)

        try:
          logging.debug("parsed '%s'" % (m.groups()[0]))

          return m.groups()[0]
        except Exception as e:
          raise e


    def do_set_activity(self, activity):
        '''
        Set action status:[HOLD | RTOS | RTOZ | CLMP]
        Input:
            status: [HOLD | RTOS | RTOZ | CLMP]

        Output:
            None
        '''
        logging.debug(__name__ + ' : Setting activity to %s' % activity)
        cmd = 'SET:DEV:GRPZ:PSU:ACTN:%s' % activity
        result = self._execute(cmd)
        
        # verify that the command was correctly parsed
        m = re.match(r'STAT:SET:DEV:GRPZ:PSU:ACTN:(.+?):VALID', result)
        if m == None or len(m.groups()) != 1: raise Exception('The IPS did not acknowledge parsing %s correctly, instead got: %s' % (cmd, result))














    # def do_get_ramp_rate(self):
    #     '''
    #     Most recent current rate reading

    #     Input:
    #         None

    #     Output:
    #         result (float) : Current ramp rate in A/min
    #     '''
    #     result = self._execute('READ:DEV:GRPZ:PSU:SIG:RCUR')
    #     logging.debug(__name__ + ' : Read current: %s')

    #     m = re.match(r'STAT:DEV:GRPZ:PSU:SIG:RCUR:(.+?)', result)
    #     if m == None or len(m.groups()) != 1: raise Exception('Could not parse the reply: %s' % result)

    #     try:        
    #       return float(m.groups()[0])
    #     except Exception as e:
    #       raise e



    def do_set_ramp_rate_setpoint(self, ramp_rate):
        '''
        current rate to set (A/min)

        Output:
            None
        '''
        logging.debug(__name__ + ' : Setting current rate  current to %s' % ramp_rate)
        cmd = 'SET:DEV:GRPZ:PSU:SIG:RCST:%s' % ramp_rate
        result = self._execute(cmd)
        
        # verify that the command was correctly parsed
        m = re.match(r'STAT:SET:DEV:GRPZ:PSU:SIG:RCST:(.+?):VALID', result)
        if m == None or len(m.groups()) != 1: raise Exception('The IPS did not acknowledge parsing %s correctly, instead got: %s' % (cmd, result))

    def do_get_ramp_rate_setpoint(self):
        '''
        Return the current rate set point

        Input:
            None

        Output:
            result (float) : current rate in A / min
        '''
        result = self._execute('READ:DEV:GRPZ:PSU:SIG:RCST')
        logging.debug(__name__ + ' : Read current rate set point: %s')

        m = re.match(r'STAT:DEV:GRPZ:PSU:SIG:RCST:(.+?)A/m', result)
        if m == None or len(m.groups()) != 1: raise Exception('Could not parse the reply: %s' % result)

        try:        
          return float(m.groups()[0])
        except Exception as e:
          raise e


    def do_get_voltage(self):
        '''
        Return the voltage.

        Input:
            None

        Output:
            result (float) : Voltage in volts.
        '''
        result = self._execute('READ:DEV:GRPZ:PSU:SIG:VOLT')
        logging.debug(__name__ + ' : Read voltage: %s')

        m = re.match(r'STAT:DEV:GRPZ:PSU:SIG:VOLT:(.+?)V', result)
        if m == None or len(m.groups()) != 1: raise Exception('Could not parse the reply: %s' % result)

        try:        
          return float(m.groups()[0])
        except Exception as e:
          raise e




    # def do_get_sweeprate_current(self):
        # '''
        # Return sweep rate (current)

        # Input:
            # None

        # Output:
            # result (float) : sweep rate in Amp/min
        # '''
        # logging.debug(__name__ + ' : Read sweep rate (current)')
        # result = self._execute('R6')
        # return float(result.replace('R',''))

    # def do_set_sweeprate_current(self, sweeprate):
        # '''
        # Set sweep rate (current)

        # Input:
            # sweeprate(float) : Sweep rate in Amps/min.

        # Output:
            # None
        # '''
        # logging.debug(__name__ + ' : Set sweep rate (current) to %s Amps/min' % sweeprate)
        # self._execute('S%s' % sweeprate)
        # self.get_sweeprate_field() # Update sweeprate_field

    # def do_get_activity(self):
        # '''
        # Get the activity of the magnet. Possibilities: Hold, Set point, Zero or Clamp.
        # Input:
            # None

        # Output:
            # result(str) : "Hold", "Set point", "Zero" or "Clamp".
        # '''
        # result = self._execute('X')
        # logging.debug(__name__ + ' : Get activity of the magnet.')
        # return int(result[4])

    # def do_set_activity(self, mode):
        # '''
        # Set the activity to Hold, To Set point or To Zero.

        # Input:
            # mode (int) :
            # 0 : "Hold",
            # 1 : "To set point",
            # 2 : "To zero"

            # 4 : "Clamped" (not included)

        # Output:
            # None
        # '''
        # status = {
        # 0 : "Hold",
        # 1 : "To set point",
        # 2 : "To zero"
        # }
        # if status.__contains__(mode):
            # logging.debug(__name__ + ' : Setting magnet activity to %s' % status.get(mode, "Unknown"))
            # self._execute('A%s' % mode)
        # else:
            # print 'Invalid mode inserted.'

    # def hold(self):
        # '''
        # Set the device activity to "Hold"
        # Input:
            # None
        # Output:
            # None
        # '''
        # self.set_activity(0)
        # self.get_activity()

    # def to_setpoint(self):
        # '''
        # Set the device activity to "To set point". This initiates a sweep.
        # Input:
            # None
        # Output:
            # None
        # '''
        # self.set_activity(1)
        # self.get_activity()

    # def to_zero(self):
        # '''
        # Set the device activity to "To zero". This sweeps te magnet back to zero.
        # Input:
            # None
        # Output:
            # None
        # '''
        # self.set_activity(2)
        # self.get_activity()

    # def get_changed(self):
        # print "Current: "
        # print self.get_current()
        # print "Field: "
        # print self.get_field()
        # print "Magnet current: "
        # print self.get_magnet_current()
        # print "Heater current: "
        # print self.get_heater_current()
        # print "Mode: "
        # print self.get_mode()
