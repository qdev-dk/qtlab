# Authors:
# Bas Hensen <B.J.Hensen@tudelft.nl>
# Gijs de Lange - TNW <G.deLange@tudelft.nl>
# Wolfgang Pfaff <wolfgangpfff@googlemail.com>
import qt
import numpy as np

import pulsar
import pulse
import element
import pprint

reload(pulse)
reload(element)
reload(pulsar)


test_element = element.Element(				# Implementation of a sequence element.     
					'a test element',   	# Basic idea: add different pulses, and compose the actual numeric
					pulsar=qt.pulsar) 		# arrays that form the amplitudes for the hardware (typically an AWG).



# we copied the channel definition from out global pulsar
print 'Channel definitions: '
pprint.pprint(test_element._channels)
print 



# Define some bogus pulses.
sin_pulse 		= pulse.SinePulse(
					channel='RF', 
					name='A sine pulse on RF')

sq_pulse 		= pulse.SquarePulse(
					channel='MW_pulsemod', 
    				name='A square pulse on MW pmod')

special_pulse 	= pulse.SinePulse(
					channel='RF', 
					name='special pulse')

# Set properties of special pulse
special_pulse.amplitude = 0.2
special_pulse.length 	= 2e-6
special_pulse.frequency = 10e6
special_pulse.phase 	= 0



# create a few of those
test_element.add(				# Add oulse to the sequence element
	pulse.cp(					# create a copy of the pulse, configure it by given arguments (using the call method of the pulse class), and return the copy
		sin_pulse,
		frequency=1e6,
		amplitude=1,
		length=1e-6), 
    	name='first pulse') 	# name of sequence

test_element.add(
	pulse.cp(
		sq_pulse, 
		amplitude=1, 
		length=1e-6), 
		name='second pulse',
		refpulse='first pulse', # reference to second pulse where this pulse is to be mouted
		refpoint='end')			# point of mount, end appends the second pulse to the first pulse

test_element.add(
	pulse.cp(
		sin_pulse,
		frequency=2e6,
		amplitude=0.5,
		length=1e-6), 
		name='third pulse',
		refpulse='second pulse',
		refpoint='end')


# Show element overview
print 'Element overview:'
test_element.print_overview()
print 


# Create another sequence element
special_element = element.Element(name='Another element', pulsar=qt.pulsar)
special_element.add(special_pulse)

# upload waveforms
qt.pulsar.upload(test_element, special_element)

# Create the sequence
# note that we re-use the same waveforms (just with different identifier
# names)
seq = pulsar.Sequence('A Sequence')

seq.append(
	name='first element', 
	wfname='a test element', 
	trigger_wait=True, 
    goto_target='first element', 
    jump_target='first special element')

seq.append(
	name='first special element', 
	wfname='Another element', 
    repetitions=5)

seq.append(
	name='third element', 
	wfname='a test element', 
	trigger_wait=True,
    goto_target='third element', 
    jump_target='second special element')

seq.append(
	name='second special element', 
	wfname='Another element', 
    repetitions=5)

# program the Sequence onto awg
pulsar.program_sequence(seq)