import numpy as np
import qt
import plot
import logging

x = np.arange(-10, 10, 0.2)
y = np.sinc(x)

p = plot.get_plot('sinc function plot')
p = p.get_plot()

p.clear()

p.add_trace(x, y,
            lines=True,
            points=True,
            color='blue',
            title='sinc(x)')
# See p.add_trace? for a complete list of options

p.set_grid(True)
p.set_xlabel('X value [radians]')
p.set_ylabel('Y value')

# Add another curve to the plot, on the right axis
y2 = np.cos(x) *10
p.add_trace(x, y2, color='red', title='cos(x)', right=True)
p.set_y2range(-25, 15)
p.set_y2label('Y2 value')

# Adjust x and y range
p.set_xrange(-11, 11)
p.set_yrange(-0.3, 1.1)

# Nothing is actually generated before you call this!
p.update()

# This reopens the plot, if you closed it
p.run()

logging.info('Output of the plot is stored in: %s', p.get_output_dir())



# You can also plot Data objects directly.

# Note about plotting:
#
# You can produce "live" plots of data with syntax like this:
# p = plot.get_plot('test measurement live plot',
#                   replace_if_exists=True)
# p.add_data(data) # where data is a qt.Data object
# p.set_default_labels()
#
# In general however, it's better to plot your data in
# an entirely separate process from the main qtlab instance
# controlling your measurement hardware.
#
# This allows you to change your plotting routine while
# your measurement is still running. It also makes sure
# that your measurement process doesn't get killed by
# the operating system if you accidentally plot enormous
# datasets that hog too much memory.
#
# See plotting examples and the "dataview" example.

d = qt.Data('test data')
d.add_coordinate('frequency', units='s')
d.add_value('amplitude', units='V')

p_data_object = plot.get_plot(name='data object plotting')
p_data_object.add_data(d)
p_data_object.set_default_labels()

# The plot is automatically updated as you add points (see plot.get_plot? for options)
d.add_data_point(x, y)
