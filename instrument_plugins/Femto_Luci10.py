# Femto_Luci10.py, Femto Amplifier remote interface
# Joonas Govenius <joonas.govenius@aalto.fi>, 2013
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
import ctypes
import numpy as np

class Femto_Luci10(Instrument):
  '''
  Driver for Femto Luci-10 remote interface for amplifiers.

  Usage:
  Initialize with
  <name> = instruments.create('name', 'Femto_Luci10', address='<GPIB address>',
      device_type, reset=<bool>)

  device_type must be one of: ['DLPVA-100-B-D']
  
  Also note that the manual switches must be set to the correct positions
  for remote operation, as specified in the amplifier manual.
  '''

  def __init__(self, name, address, device_type, reset=False, dll_path=r'C:\Program Files (x86)\FEMTO\LUCI-10\Driver\LUCI_10.dll'):
    '''
    Initializes the Femto_Luci10.

    Input:
        name (string)    : name of the instrument
        address (int)    : interface ID (between 0 and 255, default: 0 for Luci-10)
        reset (bool)     : resets to default values, default=false
        device_type      : one of ['DLPVA-100-B-D']

    Also note that the manual switches must be set to the correct positions
    for remote operation, as specified in the amplifier manual.
    '''
    logging.info(__name__ + ' : Initializing instrument Femto_Luci10')
    Instrument.__init__(self, name, tags=['physical'])
    self._interface_id = address
    self._device_type = device_type

    if device_type == 'DLPVA-100-B-D':
    
      # (pin no, state that implies overload)
      self._overload_pin = (5,1)
      
      # (bit no, state that gives ac_mode), e.g. (3, 0) means that bit no 3 being 0 implies AC mode
      self._ac_coupling_bit = (3,0)

      # e.g. 1000: [ (2, 1), (1, 0) ] means that bit_2 == 1 and bit_1 == 0 --> gain of 1000.
      # (bits 0-7  == low byte)
      # (bits 8-15 == high byte)
      self._gains = { 10:    [ (2, 0) , (1, 0) ],
                      100:   [ (2, 0) , (1, 1) ],
                      1000:  [ (2, 1) , (1, 0) ],
                      10000: [ (2, 1) , (1, 1) ] }

      # same format as for gain.
      self._bandwidths = { 1000:   [ (4,0) ],
                           100000: [ (4,1) ] }
    else:
      raise Exception('Unknown device type: %s' % (device_type))
    
    self._last_communication_time = time.time()
    
    # Max communication rate is 300 Hz.
    self._min_time_between_commands = 0.010  # in second

    self._dll = ctypes.cdll.LoadLibrary(dll_path)

    self._find_device()

    self.add_parameter('overload', type=types.BooleanType, flags=Instrument.FLAG_GET)

    self.add_parameter('gain', type=types.IntType, flags=(Instrument.FLAG_SET|Instrument.FLAG_PERSIST),
                        minval=10, maxval=10000)

    self.add_parameter('bandwidth', type=types.IntType, flags=(Instrument.FLAG_SET|Instrument.FLAG_PERSIST),
                        minval=1, maxval=100000, units='Hz')

    self.add_parameter('ac_coupling', type=types.BooleanType, flags=(Instrument.FLAG_SET|Instrument.FLAG_PERSIST))

    self.add_function('reset')
    self.add_function('get_all')

    if reset: self.reset()
    self.get_all()

    # turn the LED off and on to signal success
    self._set_led(False)
    time.sleep(.5)
    self._set_led(True)

  def reset(self):
    '''
    Resets the instrument to default values

    Input:
        None

    Output:
        None
    '''
    logging.info(__name__ + ' : Resetting instrument')
    self.set_gain(10)


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

    self.get_overload()

  def _find_device(self):
    t = time.time()
    t_to_sleep = self._min_time_between_commands - (t - self._last_communication_time)
    if t_to_sleep > 0: time.sleep(t_to_sleep)

    no_of_devs = self._dll.EnumerateUsbDevices()
    if no_of_devs == 0: raise Exception('No Femto LUCI interfaces found!')
    time.sleep(self._min_time_between_commands)

    #logging.debug('No of USB devices found: %s' % str(no_of_devs))
    for i in range(1,1+no_of_devs):
      adapter_id = self._dll.ReadAdapterID(i)
      #logging.debug('adapter_id returned by USB device #%d: %s' % (i,adapter_id))
      if adapter_id == self._interface_id:
        self._usb_device_id = i
        return

    raise Exception('Specified Femto LUCI interface (ID = %d) not found!' % (self._interface_id))

  def _read(self, pin_no):
    '''
    Read the status of an input pin.
    '''
    for attempt in range(3):
      try:
        t = time.time()
        t_to_sleep = self._min_time_between_commands - (t - self._last_communication_time)
        if t_to_sleep > 0: time.sleep(t_to_sleep)
        if t_to_sleep < -1.: self._find_device() # update USB id

        r = getattr(self._dll, 'GetStatusPin%d' % pin_no)(ctypes.c_int(self._usb_device_id))
        self._last_communication_time = time.time()
        
        if not (r == 0 or r == 1):
          raise Exception('Failed to read pin #%u to device. Got %s' % (pin_no, r))

        return bool(r)
      except Exception as e:
        logging.warn('Failed to communicate with the amp: %s' % str(e))
        self._last_communication_time = time.time()
        time.sleep( .2 )
        self._clear_mainframe_output_buffer()
        time.sleep( .2+attempt )

  def _write(self, lowbyte, highbyte):
    '''
    Write the low and high output bytes. See also set_parameters.
    '''
    for attempt in range(3):
      try:
        t = time.time()
        t_to_sleep = self._min_time_between_commands - (t - self._last_communication_time)
        if t_to_sleep > 0: time.sleep(t_to_sleep)
        if t_to_sleep < -1.: self._find_device() # update USB id

        r = self._dll.WriteData(ctypes.c_int(self._usb_device_id), ctypes.c_int(lowbyte), ctypes.c_int(highbyte))
        if r != 0: raise Exception('Failed to write %u,%u to device. Got "%s".' % (lowbyte, highbyte, r))
        self._last_communication_time = time.time()

        return

      except Exception as e:
        logging.warn('Failed to write to LUCI: %s' % str(e))
        self._last_communication_time = time.time()
        time.sleep( .2 )
        self._clear_mainframe_output_buffer()
        time.sleep( .2+attempt )

  def _set_outputs(self, gain=None, bandwidth=None, ac_coupling=None):
    '''
    Change outputs to the specified values. If None, the previous value is used.
    
    This is a more convenient wrapper for the lower level method _write().
    '''
    # get previous value if None
    if gain == None: gain = self._get_value('gain', query=False)
    if bandwidth == None: bandwidth = self._get_value('bandwidth', query=False)
    if ac_coupling == None: ac_coupling = self._get_value('ac_coupling', query=False)

    # If still None (i.e. no previous value) use a reasonable default.
    if gain == None:
      gain = sorted(self._gains.keys())[0]
      logging.warn('Previous gain unknown. Using %g' % gain)
    if bandwidth == None:
      bandwidth = sorted(self._bandwidths.keys())[-1]
      logging.warn('Previous bandwidth unknown. Using %g' % bandwidth)
    if ac_coupling == None:
      ac_coupling = False
      logging.warn('Previous AC coupling value unknown. Using %s' % str(ac_coupling))
    
    outputs = 0
    outputs |= int(ac_coupling == bool(self._ac_coupling_bit[1])) << self._ac_coupling_bit[0]

    assert gain in self._gains.keys(), 'Unknown gain: %s' % (gain)
    for bit,state in self._gains[gain]:
      outputs |= int(bool(state)) << bit
    
    assert bandwidth in self._bandwidths.keys(), 'Unknown bandwidth: %s' % (bandwidth)
    for bit,state in self._bandwidths[bandwidth]:
      outputs |= int(bool(state)) << bit
    
    self._write(outputs % 256, outputs >> 8)
    self.update_value('gain', gain)
    self.update_value('bandwidth', bandwidth)
    self.update_value('ac_coupling', ac_coupling)

  def _set_led(self, on):
    for attempt in range(3):
      try:
        t = time.time()
        t_to_sleep = self._min_time_between_commands - (t - self._last_communication_time)
        if t_to_sleep > 0: time.sleep(t_to_sleep)
        if t_to_sleep < -1.: self._find_device() # update USB id

        if on: self._dll.LedOn(ctypes.c_int(self._usb_device_id))
        else:  self._dll.LedOff(ctypes.c_int(self._usb_device_id))
        self._last_communication_time = time.time()

      except Exception as e:
        logging.warn('Failed to change LUCI led state to %s: %s' % (str(on), str(e)))
        self._last_communication_time = time.time()
        time.sleep( .2 )
        self._clear_mainframe_output_buffer()
        time.sleep( .2+attempt )

  def do_set_gain(self, gain):
    '''
    Sets the gain of the amplifier.
    NOTE: Assumes a certain position of the manual switches! (See device manual.)
    
    Input:
        gain (int) : allowed values are device dependent
    '''
    self._set_outputs(gain=gain)

  def do_set_bandwidth(self, bandwidth):
    '''
    Sets the bandwidth of the amplifier.
    NOTE: Assumes a certain position of the manual switches! (See device manual.)
    
    Input:
        bandwidth (int) : allowed values are device dependent
    '''
    self._set_outputs(bandwidth=bandwidth)

  def do_set_ac_coupling(self, ac_coupling):
    '''
    Sets AC coupling on/off (off --> DC coupling).
    NOTE: Assumes a certain position of the manual switches! (See device manual.)
    
    Input:
        ac_coupling (bool) : AC (True) or DC (False) coupling
    '''
    self._set_outputs(ac_coupling=ac_coupling)

  def do_get_overload(self):
    '''
    Gets the overload status of the amplifier.

    Output:
        overload (bool) : whether amplifier is overloaded
    '''
    return self._read(self._overload_pin[0]) == self._overload_pin[1]
