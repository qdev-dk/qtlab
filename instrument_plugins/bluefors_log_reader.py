# bluefors_log_reader.py
# Joonas Govenius <joonas.goveius@aalto.fi>, 2014
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
import itertools

class bluefors_log_reader(Instrument):
    '''
    This is a driver for reading the Bluefors dillution fridge log files.

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'bluefors_log_reader', address='<path_to_log_files>', reset=<bool>)
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the bluefors_log_reader.

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

        self._tchannels = (1,2,5,6)
        self._rchannels = self._tchannels
        self._pchannels = (1,2,3,4,5,6)
        
        self.add_parameter('latest_t', channels=self._tchannels, format='%.3g',
            flags=Instrument.FLAG_GET, units='K', type=types.FloatType)
        self.add_parameter('latest_r', channels=self._rchannels, format='%.3g',
            flags=Instrument.FLAG_GET, units='Ohm', type=types.FloatType)
        self.add_parameter('latest_p', channels=self._pchannels, format='%.3g',
            flags=Instrument.FLAG_GET, units='mbar', type=types.FloatType)

        self.add_parameter('latest_flow',
            flags=Instrument.FLAG_GET, units='mmol/s', type=types.FloatType, format='%.3f')

        self.add_function('get_all')
        self.add_function('get_temperature')
        self.add_function('get_pressure')
        self.add_function('get_flow')

        # Add a number of parameters that are stored and named according to the same convention.
        self._params_in_common_format = [('turbo frequency', 'Hz'),
                                         ('turbo power', 'W'),
                                         ('turbo temperature_body', 'C'),
                                         ('turbo temperature_bearing', 'C'),
                                         ('turbo temperature_controller', 'C'),
                                         ('compressor oil_temperature', 'C'),
                                         ('compressor helium_temperature', 'C'),
                                         ('compressor water_in_temperature', 'C'),
                                         ('compressor water_out_temperature', 'C'),
                                         ('compressor pressure_low', 'psi (absolute)'),
                                         ('compressor pressure_high', 'psi (absolute)')]
        for param,units in self._params_in_common_format:
          param_wo_spaces = param.replace(' ','_')
          load_param = lambda t, ss=self, p=param: ss.__load_data(t, '%s %%s.log' % p)
          interp_param = ( lambda t=None, pp=param_wo_spaces, load_fn=load_param:
                           self.__interpolate_value_at_time(pp, load_fn, t) )

          setattr(self, 'get_%s' % param_wo_spaces, interp_param)
          self.add_function('get_%s' % param_wo_spaces)

          setattr(self, 'do_get_latest_%s' % param_wo_spaces, interp_param)
          self.add_parameter('latest_%s' % param_wo_spaces, format='%.3g', units=units,
                             flags=Instrument.FLAG_GET, type=types.FloatType)
        
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
        
        for ch in self._tchannels: getattr(self, 'get_latest_t%s' % ch)()
        for ch in self._rchannels: getattr(self, 'get_latest_r%s' % ch)()
        for ch in self._pchannels: getattr(self, 'get_latest_p%s' % ch)()

        self.get_latest_flow()

        for param,units in self._params_in_common_format:
          getattr(self, 'get_latest_%s' % param.replace(' ','_'))()
        
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
        
        return self.__interpolate_value_at_time(
          'T%d' % channel, lambda t: self.__load_data(t, 'CH%s T %%s.log' % channel), t)

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

        return self.__interpolate_value_at_time(
          'R%d' % channel, lambda t: self.__load_data(t, 'CH%s R %%s.log' % channel), t)

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
        
        def load_pressure_data(t):
          dd = self.__load_data(t, 'Maxigauge %s.log',
                                valueformats=['f', 'i1'],
                                usecols=(0,1,2+6*(channel-1)+3,2+6*(channel-1)+2))

          if dd == None or len(dd) == 0: raise Exception('load_data returned %s.' % dd)

          # replace value (2nd col) if the sensor was off (3rd col == 0)
          dd[dd[:,2] == 0, 1] = np.nan
          return dd[:,:2]
            
	
        return self.__interpolate_value_at_time('P%d' % channel, load_pressure_data, t)

    def get_flow(self, t=None):
        '''
        Gets the flow at time t.

        Input:
            t       -- datetime object

        Output:
            flow in mmol/s
        '''

        logging.debug(__name__ + ' : getting flow at t = {0}'.format(str(t)))
        
        return self.__interpolate_value_at_time(
          'flow', lambda t: self.__load_data(t, 'Flowmeter %s.log'), t)

    def do_get_latest_t(self, channel):
        '''
        Input:
            None

        Output:
            latest channel temperature in Kelvin.
        '''
        return self.get_temperature(channel)

    def do_get_latest_r(self, channel):
        '''
        Input:
            None

        Output:
            latest channel resistance in Ohms.
        '''
        return self.get_resistance(channel)

    def do_get_latest_p(self, channel):
        '''
        Input:
            None

        Output:
            latest channel pressure in mbar. nan if sensor is off.
        '''
        return self.get_pressure(channel)
        
    def do_get_latest_flow(self):
        '''
        Input:
            None

        Output:
            latest flow meter reading in mmol/s.
        '''
        return self.get_flow()


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


    def __interpolate_value_at_time(self, value_name, load_data, at_time=None, interpolation_kind='linear', cache_life_time=10.):
        '''
        Returns the interpolated value at 'at_time' based on the data loaded by the load_data function.

        Input:
            load_data(t)  -- function that loads the data in the neighborhood of time t
                             as a sequence of pairs [timestamp_as_datetime, value_as_float]
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
            data = load_data(t)
            if data == None or len(data) == 0: raise Exception('load_data returned %s.' % data)
          except Exception as e:
            logging.exception('Could not load %s at %s. Returning NaN.' % (value_name, str(t)))
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


    def __load_data(self, t, filename, valueformats=['f'], usecols=None):
      ''' Load data from the specified day as well as the preceding and following ones.

          filename must be a string with "%s" in place of the date string,
            e.g., "Flowmeter %s.log".

          valueformats describes the formats of the values stored on each line,
          excluding the time stamp.

          usecols can be passed as an additional parameter to loadtxt
          in order to ignore some columns.
      '''

      all_data = None
      for tt in [t-datetime.timedelta(1,0,0,0), t, t+datetime.timedelta(1,0,0,0)]:
        datestr = self.__time_to_datestr(tt)
        fname = os.path.join(self._address, datestr, filename % datestr)
        try:
          data = np.loadtxt(fname,
                            dtype={
                              'names': tuple(itertools.chain(['date', 'time'], ['value%d' % i for i in range(len(valueformats)) ])),
                              'formats': tuple(itertools.chain(['S9', 'S8'], valueformats))
                            }, delimiter=',', usecols=usecols)

          # convert the date & time strings to a datetime object
          data = np.array([ list(itertools.chain(
              [ datetime.datetime(int('20'+d[0].strip()[6:8]),
                                  int(d[0].strip()[3:5]),
                                  int(d[0].strip()[0:2]),
                                  int(d[1][0:2]), int(d[1][3:5]), int(d[1][6:8]),
                                  tzinfo=tz.tzlocal()) ],
              ( d[2+i] for i in range(len(valueformats)) )
            )) for d in data ])

          if all_data == None:
            all_data = data
          else:
            all_data = np.concatenate((all_data, data), axis=0)

        except IOError as e:
          pass # this is fairly normal, especially if tt is in the future

        except Exception as e:
          logging.exception('Failed to load data from %s.' % str(fname))

      if all_data == None:
          logging.warn('No data loaded for t = %s. Last attempt was from %s.', str(t), fname)

      return all_data


    def __time_to_datestr(self, t):
        return '{0}-{1:02d}-{2:02d}'.format(str(t.year)[-2:], t.month, t.day)


    def __line_to_datetime_val_pair(self, datestr, timestr, valstr):
        dateparts = datestr.split('-')
        timeparts = timestr.split(':')
        parsed_time = datetime.datetime(int('20'+(dateparts[2])), int(dateparts[1]), int(dateparts[0]), int(timeparts[0]), int(timeparts[1]), int(timeparts[2]), tzinfo=tz.tzlocal())
        val = float(valstr)
        return [ parsed_time, val ]
