# heater_controller.py, driver for controlling cryostat heating power
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
import types
import logging
import time
import numpy as np
import qt

class heater_controller(Instrument):
  '''
  Driver for controlling cryostat heating.

  Usage:
  Initialize with
  <name> = instruments.create('name', 'heater_controller', address='<GPIB address>',
      reset=<bool>)
  '''

  def __init__(self, name, set_heater_current, get_heater_current, get_temperature=None, update_interval=15., reset=False):
    '''
    Initializes the heater_controller.

    Input:
        name (string)                : name of the instrument
        set_heater_current(function) : function that sets the heating current, in Amps
        get_heater_current(function) : function that gets the heating current, in Amps
        get_temperature (function)   : function that gets the current temperature
        update_interval (float)      : time scale for feedback operations, in seconds
        reset (bool)                 : resets to default values, default=false

    Output:
        None
    '''
    logging.info(__name__ + ' : Initializing instrument heater_controller: %s' % name)
    Instrument.__init__(self, name, tags=['physical'])
    
    self._set_heater_current = set_heater_current
    self._get_heater_current = get_heater_current
    self._get_temperature = get_temperature
    self._update_interval = update_interval

    self.add_parameter('heater_current', type=types.FloatType, flags=Instrument.FLAG_GETSET, units='A')
    self.add_parameter('last_value_set', type=types.FloatType, flags=Instrument.FLAG_GET|Instrument.FLAG_PERSIST, units='A')
    self.add_parameter('last_change_time', type=types.FloatType, flags=Instrument.FLAG_GET|Instrument.FLAG_PERSIST, units='s')
    self.add_parameter('thermalization_time', type=types.FloatType, flags=Instrument.FLAG_GETSET|Instrument.FLAG_PERSIST, units='s')
    self.add_parameter('time_until_steady_state', type=types.FloatType, flags=Instrument.FLAG_GET, units='s')
    self.add_parameter('steady_state_reached', type=types.BooleanType, flags=Instrument.FLAG_GET)
    
    # Get/set some initial values
    self.get_heater_current()
    if self.get_last_change_time() == None: self.update_value('last_change_time', time.time())
    if self.get_thermalization_time() == None: self.update_value('thermalization_time', 3000.)
    self.get_all()

  def reset(self):
    '''
    Resets the instrument to default values

    Input:
        None

    Output:
        None
    '''
    logging.info(__name__ + ' : Resetting instrument')
    #self.get_all()


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
    self.get_heater_current()
    self.get_time_until_steady_state()
    self.get_steady_state_reached()

  def block_until_thermalization(self):
    logging.info('Sleeping approximately %g seconds until thermalization.', max(0., self.get_time_until_steady_state()))
    while not self.get_steady_state_reached():
      qt.msleep(10.) # sleep only 10 seconds at a time --> keeps updating the time_left parameter
    
  def do_set_heater_current(self, current):
    # TODO: provide a set_target_temperature function that uses feedback to reach a steady temperature faster
    self._set_heater_current(current)
    if self.get_last_value_set() != current:
      self.update_value('last_value_set', current)
      self.update_value('last_change_time', time.time())

  def do_get_heater_current(self):
    current = self._get_heater_current()
    if self.get_last_value_set() != current:
      self.update_value('last_value_set', current)
      self.update_value('last_change_time', time.time())
    return current

  def do_get_last_value_set(self):
    return self.get('last_value_set', query=False)

  def do_get_last_change_time(self):
    return self.get('last_change_time', query=False)

  def do_get_thermalization_time(self):
    return self.get('thermalization_time', query=False)
  def do_set_thermalization_time(self, t):
    self.update_value('thermalization_time', t)

  def do_get_time_until_steady_state(self):
    # TODO: be smarter about this if a get_temperature function is provided.
    time_left = self.get_thermalization_time() - (time.time() - self.get_last_change_time())
    self.update_value('steady_state_reached', time_left <= 0)
    return time_left

  def do_get_steady_state_reached(self):
    self.get_time_until_steady_state()
    return self.get('steady_state_reached', query=False)
