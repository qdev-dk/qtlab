# CryogenicLtd_SMS.py class, to perform the communication between the Wrapper and the device
# Nina Rasmussen <nina.g.rasmussen@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distribouted in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from instrument import Instrument
from time import time, sleep
import visa
import types
import logging
import re

class CryogenicLtd_SMS(Instrument):
    '''
    This is the python driver for the Cryogenic Limited SMS Magnet Power Supply

    Usage:
    Initialize with
    <name> = instruments.create('name', 'OxfordInstruments_IPS120', address='<Instrument address>')
    <Instrument address> = COM1

    Note: Since the ISOBUS allows for several instruments to be managed in parallel, the command
    which is sent to the device starts with '@n', where n is the ISOBUS instrument number.


    CAUTION: EXCEPTION AND PROPER FEEDBACK TO ERRORNOUS IMPORT SHOULD BE IMPLEMENTED!
    '''
#TODO: auto update script
#TODO: get doesn't always update the wrapper! (e.g. when input is an int and output is a string)

    def __init__(self, name, address):
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
        self._visainstrument = visa.SerialInstrument(self._address)

        #Add parameters
        self.add_parameter('field',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='T',
            tags=['measure']
            )
        self.add_parameter('voltage',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='V',
            tags=['measure']
            )
        self.add_parameter('ramp_rate',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            units='A/SEC',
            tags=['measure']
            )
        self.add_parameter('mid_setpoint',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            units='T',
            tags=['measure']
            )
        self.add_parameter('max_setpoint',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            units='T',
            tags=['measure']
            )
     
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
        self.get_field()

    def do_get_field(self):
        '''
        Read the current magnetic field.
        Output:
            field (float)
        '''
        # Send a command to the instrument
        val = self._visainstrument.ask('G O')
        pattern = r"[-+]?\d*\.\d+|\d+"
        field = float(re.findall(pattern, val)[3])
        return field

    def do_get_voltage(self):
        '''
        Read the current voltage.
        Output:
            voltage (float)
        '''
        # Send a command to the instrument
        val = self._visainstrument.ask('G O')
        pattern = r"[-+]?\d*\.\d+|\d+"
        voltage = float(re.findall(pattern, val)[4])
        return voltage

    def do_get_ramp_rate(self):
        '''
        Read the current rate.
        Output:
            rate (float)
        '''
        # Send a command to the instrument
        val = self._visainstrument.ask('G R')
        pattern = r"[-+]?\d*\.\d+|\d+"
        print val
        print re.findall(pattern, val)
        ramp_rate = float(re.findall(pattern, val)[3])
        return ramp_rate

    def do_set_ramp_rate(self,rate):
        '''
        Sets the ramp rate.
        Output:
            rate (float)
        '''
        max = 0.0113 
        if rate > max:
            rate = max 
            print 'Rate exceeds tolerance. Rate set to %1.5f' %max
        elif rate < 0:
            rate = 0.00001
            print "Rate setpoint below zero. Rate set to 0.00001"
        # Send a command to the instrument
        string = 'SET RAMP %1.6f' %rate
        out=self._visainstrument.ask(string)
        return out

    def do_get_mid_setpoint(self):
        '''
        Read the current mid set point.
        Output:
            mid set point (float)
        '''
        # Send a command to the instrument
        val = self._visainstrument.ask('GET MID')
        pattern = r"[-+]?\d*\.\d+|\d+"
        mid_setpoint = float(re.findall(pattern, val)[3])
        return mid_setpoint

    def do_set_mid_setpoint(self,setpoint):
        '''
        Sets the MID set point.
        Output:
            Mid_setpoint (float)
        '''
        ##Nifty if that takes the unit into account could be made here
        max = 0.1
        if setpoint > max:
            setpoint = max 
            print 'Rate exceeds tolerance. Rate set to %1.5f' %max
           
        # Send a command to the instrument
        string = 'SET MID %1.6f' %setpoint
        print string
        out=self._visainstrument.ask(string)
        print out
        return string

    def do_get_max_setpoint(self):
        '''
        Read the current mid set point.
        Output:
            mid set point (float)
        '''
        # Send a command to the instrument
        val = self._visainstrument.ask('GET MAX')
        pattern = r"[-+]?\d*\.\d+|\d+"
        max_setpoint = float(re.findall(pattern, val)[3])
        return max_setpoint

    def do_set_max_setpoint(self,setpoint):
        '''
        Sets the MID set point.
        Output:
            Max_setpoint (float)
        '''
        ##Nifty if that takes the unit into account could be made here
        max = 0.1
        if setpoint > max:
            setpoint = max 
            print 'Rate exceeds tolerance. Rate set to %1.5f' %max
           
        # Send a command to the instrument
        string = 'SET MAX %1.6f' %setpoint
        print string
        out=self._visainstrument.ask(string)
        print out
        return out


    def ramp_to(self,string):
        '''
        Sets the MID set point.
        Output:
            status (float)
        '''
        #Exceptions needed!
        string=string.upper()

        if string!='ZERO' and string!='MID' and string!='MAX':
            out = False
            return out
        string = 'RAMP ' + string
        print string
        self._visainstrument.write(string)
        self._visainstrument.ask('RAMP STATUS')
        #self.empty_buffer()
        out = True
        return out

    def ramp_status(self):
        out = self._visainstrument.ask('RAMP STATUS')
        if out.rsplit(None, 1)[-1] =='TESLA':
            return 'DONE'
        elif out.rsplit(None, 1)[-1] =='A/SEC':
            return 'RAMPING'
        return False

    def empty_buffer(self):
        junk = self._visainstrument.read()
        print junk