import numpy as np
import pulse
import pulsar

class OriginalEOMAOMPulse(pulse.Pulse):
    def __init__(self, name, eom_channel, aom_channel,  **kw):
        pulse.Pulse.__init__(self, name)
        self.eom_channel = eom_channel
        self.aom_channel = aom_channel

        self.channels = [eom_channel,aom_channel]
                                               
        self.eom_pulse_duration        = kw.pop('eom_pulse_duration'      ,2e-9) 
        self.eom_off_duration          = kw.pop('eom_off_duration'        ,150e-9)
        self.eom_off_amplitude         = kw.pop('eom_off_amplitude'       ,-.25)
        self.eom_pulse_amplitude       = kw.pop('eom_pulse_amplitude'     ,1.2)
        self.eom_overshoot_duration1   = kw.pop('eom_overshoot_duration1' ,10e-9)
        self.eom_overshoot1            = kw.pop('eom_overshoot1'          ,-0.03)
        self.eom_overshoot_duration2   = kw.pop('eom_overshoot_duration2' ,4e-9)
        self.eom_overshoot2            = kw.pop('eom_overshoot2'          ,-0.03)
        self.aom_risetime              = kw.pop('aom_risetime'            ,23e-9)
        self.aom_amplitude             = kw.pop('aom_amplitude'           ,1.0)

        self.start_offset   = self.eom_off_duration
        self.stop_offset    = 3*self.eom_off_duration+self.eom_pulse_duration
        self.length         = 4*self.eom_off_duration+2.*self.eom_pulse_duration                                      
        
    def __call__(self,  **kw):
        self.eom_pulse_duration        = kw.pop('eom_pulse_duration'      ,self.eom_pulse_duration) 
        self.eom_off_duration          = kw.pop('eom_off_duration'        ,self.eom_off_duration)
        self.eom_off_amplitude         = kw.pop('eom_off_amplitude'       ,self.eom_off_amplitude)
        self.eom_pulse_amplitude       = kw.pop('eom_pulse_amplitude'     ,self.eom_pulse_amplitude)
        self.eom_overshoot_duration1   = kw.pop('eom_overshoot_duration1' ,self.eom_overshoot_duration1)
        self.eom_overshoot1            = kw.pop('eom_overshoot1'          ,self.eom_overshoot1)
        self.eom_overshoot_duration2   = kw.pop('eom_overshoot_duration2' ,self.eom_overshoot_duration2)
        self.eom_overshoot2            = kw.pop('eom_overshoot2'          ,self.eom_overshoot2)
        self.aom_risetime              = kw.pop('aom_risetime'            ,self.aom_risetime)
        self.aom_amplitude             = kw.pop('aom_amplitude'           ,1.0)
        
        self.start_offset   = self.eom_off_duration
        self.stop_offset    = 3*self.eom_off_duration+self.eom_pulse_duration        
        self.length         = 4*self.eom_off_duration + 2*self.eom_pulse_duration

        return self
        
       
    def chan_wf(self, channel, tvals):
        
        tvals -= tvals[0]
        tvals = np.round(tvals, pulsar.SIGNIFICANT_DIGITS) 
        
        if channel == self.eom_channel:

            off_time1_start     = 0
            off_time1_stop      = np.where(tvals <= self.eom_off_duration)[0][-1]
            opt_pulse_stop      = np.where(tvals <= np.round(
                self.eom_off_duration+self.eom_pulse_duration, 
                    pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            overshoot1_stop     = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_pulse_duration + \
                                    self.eom_overshoot_duration1,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            overshoot2_stop     = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_pulse_duration + self.eom_overshoot_duration1 + \
                                    self.eom_overshoot_duration2,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            off_time2_stop      = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_pulse_duration + \
                                     self.eom_off_duration,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
    
            #print len(tvals)
            wf = np.zeros(len(tvals)/2)
            wf[off_time1_start:off_time1_stop] += self.eom_off_amplitude
            wf[off_time1_stop:opt_pulse_stop]  += self.eom_pulse_amplitude
            wf[opt_pulse_stop:overshoot1_stop] += self.eom_overshoot1
            wf[overshoot1_stop:overshoot2_stop]+= self.eom_overshoot2
            wf[opt_pulse_stop:off_time2_stop]  += self.eom_off_amplitude

            #compensation_pulse
            wf = np.append(wf,-wf)


        if channel == self.aom_channel:

            wf = np.zeros(len(tvals))

            pulse_start = np.where(tvals <= np.round(self.eom_off_duration-self.aom_risetime, 
                pulsar.SIGNIFICANT_DIGITS))[0][-1]
            pulse_stop  = np.where(tvals <= np.round(self.eom_off_duration + \
                            self.eom_pulse_duration + self.aom_risetime, 
                                pulsar.SIGNIFICANT_DIGITS))[0][-1]

            wf[pulse_start:pulse_stop] += self.aom_amplitude
            
        return wf


class EOMAOMPulse(pulse.Pulse):
    def __init__(self, name, eom_channel, aom_channel,  **kw):
        pulse.Pulse.__init__(self, name)
        self.eom_channel = eom_channel
        self.aom_channel = aom_channel

        self.channels = [eom_channel,aom_channel]
                                               
        self.eom_pulse_duration        = kw.pop('eom_pulse_duration'      ,2e-9) 
        self.eom_off_duration          = kw.pop('eom_off_duration'        ,150e-9)
        self.eom_off_amplitude         = kw.pop('eom_off_amplitude'       ,-.25)
        self.eom_pulse_amplitude       = kw.pop('eom_pulse_amplitude'     ,1.2)
        self.eom_overshoot_duration1   = kw.pop('eom_overshoot_duration1' ,10e-9)
        self.eom_overshoot1            = kw.pop('eom_overshoot1'          ,-0.03)
        self.eom_overshoot_duration2   = kw.pop('eom_overshoot_duration2' ,4e-9)
        self.eom_overshoot2            = kw.pop('eom_overshoot2'          ,-0.03)
        self.eom_comp_pulse_amplitude  = kw.pop('eom_comp_pulse_amplitude',self.eom_pulse_amplitude)
        self.eom_comp_pulse_duration   = kw.pop('eom_comp_pulse_duration' ,self.eom_pulse_duration)
        self.aom_risetime              = kw.pop('aom_risetime'            ,23e-9)
        self.aom_amplitude             = kw.pop('aom_amplitude'           ,1.0)

        self.start_offset   = self.eom_off_duration
        self.stop_offset    = 3*self.eom_off_duration+self.eom_pulse_duration
        self.length         = 4*self.eom_off_duration+2.*self.eom_pulse_duration                                      
        
    def __call__(self,  **kw):
        self.eom_pulse_duration        = kw.pop('eom_pulse_duration'      ,self.eom_pulse_duration) 
        self.eom_off_duration          = kw.pop('eom_off_duration'        ,self.eom_off_duration)
        self.eom_off_amplitude         = kw.pop('eom_off_amplitude'       ,self.eom_off_amplitude)
        self.eom_pulse_amplitude       = kw.pop('eom_pulse_amplitude'     ,self.eom_pulse_amplitude)
        self.eom_overshoot_duration1   = kw.pop('eom_overshoot_duration1' ,self.eom_overshoot_duration1)
        self.eom_overshoot1            = kw.pop('eom_overshoot1'          ,self.eom_overshoot1)
        self.eom_overshoot_duration2   = kw.pop('eom_overshoot_duration2' ,self.eom_overshoot_duration2)
        self.eom_overshoot2            = kw.pop('eom_overshoot2'          ,self.eom_overshoot2)
        self.eom_comp_pulse_amplitude  = kw.pop('eom_comp_pulse_amplitude',self.eom_pulse_amplitude)
        self.eom_comp_pulse_duration   = kw.pop('eom_comp_pulse_duration' ,self.eom_pulse_duration)
        self.aom_risetime              = kw.pop('aom_risetime'            ,self.aom_risetime)
        self.aom_amplitude             = kw.pop('aom_amplitude'           ,self.aom_amplitude )
        
        self.start_offset   = self.eom_off_duration
        self.stop_offset    = 3*self.eom_off_duration+self.eom_pulse_duration        
        self.length         = 4*self.eom_off_duration + 2*self.eom_pulse_duration

        return self
        
       
    def chan_wf(self, channel, tvals):
        
        tvals -= tvals[0]
        tvals = np.round(tvals, pulsar.SIGNIFICANT_DIGITS) 
        
        if channel == self.eom_channel:

            off_time1_start     = 0
            off_time1_stop      = np.where(tvals <= self.eom_off_duration)[0][-1]
            opt_pulse_stop      = np.where(tvals <= np.round(
                self.eom_off_duration+self.eom_pulse_duration, 
                    pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            overshoot1_stop     = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_pulse_duration + \
                                    self.eom_overshoot_duration1,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            overshoot2_stop     = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_pulse_duration + self.eom_overshoot_duration1 + \
                                    self.eom_overshoot_duration2,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            off_time2_stop      = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_pulse_duration + \
                                     self.eom_off_duration,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
    
            #print len(tvals)
            wf = np.zeros(len(tvals)/2)
            wf[off_time1_start:off_time1_stop] += self.eom_off_amplitude
            wf[off_time1_stop:opt_pulse_stop]  += self.eom_pulse_amplitude
            wf[opt_pulse_stop:overshoot1_stop] += self.eom_overshoot1
            wf[overshoot1_stop:overshoot2_stop]+= self.eom_overshoot2
            wf[opt_pulse_stop:off_time2_stop]  += self.eom_off_amplitude

            #compensation_pulse
             #compensation_pulse
            comp_wf = np.zeros(len(tvals)/2)

            comp_amp = (2*self.eom_off_duration * self.eom_off_amplitude + \
                            self.eom_comp_pulse_duration * self.eom_comp_pulse_amplitude + \
                            self.eom_overshoot_duration1 * self.eom_overshoot1 + \
                            self.eom_overshoot_duration2 * self.eom_overshoot2) / (2 * self.eom_off_duration)

            comp_wf -= comp_amp

            wf = np.append(wf,comp_wf)



        if channel == self.aom_channel:

            wf = np.zeros(len(tvals))

            pulse_start = np.where(tvals <= np.round(self.eom_off_duration-self.aom_risetime, 
                pulsar.SIGNIFICANT_DIGITS))[0][-1]
            pulse_stop  = np.where(tvals <= np.round(self.eom_off_duration + \
                            self.eom_pulse_duration + self.aom_risetime, 
                                pulsar.SIGNIFICANT_DIGITS))[0][-1]

            wf[pulse_start:pulse_stop] += self.aom_amplitude
            
        return wf
                
class EOMAOMPulse_step(pulse.Pulse):
    def __init__(self, name, eom_channel, aom_channel,  **kw):
        pulse.Pulse.__init__(self, name)
        self.eom_channel = eom_channel
        self.aom_channel = aom_channel

        self.channels = [eom_channel,aom_channel]
                                               
        self.eom_off_duration          = kw.pop('eom_off_duration'        ,100e-9)## we should try to make this shorter
        self.eom_off_amplitude         = kw.pop('eom_off_amplitude'       ,-.25)
        self.eom_off_2_amplitude       = kw.pop('eom_off_2_amplitude'     ,2.65)
        self.eom_overshoot_duration1   = kw.pop('eom_overshoot_duration1' ,10e-9)##check these
        self.eom_overshoot1            = kw.pop('eom_overshoot1'          ,0.03)##check these
        self.eom_overshoot_duration2   = kw.pop('eom_overshoot_duration2' ,4e-9)##check these
        self.eom_overshoot2            = kw.pop('eom_overshoot2'          ,0.03)##check these
        self.aom_risetime              = kw.pop('aom_risetime'            ,23e-9)
        self.aom_on                    = kw.pop('aom_on'                  ,True)

        self.start_offset   = self.eom_off_duration
        self.stop_offset    = 3*self.eom_off_duration
        self.length         = 4*self.eom_off_duration                                      
        
    def __call__(self,  **kw):
        self.eom_off_duration          = kw.pop('eom_off_duration'        ,self.eom_off_duration)
        self.eom_off_amplitude         = kw.pop('eom_off_amplitude'       ,self.eom_off_amplitude)
        self.eom_off_2_amplitude       = kw.pop('eom_off_2_amplitude'     ,self.eom_off_2_amplitude)
        self.eom_overshoot_duration1   = kw.pop('eom_overshoot_duration1' ,self.eom_overshoot_duration1)
        self.eom_overshoot1            = kw.pop('eom_overshoot1'          ,self.eom_overshoot1)
        self.eom_overshoot_duration2   = kw.pop('eom_overshoot_duration2' ,self.eom_overshoot_duration2)
        self.eom_overshoot2            = kw.pop('eom_overshoot2'          ,self.eom_overshoot2)
        self.aom_risetime              = kw.pop('aom_risetime'            ,self.aom_risetime)
        self.aom_on                    = kw.pop('aom_on'                  ,True)
        
        self.start_offset   = self.eom_off_duration
        self.stop_offset    = 3*self.eom_off_duration        
        self.length         = 4*self.eom_off_duration

        return self
        
    def chan_wf(self, channel, tvals):
        
        tvals -= tvals[0]
        tvals = np.round(tvals, pulsar.SIGNIFICANT_DIGITS) 
        
        if channel == self.eom_channel:

            off_time1_start     = 0
            off_time1_stop      = np.where(tvals <= self.eom_off_duration)[0][-1]
            
            overshoot1_stop     = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_overshoot_duration1,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            overshoot2_stop     = np.where(tvals <= np.round(self.eom_off_duration + \
                                    self.eom_overshoot_duration1 + \
                                    self.eom_overshoot_duration2,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            off_time2_stop      = np.where(tvals <= np.round(self.eom_off_duration + \
                                     self.eom_off_duration,
                                        pulsar.SIGNIFICANT_DIGITS))[0][-1]
    
            #print len(tvals)
            pulse_wf = np.zeros(len(tvals)/2)
            pulse_wf[off_time1_start:off_time1_stop] += self.eom_off_amplitude
            pulse_wf[off_time1_stop:overshoot1_stop] += self.eom_overshoot1
            pulse_wf[overshoot1_stop:overshoot2_stop]+= self.eom_overshoot2
            pulse_wf[off_time1_stop:off_time2_stop]  += self.eom_off_2_amplitude

            #compensation_pulse
            comp_wf = np.zeros(len(tvals)/2)

            comp_amp = (self.eom_off_duration * self.eom_off_amplitude + \
                            self.eom_off_duration * self.eom_off_2_amplitude + \
                            self.eom_overshoot_duration1 * self.eom_overshoot1 + \
                            self.eom_overshoot_duration2 * self.eom_overshoot2) / (2 * self.eom_off_duration)

            comp_wf -= comp_amp

            wf = np.append(pulse_wf,comp_wf)


        if channel == self.aom_channel:

            wf = np.zeros(len(tvals))

            pulse_start = np.where(tvals <= np.round(self.eom_off_duration-self.aom_risetime, 
                pulsar.SIGNIFICANT_DIGITS))[0][-1]
            pulse_stop  = np.where(tvals <= np.round(self.eom_off_duration + self.aom_risetime, 
                                pulsar.SIGNIFICANT_DIGITS))[0][-1]

            wf[pulse_start:pulse_stop] += 1*self.aom_on 
            
        return wf

class EOMAOMPulse_raymond_step(pulse.Pulse):
    def __init__(self, name, eom_channel, aom_channel, eom_trigger_channel, **kw):
        pulse.Pulse.__init__(self, name)
        self.eom_channel = eom_channel
        self.aom_channel = aom_channel
        self.eom_trigger_channel = eom_trigger_channel

        self.channels = [eom_channel,aom_channel,eom_trigger_channel]
                                               
        self.eom_pulse_duration        = kw.pop('eom_pulse_duration'      ,80e-9)
        self.eom_pulse_amplitude       = kw.pop('eom_pulse_amplitude'     ,3.0) 
        self.eom_comp_pulse_amplitude  = kw.pop('eom_comp_pulse_amplitude',0.25*self.eom_pulse_amplitude)

        self.eom_trigger_amplitude     = kw.pop('eom_trigger_amplitude'   ,1.0)
        self.aom_risetime              = kw.pop('aom_risetime'            ,23e-9)
        self.aom_amplitude             = kw.pop('aom_amplitude'           ,1.0)

        self.start_offset   = self.eom_pulse_duration
        self.stop_offset    = 4*self.eom_pulse_duration
        self.length         = 5*self.eom_pulse_duration
        
    def __call__(self,  **kw):
        return self
        
       
    def chan_wf(self, channel, tvals):

        tvals -= tvals[0]
        tvals = np.round(tvals, pulsar.SIGNIFICANT_DIGITS) 

        if channel == self.eom_trigger_channel:

            trigger_pulse_start = np.where(tvals <= self.eom_pulse_duration)[0][-1]
            trigger_pulse_stop = np.where(tvals <= 2.*self.eom_pulse_duration)[0][-1]

            wf = np.zeros(len(tvals))
            wf[trigger_pulse_start:trigger_pulse_stop] += self.eom_trigger_amplitude

        elif channel == self.eom_channel:

            opt_pulse1_start     = np.where(tvals <= np.round(0.5*self.eom_pulse_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
            opt_pulse1_stop      = np.where(tvals <= np.round(1.5*self.eom_pulse_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
            opt_pulse2_start     = np.where(tvals <= np.round(2.5*self.eom_pulse_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
            opt_pulse2_stop      = np.where(tvals <= np.round(4.5*self.eom_pulse_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
  
            #print len(tvals)
            wf = np.zeros(len(tvals))
            wf[opt_pulse1_start:opt_pulse1_stop] += self.eom_pulse_amplitude
            wf[opt_pulse2_start:opt_pulse2_stop] -= self.eom_comp_pulse_amplitude

        elif channel == self.aom_channel:

            wf = np.zeros(len(tvals))
            pulse_start     = np.where(tvals <= np.round(self.eom_pulse_duration-self.aom_risetime, \
                    pulsar.SIGNIFICANT_DIGITS))[0][-1]
            pulse_stop      = np.where(tvals <= np.round(self.eom_pulse_duration+self.aom_risetime, \
                    pulsar.SIGNIFICANT_DIGITS))[0][-1]

            wf[pulse_start:pulse_stop] += self.aom_amplitude
            
        return wf

class EOMAOMPulse_raymond_pulse(pulse.Pulse):
    def __init__(self, name, eom_channel, aom_channel, eom_trigger_channel, **kw):
        pulse.Pulse.__init__(self, name)
        self.eom_channel = eom_channel
        self.aom_channel = aom_channel
        self.eom_trigger_channel = eom_trigger_channel

        self.channels = [eom_channel,aom_channel,eom_trigger_channel]
                                               
        self.eom_pulse_duration        = kw.pop('eom_pulse_duration'      ,50e-9)
        self.eom_pulse_amplitude       = kw.pop('eom_pulse_amplitude'     ,1.45) 

        self.eom_trigger_duration      = kw.pop('eom_trigger_eom_trigger_duration'  ,60e-9)
        self.eom_trigger_amplitude     = kw.pop('eom_trigger_amplitude'             ,1.0)
        self.eom_trigger_pulse_duration= kw.pop('eom_trigger_pulse_duration'        ,1e-9)
        self.aom_risetime              = kw.pop('aom_risetime'                      ,23e-9)
        self.aom_amplitude             = kw.pop('aom_amplitude'                     ,1.0)
        
        self.eom_comp_pulse_amplitude  = kw.pop('eom_comp_pulse_amplitude',\
                self.eom_pulse_amplitude*self.eom_trigger_pulse_duration/self.eom_pulse_duration)

        self.start_offset   = self.eom_trigger_duration
        self.stop_offset    = 3*self.eom_trigger_duration
        self.length         = 4*self.eom_trigger_duration + 2*self.eom_trigger_pulse_duration
        
    def __call__(self,  **kw):
        return self
        
       
    def chan_wf(self, channel, tvals):

        tvals -= tvals[0]
        tvals = np.round(tvals, pulsar.SIGNIFICANT_DIGITS) 
        
        if channel == self.eom_trigger_channel:

            trigger1_pulse_start = 0
            trigger1_pulse_stop  = np.where(tvals <= np.round(self.eom_trigger_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
            print len(tvals), trigger1_pulse_stop
            trigger2_pulse_start = np.where(tvals <= np.round(self.eom_trigger_duration + self.eom_trigger_pulse_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
            
            wf = np.zeros(len(tvals)/2)
            wf[trigger1_pulse_start:trigger1_pulse_stop] += self.eom_trigger_amplitude
            wf[trigger2_pulse_start:] += self.eom_trigger_amplitude

            wf=np.append(wf,np.zeros(len(tvals)/2))

        elif channel == self.eom_channel:

            opt_pulse_start     = np.where(tvals <= np.round(self.eom_trigger_duration+\
                    0.5*self.eom_trigger_pulse_duration-0.5*self.eom_pulse_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
            opt_pulse_stop      = np.where(tvals <= np.round(self.eom_trigger_duration+\
                    0.5*self.eom_trigger_pulse_duration+0.5*self.eom_pulse_duration,pulsar.SIGNIFICANT_DIGITS))[0][-1]
  
            #print len(tvals)
            wf = np.zeros(len(tvals)/2)
            wf[opt_pulse_start:opt_pulse_stop] += self.eom_pulse_amplitude

             #compensation_pulse
            comp_wf = np.zeros(len(tvals)/2)
            comp_wf[opt_pulse_start:opt_pulse_stop] -= self.eom_comp_pulse_amplitude

            wf = np.append(wf,comp_wf)

        elif channel == self.aom_channel:

            wf = np.zeros(len(tvals))
            pulse_start     = np.where(tvals <= np.round(self.eom_trigger_duration-self.aom_risetime, \
                    pulsar.SIGNIFICANT_DIGITS))[0][-1]
            pulse_stop      = np.where(tvals <= np.round(self.eom_trigger_duration+self.eom_trigger_pulse_duration\
                    +self.aom_risetime,pulsar.SIGNIFICANT_DIGITS))[0][-1]

            wf[pulse_start:pulse_stop] += self.aom_amplitude
            
        return wf