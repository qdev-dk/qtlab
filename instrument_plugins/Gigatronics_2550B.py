# Gigatronics_2550B.py class, to perform the communication between the Wrapper and the device
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
#import visa
import types
import logging
import numpy
import re
import socket
import math
import time
import threading
import struct


class Gigatronics_2550B(Instrument):
    '''
    This is the driver for the Gigatronics 2550B Signal Genarator

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'Gigatronics_2550B', address='<GBIP address>, reset=<bool>')
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the Gigatronics_2550B, and communicates with the wrapper.

        Input:
          name (string)    : name of the instrument
          address (string) : GPIB address
          reset (bool)     : resets to default values, default=False
        '''
        logging.info(__name__ + ' : Initializing instrument Gigatronics_2550B')
        Instrument.__init__(self, name, tags=['physical'])
        
        
        self.__cached_freq = -1.
        self.__cached_freq_timestamp = 0.
        
        self.__tcp_lock = threading.Semaphore()
        self.__tcp_connected = False
        self.__tcp_last_used = 0.
        self.__tcp_close_thread = threading.Thread(target=self.__close_inactive_connection, name="gigatronics_auto_close") 
        self.__tcp_close_thread.daemon = True  # a daemon thread doesn't prevent program from exiting
        self.__tcp_close_thread.start()
        
        self._address = address
        self._tcpdst = re.match(r"^(\d+\.\d+\.\d+\.\d+):(\d+)", address).groups() # parse into IP & port
        if len(self._tcpdst) != 2: raise Exception("Could not parse {0} into an IPv4 address and a port. Should be in format 192.168.1.1:2550.".format(address))

        #self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self._socket.settimeout(3.) # timeout in seconds
        #self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #self._socket.bind(('0.0.0.0', 12550)) # always use the same LOCAL port because the device doesn't accept a new connection from a different port if the previous one wasn't properly closed
        #self._socket.connect((self._tcpdst[0], int(self._tcpdst[1])))

        self.add_parameter('power',
            flags=Instrument.FLAG_GETSET, units='dBm', minval=-135, maxval=16, type=types.FloatType)
        self.add_parameter('phase',
            flags=Instrument.FLAG_GETSET, units='rad', minval=-numpy.pi, maxval=numpy.pi, type=types.FloatType)
        self.add_parameter('frequency',
            flags=Instrument.FLAG_GETSET, units='Hz', minval=1e5, maxval=50e9, type=types.FloatType)
        self.add_parameter('status',
            flags=Instrument.FLAG_GETSET, type=types.StringType)

        self.add_function('reset')
        self.add_function ('get_all')

        if (reset):
            self.reset()
        else:
            self.get_all()

    def __ask(self, querystr):
        self.__tcp_lock.acquire()

        try:
            self.__connect()
            self._socket.sendall(querystr)

            reply = ''
            while '\n' not in reply:
                reply = reply + self._socket.recv(512)

        except Exception:
            self.__tcp_lock.release()
            raise

        self.__tcp_last_used = time.time()
        self.__tcp_lock.release()

        return reply

    def __tell(self, cmd):
        self.__tcp_lock.acquire()

        try:
            self.__connect()
            logging.debug(__name__ + ' : telling instrument to: ' + cmd)
            self._socket.sendall(cmd)
        except Exception:
            self.__tcp_lock.release()
            raise

        self.__tcp_last_used = time.time()
        self.__tcp_lock.release()

        return

    def __connect(self):
        if not (self.__tcp_connected):
            logging.debug(__name__ + ' : opening TCP socket')
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # this should cause RST to be sent when socket.close() is called
            l_onoff = 1
            l_linger = 1
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', l_onoff, l_linger))

            # always use the same LOCAL port because the device doesn't accept a new connection from a different port if the previous one wasn't properly closed
            #self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            #self._socket.bind(('0.0.0.0', 12550))
            
            self._socket.settimeout(3.) # timeout in seconds
            self._socket.connect((self._tcpdst[0], int(self._tcpdst[1])))
            self.__tcp_connected = True
    
    def __close_inactive_connection(self):
        while True:
            t0 = time.time()
            time.sleep(2.)
            t1 = time.time()
            self.__tcp_lock.acquire()
            t2 = time.time()
            #logging.debug(__name__ + ' : tcp_connected == ' + str(self.__tcp_connected))
            if (self.__tcp_connected) and ((time.time() - self.__tcp_last_used) > 3.0):
                self.close_connection_gracefully()
            t3 = time.time()
            self.__tcp_lock.release()
            t4 = time.time()
            logging.debug(__name__ + ' : dt1 = {0:0.3f}, dt2 = {0:0.3f}, dt3 = {0:0.3f}, dt4 = {0:0.3f}'.format(t1-t0, t2-t1, t3-t2, t4-t3))

    def reset(self):
        '''
        Resets the instrument to default values

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : resetting instrument')
        self.__tell('*RST')
        self.get_all()
        
    def close_connection_gracefully(self):
        '''
        Closes the TCP connection gracefully

        Input:
            None

        Output:
            None
        '''
        if self.__tcp_connected:
            logging.debug(__name__ + ' : closing TCP socket')
            try:
                self._socket.shutdown(socket.SHUT_WR)
                self._socket.settimeout(1.) # timeout in seconds
                self._socket.recv(512)
            except Exception:
                logging.debug(__name__ + ' : failed to gracefully shutdown TCP socket.')
            #time.sleep(0.5)
            self._socket.close()
            self.__tcp_connected = False

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
        self.get_power()
        self.get_phase()
        self.get_frequency()
        self.get_status()

    def do_get_power(self):
        '''
        Reads the power of the signal from the instrument

        Input:
            None

        Output:
            ampl (?) : power in ?
        '''
        logging.debug(__name__ + ' : get power')
        return float(self.__ask('POW:AMPL?'))

    def do_set_power(self, amp):
        '''
        Set the power of the signal

        Input:
            amp (float) : power in ??

        Output:
            None
        '''
        logging.debug(__name__ + ' : set power to %f' % amp)
        self.__tell('POW:AMPL %s' % amp)

    def do_get_phase(self):
        '''
        Reads the phase of the signal from the instrument

        Input:
            None

        Output:
            phase (float) : Phase in radians
        '''
        logging.debug(__name__ + ' : get phase')

        rep = self.__ask('PHASE?')
        m = re.match(r"^([\d\.]+) (RAD|DEG)", rep)
        if m == None or len(m.groups()) != 2: raise Exception('Failed to parse {0} in reply to PHASE?.'.format())

        phase = float(m.groups()[0])
        if m.groups()[1] == 'DEG': phase = phase * math.pi/180.
        return phase

    def do_set_phase(self, phase):
        '''
        Set the phase of the signal

        Input:
            phase (float) : Phase in radians

        Output:
            None
        '''
        logging.debug(__name__ + ' : set phase to %f' % phase)
        self.__tell('PHASE %s RAD' % phase)

    def do_get_frequency(self):
        '''
        Reads the frequency of the signal from the instrument

        Input:
            None

        Output:
            freq (float) : Frequency in Hz
        '''
        t = time.time()
        if t - self.__cached_freq_timestamp < 1. :  # return cached freq if it's < 1 second old
            logging.debug(__name__ + ' : returning cached frequency ' + str(self.__cached_freq))
            return self.__cached_freq

        logging.debug(__name__ + ' : get frequency')
        f = float(self.__ask('FREQ:CW?'))
        self.__cached_freq = f
        self.__cached_freq_timestamp = t
        return f

    def do_set_frequency(self, freq):
        '''
        Set the frequency of the instrument

        Input:
            freq (float) : Frequency in Hz

        Output:
            None
        '''
        
        f0 = self.do_get_frequency()
        
        logging.debug(__name__ + ' : set frequency to %f' % freq)
        self.__tell('FREQ:CW %s' % freq)

        self.__cached_freq = freq
        self.__cached_freq_timestamp = time.time()

        #if freq <= 2e9: time.sleep(.5) # sleep 500ms so that power stabilizes

        # the output power drops for a short time when changing
        # frequency past certain boundaries
        boundaries = [0.71e9, 0.18e9, 0.36e9, 0.675e9, 0.88e9, 1.01e9, 1.42e9, 2e9, 3.2e9, 4e9, 5.1e9, 8e9, 10.1e9, 12.7e9, 16.01e9, 20.2e9, 25.4e9, 28.2e9, 28.57e9, 30.09e9, 32.02e9, 39.6e9, 47.99e9]
        if any([ (f0 - b)*(freq - b) <= 0. for b in boundaries ]): time.sleep(.2) # sleep 200ms so that power stabilizes
        
    def do_get_status(self):
        '''
        Reads the output status from the instrument

        Input:
            None

        Output:
            status (string) : 'On' or 'Off'
        '''
        logging.debug(__name__ + ' : get status')
        stat = self.__ask('OUTP?').replace("\r", '').replace("\n", '')

        if (stat=='1'):
          return 'on'
        elif (stat=='0'):
          return 'off'
        else:
          raise ValueError('Output status not specified : "%s"' % stat)
        return

    def do_set_status(self, status):
        '''
        Set the output status of the instrument

        Input:
            status (string) : 'On' or 'Off'

        Output:
            None
        '''
        logging.debug(__name__ + ' : set status to %s' % status)
        if status.upper() in ('ON', 'OFF'):
            status = status.upper()
        else:
            raise ValueError('set_status(): can only set on or off')
        self.__tell('OUTP %s' % status)

    # shortcuts
    def off(self):
        '''
        Set status to 'off'

        Input:
            None

        Output:
            None
        '''
        self.set_status('off')

    def on(self):
        '''
        Set status to 'on'

        Input:
            None

        Output:
            None
        '''
        self.set_status('on')

