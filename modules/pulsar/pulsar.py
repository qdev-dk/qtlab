# Authors:
# Bas Hensen <B.J.Hensen@tudelft.nl>
# Gijs de Lange - TNW <G.deLange@tudelft.nl>
# Wolfgang Pfaff <wolfgangpfff@googlemail.com>
# this module contains the sequencer and sequence classes

# TODO this would be nice to have also accessible from clients.
# should therefore be a SharedObject
# TODO in principle that could be generalized for other
# sequencing hardware i guess

import time
import numpy as np
import logging

# some pulses use rounding when determining the correct sample at which to insert a particular
# value. this might require correct rounding -- the pulses are typically specified on short time
# scales, but the time unit we use is seconds. therefore we need a suitably chosen digit on which
# to round. 9 would round a pulse to 1 ns precision. 11 is 10 ps, and therefore probably beyond
# the lifetime of this code (no 10ps AWG available yet :))
SIGNIFICANT_DIGITS = 11

class Pulsar:
    """
    This is the object that communicates with the AWG.
    """

    AWG = None
    AWG_type = 'regular' # other option at this point is 'opt09'
    clock = 1e9
    channel_ids = ['ch1', 'ch1_marker1', 'ch1_marker2',
        'ch2', 'ch2_marker1', 'ch2_marker2',
        'ch3', 'ch3_marker1', 'ch3_marker2',
        'ch3', 'ch3_marker1', 'ch3_marker2' ]
    AWG_sequence_cfg={}

    def __init__(self):
        self.channels = {}

    ### channel handling
    def define_channel(self, id, name, type, delay, offset,
            high, low, active, skew=0):

        _doubles = []
        for c in self.channels:
            if self.channels[c]['id'] == id:
                logging.warning(
                    "Channel '%s' already in use, will overwrite." % id)
                _doubles.append(c)
        for c in _doubles:
            del self.channels[c]

        self.channels[name] = {
            'id' : id,
            'type' : type,
            'delay' : delay,
            'offset' : offset,
            'high' : high,
            'low' : low,
            'active' : active,
            'skew'   : skew,
            }

    def set_channel_opt(self, name, option, value):
        self.channels[name][option] = value

    def get_subchannels(self, id):
        return [id[:3], id[:3]+'_marker1', id[:3]+'_marker2']

    def get_channel_names_by_id(self, id):
        chans = {id : None, id+'_marker1' : None, id+'_marker2' : None}

        for c in self.channels:
            if self.channels[c]['id'] in chans:
                chans[self.channels[c]['id']] = c

        return chans

    def get_channel_name_by_id(self, id):
        chan = None

        for c in self.channels:
            if self.channels[c]['id'] == id:
                return c

    def get_used_subchannel_ids(self, all_subchannels=True):
        chans = []

        for c in self.channels:
            if self.channels[c]['active'] and \
                self.channels[c]['id'] not in chans:

                if all_subchannels:
                    [ chans.append(id) for id in \
                        self.get_subchannels(self.channels[c]['id'])]
                else:
                    chans.append(self.channels[c]['id'])

        return chans

    def get_used_channel_ids(self):
        chans = []

        for c in self.channels:
            if self.channels[c]['active'] and \
                self.channels[c]['id'][:3] not in chans:

                chans.append(self.channels[c]['id'][:3])

        return chans

    def setup_channels(self, output=False, reset_unused=True):
        for n in self.channel_ids:
            getattr(self.AWG, 'set_%s_status' % n[:3])('off')

        if reset_unused:
            for n in self.channel_ids:
                if 'marker' in n:
                    getattr(self.AWG, 'set_%s_low' % n)(0)
                    getattr(self.AWG, 'set_%s_high' % n)(1)
                else:
                    getattr(self.AWG, 'set_%s_amplitude' % n)(2.)
                    getattr(self.AWG, 'set_%s_offset' % n)(0.)

        for c in self.channels:
            n = self.channels[c]['id']

            # set correct bounds
            if self.channels[c]['type'] == 'analog':
                a = self.channels[c]['high'] - self.channels[c]['low']
                o = (self.channels[c]['high'] + self.channels[c]['low'])/2.
                getattr(self.AWG, 'set_%s_amplitude' % n)(a)
                getattr(self.AWG, 'set_%s_offset' % n)(o)
            elif self.channels[c]['type'] == 'marker':
                getattr(self.AWG, 'set_%s_low' % n)(self.channels[c]['low'])
                getattr(self.AWG, 'set_%s_high' % n)(self.channels[c]['high'])

            # turn on the used channels
            if output and self.channels[c]['active']:
                getattr(self.AWG, 'set_%s_status' % n[:3])('on')

    def activate_channels(self, channels='all'):
        ids = self.get_used_channel_ids()
        #print ids
        for id in ids:
            output = False
            names = self.get_channel_names_by_id(id)
            for sid in names:
                #print sid
                if names[sid] == None:
                    continue

                if channels != 'all' and names[sid] not in channels:
                    continue

                if self.channels[names[sid]]['active']:
                    output = True

            if output:
                getattr(self.AWG, 'set_%s_status' % id)('on')

    def get_awg_channel_cfg(self):
        channel_cfg={}

        for c in self.channels:
            n = self.channels[c]['id']
            if self.channels[c]['type'] == 'analog':
                channel_cfg['ANALOG_METHOD_%s' %n[-1]] = 1
                a = self.channels[c]['high'] - self.channels[c]['low']
                o = (self.channels[c]['high'] + self.channels[c]['low'])/2.
                channel_cfg['ANALOG_AMPLITUDE_%s' %n[-1]] = a
                channel_cfg['ANALOG_OFFSET_%s' %n[-1]] = o
                channel_cfg['CHANNEL_SKEW_%s' %n[-1]] = self.channels[c]['skew']
            elif self.channels[c]['type'] == 'marker':
                channel_cfg['MARKER1_METHOD_%s'%n[2]] = 2
                channel_cfg['MARKER2_METHOD_%s'%n[2]] = 2
                channel_cfg['MARKER%s_LOW_%s'%(n[-1],n[2])] = self.channels[c]['low']
                channel_cfg['MARKER%s_HIGH_%s'%(n[-1],n[2])] = self.channels[c]['high']
                channel_cfg['MARKER%s_SKEW_%s'%(n[-1],n[2])] = self.channels[c]['skew']
            #elif self.channels[c]['type'] == 'dc':
            #    channel_cfg['DC_OUTPUT_LEVEL_%s'%n[-1]] = self.channels[c]['level']

            # activate the used channels
            if  self.channels[c]['active']:
                channel_cfg['CHANNEL_STATE_%s' %n[-1]] = 1
            else:
                channel_cfg['CHANNEL_STATE_%s' %n[-1]] = 0
        return channel_cfg


    ### waveform/file handling
    def delete_all_waveforms(self):
        self.AWG.delete_all_waveforms_from_list()

    # i don't know what this function does...
    # def clear_waveforms(self):
    #   self.AWG.clear_waveforms()

    def upload(self, *elements, **kw):
        verbose = kw.pop('verbose', True)
        channels = kw.pop('channels', 'all')

        _t0 = time.time()
        elt_cnt = len(elements)

        if verbose:
            "Generate/upload %d elements: " % elt_cnt

        for i,e in enumerate(elements):
            if verbose:
                print "%d / %d: %s (%d samples)... " % \
                    (i+1,elt_cnt, e.name, e.samples())

            self.upload_element(e, verbose=False, channels=channels)

        _t = time.time() - _t0
        if verbose:
            print "Upload finished in %.2f seconds." % _t
            print


    def upload_element(self, element, verbose=True, channels='all'):
        if verbose:
            print "Generate/upload '%s' (%d samples)... " \
                % (element.name, element.samples()),

        _t0 = time.time()

        tvals, wfs = element.normalized_waveforms()
        chan_ids = self.get_used_channel_ids()

        # order the waveforms according to physical AWG channels and
        # make empty sequences where necessary
        for id in chan_ids:
            wfname = element.name + '_%s' % id

            # determine if we actually want to upload this channel
            upload = False
            if channels == 'all':
                upload = True
            else:
                for c in channels:
                    if self.channels[c]['id'][:3] == id:
                        upload = True
                if not upload:
                    continue

            chan_wfs = {id : None, id+'_marker1' : None,
                id+'_marker2' : None }
            grp = self.get_channel_names_by_id(id)

            for sid in grp:
                if grp[sid] != None and grp[sid] in wfs:
                    chan_wfs[sid] = wfs[grp[sid]]
                else:
                    chan_wfs[sid] = np.zeros(element.samples())

            # upload to AWG
            self.AWG.send_waveform(chan_wfs[id], chan_wfs[id+'_marker1'],
                chan_wfs[id+'_marker2'], wfname)#, self.clock)#here is wehere gijs' code comes in!
            self.AWG.import_waveform_file(wfname, wfname, type='wfm')

        _t = time.time() - _t0

        if verbose:
            print "finished in %.2f seconds." % _t

    ### sequence handling
    def program_sequence(self, sequence, channels='all', loop=True,
            start=False):

        _t0 = time.time()

        print "Programming '%s' (%d element(s))..." \
            % (sequence.name, sequence.element_count()),

        # determine which channels are involved in the sequence
        if channels  == 'all':
            chan_ids = self.get_used_channel_ids()
        else:
            chan_ids = []
            for c in channels:
                if self.channels[c]['id'][:3] not in chan_ids:
                    chan_ids.append(self.channels[c]['id'][:3])

        # prepare the awg
        self.AWG.stop()
        self.AWG.set_runmode('SEQ')

        self.AWG.set_event_jump_timing('SYNC' if self.AWG_sequence_cfg['JUMP_TIMING'] == 1 else 'ASYNC')
        self.setup_channels()

        # this clears all element properties so we're sure not to
        # keep any jumping, goto, etc. properties
        self.AWG.set_sq_length(0)

        self.AWG.set_sq_length(sequence.element_count())

        # set all the waveforms
        for i,elt in enumerate(sequence.elements):
            idx = i+1
            for id in chan_ids:
                chanidx = int(id[2])

                wf = elt['wfname'] + '_%s' % id
                self.AWG.set_sqel_waveform(wf, chanidx, idx)

            self.AWG.set_sqel_loopcnt_to_inf(idx, False)
            self.AWG.set_sqel_loopcnt(elt['repetitions'], idx)

            if elt['goto_target'] != None:
                self.AWG.set_sqel_goto_state(idx, '1')
                self.AWG.set_sqel_goto_target_index(idx,
                    sequence.element_index(elt['goto_target']))
            # else:
            #    self.AWG.set_sqel_goto_state(idx, '0')

            if elt['jump_target'] != None:
                self.AWG.set_sqel_event_jump_type(idx, 'IND')
                self.AWG.set_sqel_event_jump_target_index(idx,
                    sequence.element_index(elt['jump_target']))
            # else:


            if elt['trigger_wait']:
                self.AWG.set_sqel_trigger_wait(idx, 1)

        if loop:
            self.AWG.set_sqel_goto_state(idx, '1')
            self.AWG.set_sqel_goto_target_index(idx, 1)

        # turn on the channel output
        self.activate_channels(channels)

        # setting jump modes and loading the djump table
        if sequence.djump_table != None and self.AWG_type not in ['opt09']:
            raise Exception('The AWG configured does not support dynamic jumping')

        if self.AWG_type in ['opt09']:
            if sequence.djump_table != None:
                self.AWG.set_event_jump_mode('DJUM')
                print 'AWG set to dynamical jump'

                for i in range(16):
                    self.AWG.set_djump_def(i, 0)

                for i in sequence.djump_table.keys():
                    el_idx = sequence.element_index(sequence.djump_table[i])
                    self.AWG.set_djump_def(i, el_idx)

            else:
                self.AWG.set_event_jump_mode('EJUM')
                print 'AWG set to event jump'

        if start:
            self.AWG.start()

        _t = time.time() - _t0
        print " finished in %.2f seconds." % _t
        print

    def program_awg(self, sequence, *elements, **kw):


        """
        Upload a single file to the AWG (.awg) which contains all waveforms AND sequence information (i.e. nr of repetitions, event jumps etc)
        this should combine two functions previously known as pulsar.upload_sequence and pulsar.program_sequence. Advantage is that it's much faster,
        since sequence information is sent to the AWG in a single file.

        """
        verbose=kw.pop('verbose',False)

        debug=kw.pop('debug', False)
        channels=kw.pop('channels','all')
        loop=kw.pop('loop',True)
        allow_non_zero_first_point_on_trigger_wait=kw.pop('allow_first_zero',False)
        elt_cnt = len(elements)
        chan_ids = self.get_used_channel_ids()
        packed_waveforms={}

        elements_with_non_zero_first_points=[]

        # order the waveforms according to physical AWG channels and
        # make empty sequences where necessary
        for i,element in enumerate(elements):
            if verbose==True:
                print "%d / %d: %s (%d samples)... " % \
                    (i+1,elt_cnt, element.name, element.samples())

            if verbose:
                print "Generate/upload '%s' (%d samples)... " \
                    % (element.name, element.samples()),
            _t0 = time.time()

            tvals, wfs = element.normalized_waveforms()
            for id in chan_ids:
                wfname = element.name + '_%s' % id

                # determine if we actually want to upload this channel
                upload = False
                if channels == 'all':
                    upload = True
                else:
                    for c in channels:
                        if self.channels[c]['id'][:3] == id:
                            upload = True
                    if not upload:
                        continue

                chan_wfs = {id : None, id+'_marker1' : None,
                    id+'_marker2' : None }
                grp = self.get_channel_names_by_id(id)

                for sid in grp:
                    if grp[sid] != None and grp[sid] in wfs:
                        chan_wfs[sid] = wfs[grp[sid]]
                        if chan_wfs[sid][0]!=0.:
                            elements_with_non_zero_first_points.append(element.name)
                    else:
                        chan_wfs[sid] = np.zeros(element.samples())

                # Create wform files
                packed_waveforms[wfname]=self.AWG.pack_waveform(chan_wfs[id],chan_wfs[id+'_marker1'],chan_wfs[id+'_marker2'])


        _t = time.time() - _t0

        if verbose:
            print "finished in %.2f seconds." % _t

        #sequence programming ----------------------------------------------------------

        _t0 = time.time()
        if sequence.element_count() >8000:
            print "Error: trying to program '%s' (%d element(s))...\n Sequence contains more than 8000 elements, Aborting" \
                % (sequence.name, sequence.element_count()),
            return 


        print "Programming '%s' (%d element(s))...\n" \
            % (sequence.name, sequence.element_count()),

        # determine which channels are involved in the sequence
        if channels  == 'all':
            chan_ids = self.get_used_channel_ids()
        else:
            chan_ids = []
            for c in channels:
                if self.channels[c]['id'][:3] not in chan_ids:
                    chan_ids.append(self.channels[c]['id'][:3])

        #Create lists with sequence information:
        #wfname_l = list of waveform names [[wf1_ch1,wf2_ch1..],[wf1_ch2,wf2_ch2..],...]
        #nrep_l = list specifying the number of reps for each seq element
        #wait_l = idem for wait_trigger_state
        #goto_l = idem for goto_state (goto is the element where it hops to in case the element is finished)

        wfname_l=[]
        nrep_l=[]
        wait_l=[]
        goto_l=[]
        logic_jump_l=[]

        for id in chan_ids:
        # set all the waveforms
            el_wfnames=[]
            #add all wf names of channel
            for elt in sequence.elements:
                el_wfnames.append(elt['wfname'] + '_%s' % id) #  should the name include id nr?

            wfname_l.append(el_wfnames)

        for elt in sequence.elements:

            nrep_l.append(elt['repetitions'])
            if elt['goto_target'] != None:
                goto_l.append(sequence.element_index(elt['goto_target']))
            else:
                goto_l.append(0)
            if elt['jump_target'] != None:
                logic_jump_l.append(sequence.element_index(elt['jump_target']))
            else:
                logic_jump_l.append(0)
            if elt['trigger_wait']:
                wait_l.append(1)
                #if (elt['wfname'] in elements_with_non_zero_first_points) and not(allow_non_zero_first_point_on_trigger_wait):
                    #print 'warning Trigger wait set for element with a non-zero first point'
                    #raise Exception('pulsar: Trigger wait set for element {} with a non-zero first point'.format(elt['wfname']))
            else:
                wait_l.append(0)

        if loop:
            goto_l[-1]=1

         # setting jump modes and loading the djump table
        if sequence.djump_table != None and self.AWG_type not in ['opt09']:
            raise Exception('pulsar: The AWG configured does not support dynamic jumping')

        if self.AWG_type in ['opt09']:
            if sequence.djump_table != None:
                #self.AWG.set_event_jump_mode('DJUM')
                self.AWG_sequence_cfg['EVENT_JUMP_MODE'] = 2 #DYNAMIC JUMP
                print 'AWG set to dynamical jump'
                awg_djump_table = np.zeros(16, dtype='l')
                for i in sequence.djump_table.keys():
                    el_idx = sequence.element_index(sequence.djump_table[i])
                    awg_djump_table[i] = el_idx
                self.AWG_sequence_cfg['TABLE_JUMP_DEFINITION'] = awg_djump_table

            else:
                self.AWG_sequence_cfg['EVENT_JUMP_MODE'] = 1 #EVENT JUMP
       #       print 'AWG set to event jump'
        if debug==True:
            self.check_sequence_consistency(packed_waveforms,
                                            wfname_l,
                                            nrep_l, wait_l, goto_l, logic_jump_l)

        filename = sequence.name+'_FILE.AWG'
        awg_file=self.AWG.generate_awg_file(packed_waveforms,
                                            np.array(wfname_l),
                                            nrep_l, wait_l, goto_l, logic_jump_l,
                                            self.get_awg_channel_cfg(),
                                            self.AWG_sequence_cfg)
        self.AWG.send_awg_file(filename,awg_file)

        self.AWG.load_awg_file(filename)

        self.activate_channels(channels)



        _t = time.time() - _t0
        print " finished in %.2f seconds." % _t
        print

    def check_sequence_consistency(self, packed_waveforms,
                                            wfname_l,
                                            nrep_l, wait_l, goto_l, logic_jump_l):
        if not len(wfname_l[0])==len(wfname_l[1])==len(wfname_l[2])==len(wfname_l[3])==len(nrep_l)==len(wait_l)==len(goto_l)==len(logic_jump_l):
            raise Exception('pulsar: sequence list of elements/properties has unequal length')

        ch=0
        for ch_wf in wfname_l:
            ch+=1
            el=0
            for wfname in ch_wf:
                el+=1
                if wfname not in packed_waveforms.keys():
                    raise Exception('pulsar: waveform name '+ wfname + ' , in position ' + str(el) + ' , channel ' + str(ch) + ' does not exist in waveform dictionary')

class Sequence:
    """
    Class that contains a sequence.
    A sequence is defined as a series of Elements that are given
    certain properties, such as repetition and jump events.

    We keep this independent of element generation here.
    Elements are simply referred to by name, the task to ensure
    they are available lies with the Pulsar.
    """

    def __init__(self, name):
        self.name = name

        self.elements = []

        self.djump_table = None

    def _make_element_spec(self, name, wfname, repetitions, goto_target,
            jump_target, trigger_wait):

        elt = {
            'name' : name,
            'wfname' : wfname,
            'repetitions' : repetitions,
            'goto_target' : goto_target,
            'jump_target' : jump_target,
            'trigger_wait' : trigger_wait,
            }
        return elt

    def insert_element(self, name, wfname, pos=None, repetitions=1,
            goto_target=None, jump_target=None, trigger_wait=False):

        for elt in self.elements:
            if elt['name'] == name:
                print 'insert_element'
                print name
                print 'Sequence names must be unique. Not added.'
                return False

        elt = self._make_element_spec(name, wfname, repetitions, goto_target,
            jump_target, trigger_wait)

        if pos == None:
            pos = len(self.elements)
        self.elements.insert(pos, elt)
        return True

    def append(self, name, wfname, **kw):
        '''
        Takes name wfname and other arguments as input. Does not take an element as input
        '''
        self.insert_element(name, wfname, pos=len(self.elements), **kw)

    def element_count(self):
        return len(self.elements)

    def element_index(self, name, start_idx=1):
        names = [self.elements[i]['name'] for i in range(len(self.elements))]
        return names.index(name)+start_idx

    def set_djump(self, state):
        if state==True:
            #if program_sequence gets a djump_table it will set the AWG later to DJUM
            self.djump_table = {}

        if state==False:
            self.djump_table = None
        return True

    def add_djump_address(self, pattern, name):
        #name should be the name of the element and pattern the bit address
        self.djump_table[pattern] = name
        return True

    def append_element(self, element, pos = None):
        '''
        Differs from normal append that it takes an element as input and not the arguments to make an element
        '''
        for elt in self.elements:
            if elt['name'] == element['name']:
                print 'append_element'
                print element['name']
                print 'Sequence names must be unique. Not added.'
                return False
        if pos == None:
            pos = len(self.elements)
        self.elements.insert(pos, element)
        return True



