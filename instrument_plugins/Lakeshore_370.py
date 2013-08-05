# Lakeshore 370, Lakeshore 370 temperature controller driver
# Joonas Govenius <joonas.govenius@aalto.fi>, 2013
# Based on Lakeshore 340 driver by Reinier Heeres <reinier@heeres.eu>, 2010.
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
import re
import math
import time
import numpy as np

class Lakeshore_370(Instrument):

    def __init__(self, name, address, reset=False, **kwargs):
        Instrument.__init__(self, name)

        self._address = address
    
        visaargs = {}
        if address.lower().startswith('asrl'):
          # These are for an RS-232 connection, values found in the LS manual
          visaargs['parity'] = visa.odd_parity
          visaargs['data_bits'] = 7
          visaargs['stop_bits'] = 1
        self._visa = visa.instrument(self._address,
                                     term_chars='\n', # This is set on the screen (behind "Computer Interface")
                                     **visaargs)
        
        self._channels = kwargs.get('channels', (1, 2, 5, 6))
        
        self._logger = kwargs.get('logger', None)
        
        self.add_parameter('identification',
            flags=Instrument.FLAG_GET)
            
        self.add_parameter('common_mode_reduction',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType)
            
        self.add_parameter('guard_drive',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType)

        self.add_parameter('scanner_auto',
            flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)
            
        self.add_parameter('scanner_channel',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map=dict(zip(self._channels,self._channels)))

        self.add_parameter('kelvin',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            channels=self._channels,
            units='K')

        self.add_parameter('resistance',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            channels=self._channels,
            units='Ohm')

        self.add_parameter('resistance_range',
            flags=Instrument.FLAG_GET,
            type=types.StringType,
            channels=self._channels,
            format_map={
                1: '2 mOhm',
                2: '6.32 mOhm',
                3: '20 mOhm',
                4: '63.2 mOhm',
                5: '200 mOhm',
                6: '632 mOhm',
                7: '2 Ohm',
                8: '6.32 Ohm',
                9: '20 Ohm',
                10: '63.2 Ohm',
                11: '200 Ohm',
                12: '632 Ohm',
                13: '2 kOhm',
                14: '6.32 kOhm',
                15: '20 kOhm',
                16: '63.2 kOhm',
                17: '200 kOhm',
                18: '632 kOhm',
                19: '2 MOhm',
                20: '6.32 MOhm',
                21: '20 MOhm',
                22: '63.2 MOhm'
                })

        self.add_parameter('excitation_mode',
            flags=Instrument.FLAG_GET,
            type=types.IntType,
            channels=self._channels,
            format_map={
                0: 'voltage',
                1: 'current'
                })

        self.add_parameter('excitation_on',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType,
            channels=self._channels)

        self.add_parameter('excitation_range',
            flags=Instrument.FLAG_GET,
            type=types.StringType,
            channels=self._channels,
            format_map={
                1: '2 uV or 1 pA',
                2: '6.32 uV or 3.16 pA',
                3: '20 uV or 10 pA',
                4: '63.2 uV or 31.6 pA',
                5: '200 uV or 100 pA',
                6: '632 uV or 316 pA',
                7: '2 mV or 1 nA',
                8: '6.32 mV or 3.16 nA',
                9: '20 mV or 10 nA',
                10: '63.2 mV or 31.6 nA',
                11: '200 mV or 100 nA',
                12: '632 mV or 316nA',
                13: '1 uA',
                14: '3.16 uA',
                15: '10 uA',
                16: '31.6 uA',
                17: '100 uA',
                18: '316 uA',
                19: '1 mA',
                20: '3,16 mA',
                21: '10 mA',
                22: '31.6 mA'
                })

        self.add_parameter('autorange',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType,
            channels=self._channels)

        self.add_parameter('scanner_dwell_time',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='s',
            channels=self._channels)

        self.add_parameter('scanner_pause_time',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='s',
            channels=self._channels)

        self.add_parameter('filter_on',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType,
            channels=self._channels)

        self.add_parameter('filter_settle_time',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            units='s',
            channels=self._channels)

        self.add_parameter('filter_reset_threshold',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='%',
            channels=self._channels)

        self._heater_ranges = {
            0: 'off',
            1: '31.6 uA',
            2: '100 uA',
            3: '316 uA',
            4: '1 mA',
            5: '3.16 mA',
            6: '10 mA',
            7: '31.6 mA',
            8: '100 mA' }
        self.add_parameter('heater_range',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map=self._heater_ranges)

        self.add_parameter('heater_power',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='W or %')

        self.add_parameter('heater_status',
            flags=Instrument.FLAG_GET,
            type=types.IntType,
            format_map={
                0: 'OK',
                1: 'heater open error'
                })

        self.add_parameter('mode',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map={0: 'Local', 1: 'Remote', 2: 'Remote, local lock'})

        self.add_parameter('temperature_control_mode',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map={
                1: 'closed loop PID',
                2: 'Zone tuning',
                3: 'open loop',
                4: 'off'
                })

        self.add_parameter('temperature_control_pid',
            flags=Instrument.FLAG_GETSET,
            type=types.TupleType)

        self.add_parameter('temperature_control_setpoint',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType)

        self.add_parameter('temperature_control_channel',
            flags=Instrument.FLAG_GET,
            type=types.IntType,
            format_map=dict(zip(self._channels,self._channels)))

        self.add_parameter('temperature_control_use_filtered_reading',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType)

        self.add_parameter('temperature_control_setpoint_units',
            flags=Instrument.FLAG_GET,
            type=types.IntType,
            format_map={1: 'K', 2: 'Ohm'})

        self.add_parameter('temperature_control_heater_max_range',
            flags=Instrument.FLAG_GET,
            type=types.IntType,
            format_map=self._heater_ranges)

        self.add_parameter('temperature_control_heater_load_resistance',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='Ohm')

        self.add_function('local')
        self.add_function('remote')

        if reset:
            self.reset()
        else:
            self.get_all()

    def reset(self):
        self.__write('*RST')

    def get_all(self):
        self.get_identification()
        self.get_mode()        

        self.get_scanner_auto()
        self.get_scanner_channel()

        self.get_temperature_control_mode()
        self.get_temperature_control_pid()
        self.get_temperature_control_setpoint()
        self.get_temperature_control_setpoint_units()
        self.get_temperature_control_channel()
        self.get_temperature_control_use_filtered_reading()
        self.get_temperature_control_heater_max_range()
        self.get_temperature_control_heater_load_resistance()
        
        self.get_heater_range()
        self.get_heater_status()
        self.get_heater_power()
        self.get_common_mode_reduction()
        self.get_guard_drive()
        
        for ch in self._channels:
          getattr(self, 'get_kelvin%s' % ch)()
          getattr(self, 'get_resistance%s' % ch)()
          getattr(self, 'get_resistance_range%s' % ch)()
          getattr(self, 'get_excitation_on%s' % ch)()
          getattr(self, 'get_excitation_mode%s' % ch)()
          getattr(self, 'get_excitation_range%s' % ch)()
          getattr(self, 'get_autorange%s' % ch)()
          getattr(self, 'get_scanner_dwell_time%s' % ch)()
          getattr(self, 'get_scanner_pause_time%s' % ch)()
          getattr(self, 'get_filter_on%s' % ch)()
          getattr(self, 'get_filter_settle_time%s' % ch)()
          getattr(self, 'get_filter_reset_threshold%s' % ch)()
          
          

    def __ask(self, msg):
        return self._visa.ask("%s" % msg).replace('\r','')

    def __write(self, msg):
        self._visa.write("%s" % msg)

    def do_get_identification(self):
        return self.__ask('*IDN?')
        
    def do_get_common_mode_reduction(self):
        ans = self.__ask('CMR?')
        return bool(int(ans))
        
    def do_get_guard_drive(self):
        ans = self.__ask('GUARD?')
        return bool(int(ans))
        
    def do_get_scanner_auto(self):
        ans = self.__ask('SCAN?')
        return bool(int(ans.split(',')[1]))

    def do_set_scanner_auto(self, val):
        ch = self.get_scanner_channel()
        cmd = 'SCAN %d,%d' % (ch, 1 if val else 0)
        self.__write(cmd)
        time.sleep(.1)
        self.get_scanner_auto()
        self.get_scanner_channel()
        
    def do_get_scanner_channel(self):
        ans = self.__ask('SCAN?')
        return int(ans.split(',')[0])

    def do_set_scanner_channel(self, val):
        auto = self.get_scanner_auto()
        cmd = 'SCAN %d,%d' % (val, 1 if auto else 0)
        self.__write(cmd)
        time.sleep(.1)
        self.get_scanner_auto()
        self.get_scanner_channel()

    def do_get_kelvin(self, channel):
        ans = float(self.__ask('RDGK? %s' % channel))
        if self._logger != None: self._logger('kelvin', channel, ans)
        return ans
        
    def do_get_resistance(self, channel):
        ans = float(self.__ask('RDGR? %s' % channel))
        if self._logger != None: self._logger('resistance', channel, ans)
        return ans
        
    def do_get_resistance_range(self, channel):
        ans = self.__ask('RDGRNG? %s' % channel)
        return int(ans.split(',')[2])
        
    def do_get_excitation_mode(self, channel):
        ans = self.__ask('RDGRNG? %s' % channel)
        return int(ans.split(',')[0])
        
    def do_get_excitation_range(self, channel):
        ans = self.__ask('RDGRNG? %s' % channel)
        return int(ans.split(',')[1])
        
    def do_get_autorange(self, channel):
        ans = self.__ask('RDGRNG? %s' % channel)
        return bool(int(ans.split(',')[3]))
        
    def do_get_excitation_on(self, channel):
        ans = self.__ask('RDGRNG? %s' % channel)
        return (int(ans.split(',')[4]) == 0)
        
    def do_get_scanner_dwell_time(self, channel):
        ans = self.__ask('INSET? %s' % channel)
        return float(ans.split(',')[1])
        
    def do_get_scanner_pause_time(self, channel):
        ans = self.__ask('INSET? %s' % channel)
        return float(ans.split(',')[2])
        
    def do_get_filter_on(self, channel):
        ans = self.__ask('FILTER? %s' % channel)
        return bool(int(ans.split(',')[0]))
        
    def do_get_filter_settle_time(self, channel):
        ans = self.__ask('FILTER? %s' % channel)
        return float(ans.split(',')[1])
        
    def do_set_filter_settle_time(self, val, channel):
        cmd = 'FILTER %s,1,%d,80' % (channel,int(np.round(val)))
        self.__write(cmd)
        time.sleep(.1)
        getattr(self, 'get_filter_settle_time%s' % channel)()
        
    def do_get_filter_reset_threshold(self, channel):
        ans = self.__ask('FILTER? %s' % channel)
        return float(ans.split(',')[2])
        
    def do_get_heater_range(self):
        ans = self.__ask('HTRRNG?')
        return int(ans)
        
    def do_get_heater_power(self):
        ans = self.__ask('HTR?')
        return float(ans)
        
    def do_set_heater_range(self, val):
        self.__write('HTRRNG %d' % val)
        time.sleep(.1)
        self.get_heater_range()
        
    def do_get_heater_status(self):
        ans = self.__ask('HTRST?')
        return ans
        
    def do_get_mode(self):
        ans = self.__ask('MODE?')
        return int(ans)

    def do_set_mode(self, mode):
        self.__write('MODE %d' % mode)
        time.sleep(.1)
        self.get_mode()

    def local(self):
        self.set_mode(1)

    def remote(self):
        self.set_mode(2)
        
    def do_get_temperature_control_mode(self):
        ans = self.__ask('CMODE?')
        return int(ans)

    def do_set_temperature_control_mode(self, mode):
        self.__write('CMODE %d' % mode)
        time.sleep(.1)
        self.get_temperature_control_mode()

    def do_get_temperature_control_pid(self):
        ans = self.__ask('PID?')
        fields = ans.split(',')
        if len(fields) != 3:
            return None
        fields = [float(f) for f in fields]
        return fields

    def do_set_temperature_control_pid(self, val):
        assert len(val) == 3, 'PID parameter must be a triple of numbers.'
        assert val[0] >= 0.001 and val[0] < 1000, 'P out of range.'
        assert val[1] >= 0 and val[1] < 10000, 'I out of range.'
        assert val[2] >= 0 and val[2] < 2500, 'D out of range.'
        cmd = 'PID %.5g,%.5g,%.5g' % (val[0], val[1], val[2])
        self.__write(cmd)
        time.sleep(.1)
        self.get_temperature_control_pid()
       
    def do_get_temperature_control_setpoint(self):
        ans = self.__ask('SETP?')
        return float(ans)
        
    def do_set_temperature_control_setpoint(self, val):
        self.__write('SETP %.3E' % (val))
        time.sleep(.1)
        self.get_temperature_control_setpoint()
        
    def do_get_temperature_control_channel(self):
        ans = self.__ask('CSET?')
        return int(ans.split(',')[0])
        
    def do_get_temperature_control_use_filtered_reading(self):
        ans = self.__ask('CSET?')
        return bool(ans.split(',')[1])
        
    def do_get_temperature_control_setpoint_units(self):
        ans = self.__ask('CSET?')
        return ans.split(',')[2]
        
    def do_get_temperature_control_heater_max_range(self):
        ans = self.__ask('CSET?')
        return int(ans.split(',')[5])
        
    def do_get_temperature_control_heater_load_resistance(self):
        ans = self.__ask('CSET?')
        return float(ans.split(',')[6])
