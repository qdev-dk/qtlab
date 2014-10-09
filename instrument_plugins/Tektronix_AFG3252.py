# Driver for Tektronix_AFG3252
# Russell Lake <russell.lake@aalto.fi>
# Joonas Govenius <joonas.govenius@aalto.fi>
#
# Based originally on the Tektronix_AWG5014.py class. 
# Pieter de Groot <pieterdegroot@gmail.com>, 2008
# Martijn Schaafsma <qtlab@mcschaafsma.nl>, 2008
# Guenevere Prawiroatmodjo <guen@vvtp.tudelft.nl>, 2009
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
import numpy as np
import struct
import base64

class Tektronix_AFG3252(Instrument):
    '''
    This is the python driver for the Tektronix AFG3252
    Arbitrary Waveform Generator

    Usage:
    Initialize with
    <name> = instruments.create('name', 'Tektronix_AFG3252', address='<GPIB address>',
        reset=<bool>)

    think about:    clock, waveform length

    TODO:
    1) Get All
    2) Remove test_send??
    3) Add docstrings
    4) Add 4-channel compatibility
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the AFG3252.

        Input:
            name (string)    : name of the instrument
            address (string) : GPIB address
            reset (bool)     : resets to default values, default=false

        Output:
            None
        '''
        logging.debug(__name__ + ' : Initializing instrument')
        Instrument.__init__(self, name, tags=['physical'])


        self._address = address
        self._visainstrument = visa.instrument(self._address)

        # Add parameters
        self.add_parameter('output', type=types.BooleanType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), channel_prefix='ch%d_')

        self.add_parameter('ref_clock_mode',
            flags=Instrument.FLAG_GETSET|Instrument.FLAG_GET_AFTER_SET, type=types.StringType, format_map = {
                "INT" : "internal",
                "EXT" : "external"}) 

        self.add_parameter('amplitude', format='%.09e', type=types.FloatType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), minval=0, maxval=5., units='V', channel_prefix='ch%d_')

        self.add_parameter('offset', format='%.09e', type=types.FloatType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), minval=-2, maxval=2, units='V', channel_prefix='ch%d_')

        self.add_parameter('frequency', format='%.09e', type=types.FloatType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), minval=1E-6, maxval=240E6, units='Hz', channel_prefix='ch%d_')
        
        self.add_parameter('pulse_width', format='%.09e', type=types.FloatType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), minval=0, units='s', channel_prefix='ch%d_')
        
        self.add_parameter('pulse_delay', format='%.09e', type=types.FloatType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), minval=0, units='s', channel_prefix='ch%d_')

        self.add_parameter('load_impedance', type=types.FloatType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), minval=1, units='Ohm', channel_prefix='ch%d_')

        self.add_parameter('phase', format='%.09e', type=types.FloatType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), minval=0, maxval=6.283, units='rad', channel_prefix='ch%d_')

        self.add_parameter('shape', type=types.StringType,
            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
            channels=(1, 2), channel_prefix='ch%d_' , format_map = {
                "SIN" : "Sine",
                "SQU" : "Square",
                "PULS" : "Pulse",
                "RAMP" : "Ramp",
                "PRN" : "Noise",
                "DC" : "DC",
                "SINC" : "Sin(x)/x ",
                "GAUS" : "Gaussian",
                "LOR" : "Lorentz",
                "ERIS" : "Exp Rise",
                "EDEC" : "Exp Decay", 
                "HAV" : "Haversine",
                "USER1" :"USER1", 
                "USER2" :"USER2", 
                "USER3" :"USER3", 
                "USER4" :"USER4", 
                "EMEM" : "Edit Memory",
                "EFIL" : "EFile"}
)


        self.add_parameter('waveform_data', type=types.StringType, flags=Instrument.FLAG_GET, channels=(1, 2), channel_prefix='ch%d_')

        self.add_parameter('polarity', type=types.StringType, flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET, channels=(1, 2),channel_prefix='ch%d_', format_map={"INV" : "inverted","NORM" : "normal"}
)

        # Add functions
        self.add_function('reset')
        self.add_function('get_all')
        self.add_function('clear_waveforms')
        self.add_function('load_waveform')
        self.add_function('set_waveform')
        self.add_function('set_ch1_waveform')
        self.add_function('set_ch2_waveform')
        self.add_function('phase_sync')
        
        if not reset:
          self.get_all()
        else:
          self.reset()
        
        
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
        logging.info(__name__ + ' : Reading all data from instrument')

        self.get_ref_clock_mode()

        for i in range(1,3):
            self.get('ch%d_amplitude' % i)
            self.get('ch%d_offset' % i)
            self.get('ch%d_frequency' % i)
            self.get('ch%d_pulse_width' % i)
            self.get('ch%d_pulse_delay' % i)
            self.get('ch%d_shape' % i)
            self.get('ch%d_waveform_data' % i)
            self.get('ch%d_polarity' % i)
            self.get('ch%d_output' % i)
            self.get('ch%d_polarity' % i)
            self.get('ch%d_load_impedance' % i)
            self.get('ch%d_phase' % i)

    def clear_waveforms(self):
        '''
        Clears the waveform on both channels.

        Input:
            None

        Output:
            None
        '''
        logging.debug(__name__ + ' : Clear waveforms from channels')
        self._visainstrument.write('SOUR1:FUNC:USER ""')
        self._visainstrument.write('SOUR2:FUNC:USER ""')


    def phase_sync(self):
        '''
        Syncs the phases of ch1 and ch2.  Set the phase with the 'phase' parameter.

        Input:
            None

        Output:
            None
        '''
        logging.debug(__name__ + ' : Synchronizing the phase of CH1 and CH2.')
        self._visainstrument.write('SOUR1:PHASE:INITIATE')



   
    def do_set_output(self, state, channel):
        '''
        This command sets the output state of the AFG3252.
        Input:
            channel (int) : the source channel
            state (int) : on (1) or off (0)

        Output:
            None
        '''
        logging.debug(__name__ + ' : Set channel output state')
        self._visainstrument.write('OUTP%s:STAT %s' % (channel, 'ON' if state else 'OFF'))

    def do_get_output(self, channel):
        '''
        This command gets the output state of the AWG.
        Input:
            channel (int) : the source channel

        Output:
            state (int) : on (1) or off (0)
        '''
        logging.debug(__name__ + ' : Get channel output state')
        return self._visainstrument.ask('OUTP%s:STAT?' % channel).strip() in ['1', 'ON']
    

    # Parameters

    def do_get_amplitude(self, channel):
        '''
        Reads the amplitude of the designated channel from the instrument

        Input:
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            amplitude (float) : the amplitude of the signal in Volts
        '''
        r = self._visainstrument.ask('SOUR%s:VOLT:LEV:IMM:AMPL?' % channel)
        logging.debug(__name__ + ' : Get amplitude of channel %s from instrument: %s'
            % (channel, r))
        return float(r)/2.



    def do_set_amplitude(self, amp, channel):
        '''
        Sets the amplitude of the designated channel of the instrument.
        NOTE: Assumes that the AFG returns pk-to-pk amplitude (which it always does in the ARB mode)!

        Input:
            amp (float)   : amplitude in Volts.
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            None
        '''
        logging.debug(__name__ + ' : Set amplitude of channel %s to %.6f'
            % (channel, amp))
        self._visainstrument.write('SOUR%s:VOLT:LEV:IMM:AMPL %.6f' % (channel, 2*amp))


    def do_get_phase(self, channel):
        '''
        Reads the amplitude of the designated channel from the instrument

        Input:
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            amplitude (float) : the amplitude of the signal in Volts
        '''
        logging.debug(__name__ + ' : Get phase of channel %s from instrument'
            % channel)
        return float(self._visainstrument.ask('SOURCE%s:PHASE:ADJUST?' % channel))



    def do_set_phase(self, phase, channel):
        '''
        Sets the phase of the designated channel of the instrument.

        Input:
            amp (float)   : phase in rad.
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            None
        '''
        logging.debug(__name__ + ' : Set phase of channel %s to %.6f rad.'
            % (channel, amp))
        self._visainstrument.write('SOURCE%s:PHASE:ADJUST %.6f' % (channel, amp))



    def do_get_offset(self, channel):
        '''
        Reads the offset of the designated channel of the instrument

        Input:
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            offset (float) : offset of designated channel in Volts
        '''
        logging.debug(__name__ + ' : Get offset of channel %s' % channel)
        return float(self._visainstrument.ask('SOUR%s:VOLT:LEV:IMM:OFFS?' % channel))

    def do_set_offset(self, offset, channel):
        '''
        Sets the offset of the designated channel of the instrument

        Input:
            offset (float) : offset in Volts
            channel (int)  : 1 or 2, the number of the designated channel

        Output:
            None
        '''
        logging.debug(__name__ + ' : Set offset of channel %s to %.6f' % (channel, offset))
        self._visainstrument.write('SOUR%s:VOLT:LEV:IMM:OFFS %.6f' % (channel, offset))


    def do_get_frequency(self, channel):
        '''
        Reads the offset of the designated channel of the instrument

        Input:
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            offset (float) : offset of designated channel in Volts
        '''
        logging.debug(__name__ + ' : Get frequency of channel %s' % channel)
        return float(self._visainstrument.ask('SOUR%s:FREQ?' % channel))

    def do_set_frequency(self, frequency, channel):
        '''
        Sets the offset of the designated channel of the instrument

        Input:
            frequency (float) : frequency in Hz
            channel (int)  : 1 or 2, the number of the designated channel

        Output:
            None
        '''
        logging.debug(__name__ + ' : Set frequency of channel %s to %.11e' % (channel, frequency))

        # from the manual: resolution is 1 uHz or 12 digits
        rounded = '%.11e' % np.round(frequency,decimals=6)
        if np.abs(float(rounded) - frequency) > np.finfo(np.float).tiny:
          logging.warn('Rounding the requested frequency (%.15e Hz) to %s Hz (i.e. by %.6e Hz).' % (frequency, rounded, float(rounded) - frequency))

        self._visainstrument.write('SOUR%s:FREQ %s' % (channel, rounded))

    def do_get_pulse_width(self, channel):
        '''
        Reads the pulse width when shape is set to 'PULS'.

        Input:
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            width (float) : width in s
        '''
        logging.debug(__name__ + ' : Get pulse width of channel %s' % channel)
        return float(self._visainstrument.ask('SOUR%s:PULS:WIDT?' % channel))

    def do_set_pulse_width(self, width, channel):
        '''
        Sets the pulse width when shape is set to 'PULS'.

        Input:
            width (float) : width in s
            channel (int)  : 1 or 2, the number of the designated channel

        Output:
            None
        '''
        logging.debug(__name__ + ' : Set pulse width of channel %s to %.6f' % (channel, width))
        f = self.get('ch%d_frequency' % channel)
        duty = f*width
        if not (duty > 1e-5 and duty < 1-1e-5):
          logging.warn('The duty cycle of the pulse waveform must be between 0.001\% and 99.999\%, not %g.' % duty)
        self._visainstrument.write('SOUR%s:PULS:WIDT %.6f' % (channel, width))

    def do_get_pulse_delay(self, channel):
        '''
        Reads the pulse delay when shape is set to 'PULS'.

        Input:
            channel (int) : 1 or 2, the number of the designated channel

        Output:
            delay (float) : delay in s
        '''
        logging.debug(__name__ + ' : Get pulse delay of channel %s' % channel)
        return float(self._visainstrument.ask('SOUR%s:PULS:DEL?' % channel))

    def do_set_pulse_delay(self, delay, channel):
        '''
        Sets the pulse delay when shape is set to 'PULS'.

        Input:
            delay (float) : delay in s
            channel (int)  : 1 or 2, the number of the designated channel

        Output:
            None
        '''
        logging.debug(__name__ + ' : Set pulse delay of channel %s to %.6f' % (channel, delay))
        f = self.get('ch%d_frequency' % channel)
        w = self.get('ch%d_pulse_width' % channel)
        if delay + w > 1./f: logging.warn('AFG ch%d delay + pulse width is more (%g s) than the period of the waveform (%g s).' % (delay+w, 1./f))
        self._visainstrument.write('SOUR%s:PULS:DEL %.6f' % (channel, delay))
        
    def do_get_load_impedance(self, channel):
        '''
        Reads the output impedance of channel 1 or 2.

        Input:  None.

        Output:
            output impedance (float) : impedance in Ohm.
        '''
        logging.debug(__name__ + ' : Get load impedance of channel %s' % channel)
        return float(self._visainstrument.ask('OUTP%s:IMP?' % channel))



    def do_set_load_impedance(self, impedance, channel):
        '''
        Sets the output impedance of ch1 or ch2.

        Input:
            impedance (float) : output impedance in Ohm.
            channel (int)  : 1 or 2, the number of the designated channel

        Output:
            None
        '''
        imp = ("%.2e" % impedance) if impedance <= 1e4 else 'INF'
        
        if impedance > 1e4 and impedance < np.inf:
          logging.warn('%.3e Ohm load impedance not supported. Assuming you meant infinite load impedance. Use np.inf if you want to avoid this message.')
        
        logging.debug(__name__ + ' : Set load impedance of channel %s to %s' % (channel, imp))
        self._visainstrument.write('OUTP%s:IMP %s' % (channel, imp))




    def do_get_shape(self,channel):
        '''
        Query the shape of the output waveform.

        Output:
            shape (string) : shape set on ch1 or ch2
        '''
        logging.debug(__name__ + ' : Get shape of channel %s' % channel)
        return str(self._visainstrument.ask('SOUR%s:FUNC:SHAP?' % channel))

        
    def do_get_ref_clock_mode(self):
        '''
        Query the reference clock mode.

        Output:
            mode (string) : INTernal or EXTernal
        '''
        r = self._visainstrument.ask(':ROSCillator:SOURce?')
        logging.debug(__name__ + ' : Get the reference clock mode: %s' % r)
        return r
        
    def do_set_ref_clock_mode(self,val):
        '''
        Set the reference clock mode(INT or EXT).

        Input:
            mode(string): see context help. 
        '''
        logging.debug(__name__ + ' : Set the reference clock mode. %s' % val)
        self._visainstrument.write(':ROSC:SOUR %s' % val)    
        
        
    def do_get_waveform_data(self,channel):
        '''
        Copy the waveform data from channel (1,2) to EMEM and then download it so that it is saved in the parameters.  
        Channel 1 always uses USER1 and channel 2 always uses USER2.
        Output: Waveform data from ch1 (USER) and ch2 (USER2) are encoded in base64.
        '''

        # turn off all outputs
        output = [0., 0.]
        for ch in range(len(output)):
          output[ch] = getattr(self, 'get_ch%u_output' % (1+ch))()
          if output[ch] != 0.: getattr(self, 'set_ch%u_output' % (1+ch))(0.)

        msg = 'TRAC:COPY EMEM,USER%u' % (channel)
        self._visainstrument.write(msg)
        data = self._visainstrument.ask('TRAC:DATA? EMEM')

        # turn outputs back on (if they were on)
        for ch,outp in enumerate(output):
          #print "ch%u --> %.2f" % (ch, outp)
          if output[ch] != 0.: getattr(self, 'set_ch%u_output' % (1+ch))(outp)

        return base64.b64encode(data)

    def do_set_shape(self, shape, channel):
        '''
        Set the shape of the output waveform.

        Input:
            shape (string)
        '''
        logging.debug(__name__ + ' : Set shape of channel %s' % channel)
        self._visainstrument.write('SOUR%s:FUNC:SHAP %s' % (channel,shape))

    def delete_waveform(self, memory):
        '''
        Deletes the contents of the spcified user waveform memory.
        Input: memory.  Select intenal memory 1 - 4 to delete.
        1 - USER1
        2 - USER2
        3 - USER3
        4 - USER4
        '''
        self._visainstrument.write('TRACE:DEL:NAME USER%u' % memory)
        
    def reset_edit_memory(self,points=2000):
        '''
        Resets the contents of the edit memory.
        Input:
           points: number of points in the waveform in the edit memory (ranges from 2 to 131072).
        
        '''
        self._visainstrument.write('TRACE:DEFINE EMEMORY,%u' % points)


    def __waveform_to_byte_array(self,waveform, normalize_by_max_abs_val=False):
        '''
        Converts an array of real numbers between plus/minus one to a byte array
        accepted by the AFG.

        If normalize_by_max_abs_val is true, the waveform is normalized by the
        maximum absolute value of the elements.
        '''
        
        if normalize_by_max_abs_val:
          wave = waveform #/ np.abs(waveform).max()
        else:
          wave = waveform

        buf = bytearray(2*len(wave))
        for i in range(len(wave)):
          struct.pack_into('>H', buf, 2*i, int(np.round((1+wave[i]) * (2**13 - 1))))

        return buf

    def __byte_array_to_waveform(self, bytes):
        '''
        Converts an array of bytes (a string) queried from the AFG into a list
        of real numbers between plus/minus one.
        '''
        assert bytes[0] == "#", "The first character must be a hash! (See AFG manual for the data format.)"
        offset = 2 + int(bytes[1])
        bytecount = int(bytes[2:offset])
        fmt = '>%uH' % (bytecount/2)
        data = bytes[offset:]
        
        if bytecount%2 != 0 or bytecount != len(data):
          msg = 'WARN: wrong byte count (%u)! fmt: %s  len(data) = %u' % (bytecount, fmt, len(data))
          raise Exception(msg)

        return (np.array(struct.unpack(fmt, data)) - (2**13 - 1)) / (2**13 - 1.)

    def waveform_data_to_waveform(self, waveform_data):
        '''
        Converts a base64 encoded array of bytes (a string)
        obtained by get_ch1/2_waveform_data() into a list
        of real numbers between plus/minus one.
        '''
        return self.__byte_array_to_waveform(base64.b64decode(waveform_data))

    def load_waveform(self, waveform, normalize_by_max_abs_val = False, memory = 1):
        '''
        Initializes edit memory with the number of points in the waveform, deletes the USER# 
        memory that will be used, loads the waveform to edit memory and then copies it to 
        USER1, USER2, USER3 or USER4.

        Input:
              waveform (float) : wafeform data array (length between 2 and 131072)
            normalize_by_max_abs_val (bool): Normalize the waveform?  Default is False.
            memory (int)  : 1 - USER1, 2 - USER2, 3 - USER3 or 4 - USER4.

        Output:
            None
        '''
        
        assert (len(waveform) >= 2 and len(waveform) <= 131072), "Waveform length out of range."

        self.reset_edit_memory(len(waveform))
        self.delete_waveform(memory)
        buf = self.__waveform_to_byte_array(waveform, normalize_by_max_abs_val)
        msg = 'TRACE:DATA EMEM,#%u%u%s' % (len(str(len(buf))), len(buf), str(buf))
        self._visainstrument.write(msg)
        
        self._visainstrument.write('TRAC:COPY USER%s,EMEM' % memory)
        
########
    def set_waveform(self, waveform, normalize_by_max_abs_val, memory):
        '''
        Load the specified waveform (array of floats between plus/minus one)
        and update the waveform_data parameter.
        
        Length of the waveform must be between 2 and 131072.
        '''
        self.load_waveform(waveform, normalize_by_max_abs_val, memory)
        #    set the memory # = ch#
        self.get('ch%s_waveform_data' % memory)

    def set_ch1_waveform(self, waveform, normalize_by_max_abs_val=False):
        self.set_waveform(waveform, normalize_by_max_abs_val, 1)
        self.set_ch1_shape('USER1')

    def set_ch2_waveform(self, waveform, normalize_by_max_abs_val=False):
        self.set_waveform(waveform, normalize_by_max_abs_val, 2)
        self.set_ch2_shape('USER2')

##########

    def do_get_polarity(self, channel):
        '''
        Gets the polarity of the designated channel.

        Input:
            None

        Output:
            channel (int) : NORMal or INVerted
        '''
        logging.debug(__name__ + ' : Get polarity of channel %s' % channel)
        outp = self._visainstrument.ask('OUTP%s:POL?' % channel)
        if (outp=='NORM'):
            return 'normal'
        elif (outp=='INV'):
            return 'inverted'
        else:
            logging.debug(__name__ + ' : Read invalid status from instrument %s' % outp)
            return 'an error occurred while reading status from instrument'

    def do_set_polarity(self, state, channel):
        '''
        Sets the status of designated channel.

        Input:
            NORM for normal or INV for inverted polarity.

        Output:
            True or False.
        '''
        logging.debug(__name__ + ' : Set polarity of channel %s to %s' % (channel, state))
       
        if (state == 'NORM'):
            self._visainstrument.write('OUTP%s:POL NORM' % channel)
        if (state == 'INV'):
            self._visainstrument.write('OUTP%s:POL INV' % channel)

# self._visainstrument.write('OUTP%s:POL %s' % (channel, polarity))

#            self._visainstrument.write('OUTP%s:POL INV' % channel)
#           print 'Tried to set status to invalid value %s' % status


    # #  Ask for string with filenames
    # def get_filenames(self):
    #     logging.debug(__name__ + ' : Read filenames from instrument')
    #     return self._visainstrument.ask('MMEM:CAT? "MAIN"')




