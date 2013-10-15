# bluefors_log_reader.py class, to perform the communication between the Wrapper and the device
# Joonas Govenius <joonas.goveius@aalto.fi>, 2013
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
import numpy as np
from scipy import interpolate
import datetime
import pytz
from dateutil import tz
import os
import qt
import time

class bluefors_log_reader(Instrument):
    '''
    This is a driver for reading the Bluefors dillution fridge log files.

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'bluefors_log_reader', address='<path_to_log_files>', reset=<bool>)
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the bluefors_log_reader, and communicates with the wrapper.

        Input:
          name (string)    : name of the instrument
          address (string) : path to log files
          reset (bool)     : resets to default values, default=False
        '''
        logging.info(__name__ + ' : Initializing instrument bluefors_log_reader')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants
        self._address = address
        self._UNIX_EPOCH = datetime.datetime(1970, 1, 1, 0, 0, tzinfo = pytz.utc)
        
        self._heater_current_to_t6_calibration_ends = 0.006 # in amps
        self._heater_current_to_t6_polyfit_coefficients = np.array([-2.07985, 1.97048e3, -1.71080e6, 8.57267e8, - 2.25600e11, 2.95946e13, -1.52644e15]) # for current in A, gives log10(T/K)
        
        # t, r: 1,2,5,6
        self.add_parameter('latest_t1',
            flags=Instrument.FLAG_GET, units='K', type=types.FloatType)
        self.add_parameter('latest_t2',
            flags=Instrument.FLAG_GET, units='K', type=types.FloatType)
        self.add_parameter('latest_t5',
            flags=Instrument.FLAG_GET, units='K', type=types.FloatType)
        self.add_parameter('latest_t6',
            flags=Instrument.FLAG_GET, units='K', type=types.FloatType)

        self.add_parameter('latest_r1',
            flags=Instrument.FLAG_GET, units='Ohm', type=types.FloatType)
        self.add_parameter('latest_r2',
            flags=Instrument.FLAG_GET, units='Ohm', type=types.FloatType)
        self.add_parameter('latest_r5',
            flags=Instrument.FLAG_GET, units='Ohm', type=types.FloatType)
        self.add_parameter('latest_r6',
            flags=Instrument.FLAG_GET, units='Ohm', type=types.FloatType)

        # p: 1,..,6
        self.add_parameter('latest_p1',
            flags=Instrument.FLAG_GET, units='mbar', type=types.FloatType)
        self.add_parameter('latest_p2',
            flags=Instrument.FLAG_GET, units='mbar', type=types.FloatType)
        self.add_parameter('latest_p3',
            flags=Instrument.FLAG_GET, units='mbar', type=types.FloatType)
        self.add_parameter('latest_p4',
            flags=Instrument.FLAG_GET, units='mbar', type=types.FloatType)
        self.add_parameter('latest_p5',
            flags=Instrument.FLAG_GET, units='mbar', type=types.FloatType)
        self.add_parameter('latest_p6',
            flags=Instrument.FLAG_GET, units='mbar', type=types.FloatType)

        self.add_parameter('latest_flow',
            flags=Instrument.FLAG_GET, units='mmol/s', type=types.FloatType)

        self.add_function('get_temperature')
        self.add_function('get_pressure')
        self.add_function('get_flow')
        self.add_function ('get_all')
        
        self.add_function('base_heater_current_to_t6')


        if (reset):
            self.reset()
        else:
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
        logging.info(__name__ + ' : get all')
        
        self.get_latest_t1()
        self.get_latest_t2()
        self.get_latest_t5()
        self.get_latest_t6()
        
        self.get_latest_r1()
        self.get_latest_r2()
        self.get_latest_r5()
        self.get_latest_r6()

        self.get_latest_p1()
        self.get_latest_p2()
        self.get_latest_p3()
        self.get_latest_p4()
        self.get_latest_p5()
        self.get_latest_p6()
        
        self.get_latest_flow()
        
    def reset(self):
        '''
        Resets the instrument to default values

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : resetting instrument')
        pass

    def __interpolate_value_at_time(self, value_name, load_data, at_time=None, interpolation_kind='linear', cache_life_time=10.):
        '''
        Returns the interpolated value at 'at_time' based on the data loaded by the load_data function.

        Input:
            load_data  -- function that loads the desired data as a sequence of pairs [timestamp_as_datetime, value_as_float]
            at_time    -- datetime object
            value_name -- the value being queried, e.g. T1, T2, ... P1, P2, ...
            cache_life_time -- specifies how long previously parsed data is used (in seconds) before reparsing
            
        Output:
            Interpolated value at 'at_time'. Latest value if at_time==None.
        '''
        
        if at_time==None:
            t = datetime.datetime.now(tz.tzlocal())
        else:
            t = at_time
        
        # Check if a cache file for the given date exists
        
        cache_file_name = "%d-%d-%d_%s_bflog.npy" % (t.year, t.month, t.day, value_name)
        cache_file_path = os.path.join(qt.config.get('tempdir'), cache_file_name)
        data = None
        from_cache = False
        try:
          if at_time != None and time.time() - os.path.getmtime(cache_file_path) < cache_life_time:
            with open(cache_file_path, 'rb') as f:
              data = np.load(f)
              logging.debug('Loaded cached data from %s.' % (cache_file_path))
              from_cache = True
        except Exception as e:
          # cache file probably doesn't exist
          logging.debug('Failed to load a cached interpolating function from %s: %s' % (cache_file_path, str(e)))

        if not from_cache:
          # parse the data log files
          try:
            data = load_data(self._address, t)
          except Exception as e:
            logging.warn('Could not load %s at %s. Returning NaN. Exception: %s' % (value_name, str(t), str(e)))
            return np.NaN
                                                    
          try:
            with open(cache_file_path, 'wb') as f:
              np.save(f, data)
              logging.debug('Cached data in %s.' % (cache_file_path))
          except Exception as e:
            logging.debug('Could not dump data in %s: %s' % (cache_file_path, str(e)))

        # return the latest data point if nothing was specified.
        if at_time==None:
          if (t - data[-1][0]).total_seconds() > 305:
            logging.warn('last %s point from %s ago.' % (value_name, str(t - data[-1][0])))
          return data[-1][1]
      
        # create the interpolating function
        interpolating_fn = interpolate.interp1d([ (d[0] - self._UNIX_EPOCH).total_seconds() for d in data ], data[:,1],
                                                  kind=interpolation_kind, bounds_error=True)

        # finally use the interpolation function
        try:
            val = interpolating_fn((t - self._UNIX_EPOCH).total_seconds())
        except Exception as e:
            logging.warn('Could not interpolate value %s for t=%s: %s' %(value_name, str(t), str(e)))
            raise e
        
        return val

    def base_heater_current_to_t6(self, current):
      try:
        t6 = np.zeros(len(current))
        past_calibration_range = current.max() > self._heater_current_to_t6_calibration_ends
        scalar_input = False
      except TypeError:
        t6 = np.zeros(1)
        past_calibration_range = current > self._heater_current_to_t6_calibration_ends
        scalar_input = True
      
      if past_calibration_range:
        logging.warn("t6 has not been calibrated for heater currents exceeding %.3e Amp." % self._heater_current_to_t6_calibration_ends)
      
      for deg, coeff in enumerate(self._heater_current_to_t6_polyfit_coefficients):
        t6 += coeff * np.power(current, deg)
      
      # convert from log10 to linear scale
      t6 = np.power(10., t6)
      
      if scalar_input: return t6[0]
      else:            return t6

    def temperature(self, channel, t=None):
      '''
      Alias for get_temperature(...).
      '''
      return self.get_temperature(channel, t)

    def __line_to_datetime_val_pair(self, datestr, timestr, valstr):
        dateparts = datestr.split('-')
        timeparts = timestr.split(':')
        parsed_time = datetime.datetime(int('20'+(dateparts[2])), int(dateparts[1]), int(dateparts[0]), int(timeparts[0]), int(timeparts[1]), int(timeparts[2]), tzinfo=tz.tzlocal())
        val = float(valstr)
        return [ parsed_time, val ]

      
    def get_temperature(self, channel, t=None):
        '''
        Gets the temperature of channel at time t.

        Input:
            channel -- channel no.
            t       -- datetime object

        Output:
            temperature in K
        '''

        logging.debug(__name__ + ' : getting temperature for channel {0} at t = {1}'.format(channel, str(t)))
        
        def load_temperature_data(address, t):
          # load the data from the preceding and following days as well
          all_data = None
          for tt in [t-datetime.timedelta(1,0,0,0), t, t+datetime.timedelta(1,0,0,0)]:
            datestr = self.__time_to_datestr(tt)
            fname = os.path.join(self._address, datestr, 'CH{0} T {1}.log'.format(channel, datestr))

            try:
              data = np.loadtxt(fname, dtype={'names': ('date', 'time', 'temperature'), 'formats': ('S9', 'S8', 'f')}, delimiter=',')
              logging.debug('Loaded R%d data for %s.' % (channel, str(tt)))
            except Exception as e:
              if datetime.datetime.now(tz.tzlocal()) > tt: # The exception is normal if tt is in the future.
                logging.debug('Failed to load temperature data from %s).' % (fname))
              continue

            try:
              data = np.array([ self.__line_to_datetime_val_pair(*d) for d in data ])
              if all_data == None:
                all_data = data
              else:
                all_data = np.concatenate((all_data, data), axis=0)
            except Exception as e:
              logging.exception('Failed to parse temperature data from %s).' % (fname))

          if all_data == None:
            msg = 'No temperature data loaded for t = %s.' % str(t)
            logging.warn(msg)
            raise Exception(msg)

          return all_data


        return self.__interpolate_value_at_time('T%d' % channel, load_temperature_data, t)

    def resistance(self, channel, t=None):
        '''
        Alias for get_resistance(...)
        '''
        return self.get_resistance(channel, t)

    def get_resistance(self, channel, t=None):
        '''
        Gets the resistance of channel at time t.

        Input:
            channel -- channel no.
            t       -- datetime object

        Output:
            resistance in Ohm
        '''

        logging.debug(__name__ + ' : getting resistance for channel {0} at t = {1}'.format(channel, str(t)))
        
        def load_resistance_data(address, t):
          # load the data from the preceding and following days as well
          all_data = None
          for tt in [t-datetime.timedelta(1,0,0,0), t, t+datetime.timedelta(1,0,0,0)]:
            datestr = self.__time_to_datestr(tt)
            fname = os.path.join(self._address, datestr, 'CH{0} R {1}.log'.format(channel, datestr))
            
            try:
              data = np.loadtxt(fname, dtype={'names': ('date', 'time', 'resistance'), 'formats': ('S9', 'S8', 'f')}, delimiter=',')
              logging.debug('Loaded R%d data for %s.' % (channel, str(tt)))
            except Exception as e:
              if datetime.datetime.now(tz.tzlocal()) > tt: # The exception is normal if tt is in the future.
                logging.debug('Failed to load resistance data from %s).' % (fname))
              continue

            try:
              data = np.array([ self.__line_to_datetime_val_pair(*d) for d in data ])
              if all_data == None:
                all_data = data
              else:
                all_data = np.concatenate((all_data, data), axis=0)
            except Exception as e:
              logging.exception('Failed to parse resistance data from %s).' % (fname))

          if all_data == None:
            msg = 'No resistance data loaded for t = %s.' % str(t)
            logging.warn(msg)
            raise Exception(msg)

          return all_data

        return self.__interpolate_value_at_time('R%d' % channel, load_resistance_data, t)
        
    def pressure(self, channel, t=None):
        '''
        Alias for get_pressure(...).
        '''
        return self.get_pressure(channel, t)

    def get_pressure(self, channel, t=None):
        '''
        Gets the pressure of channel at time t.

        Input:
            channel -- channel no.
            t       -- datetime object

        Output:
            pressure of channel in mbar at time t. nan if sensor was off.
        '''

        logging.debug(__name__ + ' : getting pressure for channel {0} at t = {1}'.format(channel, str(t)))
        
        def load_pressure_data(address, t):
          # load the data from the preceding and following days as well
          all_data = None
          for tt in [t-datetime.timedelta(1,0,0,0), t, t+datetime.timedelta(1,0,0,0)]:
            datestr = self.__time_to_datestr(tt)
            fname = os.path.join(self._address, datestr, 'Maxigauge {0}.log'.format(datestr))
            try:
              data = np.loadtxt(fname, dtype={'names': ('date', 'time', 'pressure', 'status'), 'formats': ('S9', 'S8', 'f', 'i1')}, delimiter=',', usecols=(0,1,2+6*(channel-1)+3,2+6*(channel-1)+4))
              # replace the value with NaN if the sensor is off (status != 0)
              # and convert the date & time strings to a datetime object
              data = [ [datetime.datetime(int('20'+d[0][6:8]), int(d[0][3:5]), int(d[0][0:2]), int(d[1][0:2]), int(d[1][3:5]), int(d[1][6:8]), tzinfo=tz.tzlocal()),
                          d[2] if d[3]==0 else float('nan')] for d in data ]
              if all_data == None:
                all_data = data
              else:
                all_data = np.concatenate((all_data, data), axis=0)
            except Exception as e:
              if datetime.datetime.now(tz.tzlocal()) > tt: # The exception is normal if tt is in the future.
                logging.debug('Failed to load pressure data for %s.' % str(tt))
              pass

          if all_data == None:
            msg = 'No pressure data loaded for t = %s.' % str(t)
            logging.warn(msg)
            raise Exception(msg)

          return all_data

	
        return self.__interpolate_value_at_time('P%d' % channel, load_pressure_data, t)

    def flow(self, t=None):
        '''
        Alias for get_flow(...).
        '''
        return self.get_flow(t)

    def get_flow(self, t=None):
        '''
        Gets the flow at time t.

        Input:
            t       -- datetime object

        Output:
            flow in mmol/s
        '''

        logging.debug(__name__ + ' : getting flow at t = {0}'.format(str(t)))
        
        def load_flow_data(address, t):
          # load the data from the preceding and following days as well
          all_data = None
          for tt in [t-datetime.timedelta(1,0,0,0), t, t+datetime.timedelta(1,0,0,0)]:
            datestr = self.__time_to_datestr(tt)
            fname = os.path.join(self._address, datestr, 'Flowmeter {0}.log'.format(datestr))
            try:
              data = np.loadtxt(fname, dtype={'names': ('date', 'time', 'flow'), 'formats': ('S9', 'S8', 'f')}, delimiter=',')
              # convert the date & time strings to a datetime object
              data = np.array([ [datetime.datetime(int('20'+d[0][7:9]), int(d[0][4:6]), int(d[0][1:3]), int(d[1][0:2]), int(d[1][3:5]), int(d[1][6:8]), tzinfo=tz.tzlocal()), d[2]] for d in data ])
              if all_data == None:
                all_data = data
              else:
                all_data = np.concatenate((all_data, data), axis=0)
            except Exception as e:
              if datetime.datetime.now(tz.tzlocal()) > tt: # The exception is normal if tt is in the future.
                logging.debug('Failed to load flow data for %s.' % str(tt))
              pass

          if all_data == None:
            msg = 'No flow data loaded for t = %s.' % str(t)
            logging.warn(msg)
            raise Exception(msg)
        
          return all_data

        return self.__interpolate_value_at_time('flow', load_flow_data, t)

        
    def __time_to_datestr(self, t):
        return '{0}-{1:02d}-{2:02d}'.format(str(t.year)[-2:], t.month, t.day)

        
    def do_get_latest_t1(self):
        '''
        Input:
            None

        Output:
            latest channel 1 temperature in Kelvin.
        '''
        return self.get_temperature(1)

    def do_get_latest_t2(self):
        '''
        Input:
            None

        Output:
            latest channel 2 temperature in Kelvin.
        '''
        return self.get_temperature(2)

    def do_get_latest_t5(self):
        '''
        Input:
            None

        Output:
            latest channel 5 temperature in Kelvin.
        '''
        return self.get_temperature(5)

    def do_get_latest_t6(self):
        '''
        Input:
            None

        Output:
            latest channel 6 temperature in Kelvin.
        '''
        return self.get_temperature(6)


    def do_get_latest_r1(self):
        '''
        Input:
            None

        Output:
            latest channel 1 resistance in Ohms.
        '''
        return self.get_resistance(1)

    def do_get_latest_r2(self):
        '''
        Input:
            None

        Output:
            latest channel 2 resistance in Ohms.
        '''
        return self.get_resistance(2)

    def do_get_latest_r5(self):
        '''
        Input:
            None

        Output:
            latest channel 5 resistance in Ohms.
        '''
        return self.get_resistance(5)

    def do_get_latest_r6(self):
        '''
        Input:
            None

        Output:
            latest channel 6 resistance in Ohms.
        '''
        return self.get_resistance(6)

    def do_get_latest_p1(self):
        '''
        Input:
            None

        Output:
            latest channel 1 pressure in mbar. nan if sensor is off.
        '''
        return self.get_pressure(1)
        
    def do_get_latest_p2(self):
        '''
        Input:
            None

        Output:
            latest channel 2 pressure in mbar. nan if sensor is off.
        '''
        return self.get_pressure(2)
        
    def do_get_latest_p3(self):
        '''
        Input:
            None

        Output:
            latest channel 3 pressure in mbar. nan if sensor is off.
        '''
        return self.get_pressure(3)
        
    def do_get_latest_p4(self):
        '''
        Input:
            None

        Output:
            latest channel 4 pressure in mbar. nan if sensor is off.
        '''
        return self.get_pressure(4)
        
    def do_get_latest_p5(self):
        '''
        Input:
            None

        Output:
            latest channel 5 pressure in mbar. nan if sensor is off.
        '''
        return self.get_pressure(5)
        
    def do_get_latest_p6(self):
        '''
        Input:
            None

        Output:
            latest channel 6 pressure in mbar. nan if sensor is off.
        '''
        return self.get_pressure(6)
        
        
    def do_get_latest_flow(self):
        '''
        Input:
            None

        Output:
            latest flow meter reading in mmol/s.
        '''
        return self.get_flow()
