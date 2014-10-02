# plot.py, abstract plotting classes
# Reinier Heeres <reinier@heeres.eu>
# Pieter de Groot <pieterdegroot@gmail.com>
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

import gobject
import logging
import os
import time
import types
import numpy

from lib.config import get_config
config = get_config()

from data import Data
from lib import namedlist
from lib.misc import get_dict_keys
from lib.network.object_sharer import SharedGObject, cache_result
from plotbridge.plotbridge import Plot as plotbridge_plot

def _convert_arrays(args):
    args = list(args)
    for i in range(len(args)):
        if type(args[i]) in (types.ListType, types.TupleType):
            args[i] = numpy.array(args[i])
    return args

class _PlotList(namedlist.NamedList):
    def __init__(self):
        namedlist.NamedList.__init__(self, base_name='plot')

    def add(self, name, item):
        '''Add an item to the list.'''
        if name in self._list:
            self.remove(name, send_quit=False)
        self._list[name] = item
        self._last_item = item
        self.emit('item-added', name)

    def remove(self, name, send_quit=True):
        '''Remove a plot (should be cleared and closed).'''
        if name in self:
            self[name].clear()
            if send_quit:
                self[name].quit()
        namedlist.NamedList.remove(self, name)

class Plot(SharedGObject):
    '''
    Class for plotting Data objects.

    This is a thin wrapper around plot_engines/plotbridge.py
    and mainly adds (some degree of) backward compatibility
    and the possibility to have your plot automatically
    update as new data is added to the Data object.

    To customize the plot, use the get_plot() function, which
    returns the underlying plotbridge object.
    Some functions (e.g. set_xlabel) are provided in this class
    for backward compatibility.

    If you are not plotting Data objects (i.e. just numpy arrays),
    you should use plotbridge directly.
    '''

    _plot_list = _PlotList()

    def __init__(self, *args, **kwargs):
        '''
        Create a plot object.

        args input:
            data objects (Data)

        kwargs input:
            name (string)           --- default 'plot<n>'
            mintime (int, seconds)  --- min time between autoupdates, default 1
            autoupdate (bool)       --- update the plot when data points added, default True
            template (string)       --- default 'gnuplot_2d' ('gnuplot_3d') for 2D (3D) plots
            output_dir (string)     --- directory for storing the plot. default '.'
            run (bool)              --- whether the plot script should be immediately ran (opened)
            coorddim (int or        --- index (indices) of the data column(s)
                      [int,int])        used as x (x,y) coordinate(s) for a 1D (2D) plot,
                                        default 0.
            valdim (int),           --- index of the data column used as the y (z)
                                        coordinate for a 1D (2D) plot.
         '''

        mintime = kwargs.pop('mintime', 1)
        autoupdate = kwargs.pop('autoupdate', True)
        template = kwargs.pop('template', 'gnuplot_2d')
        run = kwargs.pop('run', True)
        output_dir = kwargs.pop('output_dir', '.')
        coorddim = kwargs.pop('coorddim', [0])
        valdim = kwargs.pop('valdim', [1])
        name = kwargs.pop('name', '')
        if len(kwargs) > 0: logging.warn('Deprecated arguments ignored: %s' % str(kwargs.keys()))

        self._name = Plot._plot_list.new_item_name(self, name)

        SharedGObject.__init__(self, 'plot_%s' % self._name, replace=True)


        self._data = []

        self._mintime = mintime
        self._autoupdate = autoupdate

        self._last_update = 0
        self._update_hid = None

        self._pltbr = plotbridge_plot(name=self._name, template=template,
                                          output_dir=output_dir, overwrite=True)

        data_args = get_dict_keys(kwargs, ('coorddim', 'coorddims', 'valdim',
            'title', 'offset', 'ofs', 'traceofs', 'surfofs'))
        data_args['update'] = False
        data_args['setlabels'] = False
        self.add(*args, **data_args)

        Plot._plot_list.add(self._name, self)

        if run:
          self._pltbr.run(interactive=True)

    def get_plot(self):
      ''' Returns the underlying plotbridge object. Useful for customizing plot options. '''
      return self._pltbr

    def get_name(self):
        '''Get plot name.'''
        return self._name

    def add_data(self, data, **kwargs):
        '''Add a Data class with options to the plot list.'''

        # Extract options that apply to the global plot
        plot_opts = self._ADD_DATA_PLOT_OPTS & set(kwargs.keys())
        for key in plot_opts:
            val = kwargs.pop(key)
            self.set_property(key, val)

        if len(kwargs) > 0: logging.warn('Deprecated arguments ignored: %s' % str(kwargs.keys()))

        kwargs['data'] = data
        kwargs['new-data-point-hid'] = \
                data.connect('new-data-point', self._new_data_point_cb)
        kwargs['new-data-block-hid'] = \
                data.connect('new-data-block', self._new_data_block_cb)

        if 'title' not in kwargs:
            coorddims = kwargs['coorddims']
            valdim = kwargs['valdim']
            kwargs['title'] = data.get_title(coorddims, valdim)

        # Enable y2tics if plotting or right axis and not explicitly disabled
        if kwargs.get('right', False):
            if self.get_property('y2tics', None) is None:
                self.set_property('y2tics', True)

        self._data.append(kwargs)

    def set_mintime(self, t):
        self._mintime = t

    def get_mintime(self):
        return self._mintime

    def is_busy(self):
      ''' Deprecated: plotbridge is non-blocking. '''
      return False

    def clear(self):
        return self._pltbr.clear(update=True)

    def reset(self):
        self._pltbr.reset_options()

    def update(self, force=True, **kwargs):
        '''
        Update the plot.

        Input:
            force (bool): if True force an update, else check whether we
                would like to autoupdate and whether the last update is longer
                than 'mintime' ago.
        '''

        dt = time.time() - self._last_update

        if not force and self._autoupdate is not None and not self._autoupdate:
            return

        if self._update_hid is not None:
            if force:
                gobject.source_remove(self._update_hid)
                self._update_hid = None
            else:
                return

        cfgau = config.get('live-plot', True)
        if force or (cfgau and dt > self._mintime):
            if self.is_busy():
                self._queue_update(force=force, **kwargs)
                return

            self._last_update = time.time()
            self._do_update(**kwargs)

        # Auto-update later
        elif cfgau:
            self._queue_update(force=force, **kwargs)

    def _do_update(self):
        self._pltbr.update()

    def _queue_update(self, force=False, **kwargs):
        if self._update_hid is not None:
            return
        self._update_hid = gobject.timeout_add(int(self._mintime * 1000),
                self._delayed_update, force, **kwargs)

    def _delayed_update(self, force=True, **kwargs):
        self._update_hid = None
        self.update(force=force, **kwargs)
        return False

    def _new_data_point_cb(self, sender):
        try:
            self.update(force=False)
        except Exception, e:
            logging.warning('Failed to update plot %s: %s', self._name, str(e))

    def _new_data_block_cb(self, sender):
        self.update(force=False)

    @staticmethod
    def get_named_list():
        return Plot._plot_list

    @staticmethod
    def get(name):
        return Plot._plot_list[name]

    ### Convenience methods to the underlying plotbridge object (for backward compatibility) ###
    def set_width(self, val=None, update=True): self._pltbr.set_width(*([val] if val != None else []))
    def set_height(self, val=None, update=True): self._pltbr.set_height(*([val] if val != None else []))
    def set_fontsize(self, val=None, update=True): self._pltbr.set_fontsize(*([val] if val != None else []))
    def set_title(self, val=None, update=True): self._pltbr.set_title(*([val] if val != None else []))
    def set_legend(self, val=None, update=True): self._pltbr.set_legend(*([val] if val != None else []))
    def set_xlabel(self, val=None, update=True): self._pltbr.set_xlabel(*([val] if val != None else []))
    def set_x2label(self, val=None, update=True): self._pltbr.set_x2label(*([val] if val != None else []))
    def set_ylabel(self, val=None, update=True): self._pltbr.set_ylabel(*([val] if val != None else []))
    def set_y2label(self, val=None, update=True): self._pltbr.set_y2label(*([val] if val != None else []))
    def set_zlabel(self, val=None, update=True): self._pltbr.set_zlabel(*([val] if val != None else []))
    def set_cblabel(self, val=None, update=True): self._pltbr.set_cblabel(*([val] if val != None else []))
    def set_xlog(self, val=None, update=True): self._pltbr.set_xlog(*([val] if val != None else []))
    def set_x2log(self, val=None, update=True): self._pltbr.set_x2log(*([val] if val != None else []))
    def set_ylog(self, val=None, update=True): self._pltbr.set_ylog(*([val] if val != None else []))
    def set_y2log(self, val=None, update=True): self._pltbr.set_y2log(*([val] if val != None else []))
    def set_xticks(self, val=None, options=None, update=True): self._pltbr.set_xticks(*([val,options] if val != None else []))
    def set_x2ticks(self, val=None, options=None, update=True): self._pltbr.set_x2ticks(*([val,options] if val != None else []))
    def set_yticks(self, val=None, options=None, update=True): self._pltbr.set_yticks(*([val,options] if val != None else []))
    def set_y2ticks(self, val=None, options=None, update=True): self._pltbr.set_y2ticks(*([val,options] if val != None else []))
    def set_zticks(self, val=None, options=None, update=True): self._pltbr.set_zticks(*([val,options] if val != None else []))
    def set_xrange(self, minval=None, maxval=None, update=True): self._pltbr.set_xrange(*([minval,maxval] if minval != None else []))
    def set_x2range(self, minval=None, maxval=None, update=True): self._pltbr.set_x2range(*([minval,maxval] if minval != None else []))
    def set_yrange(self, minval=None, maxval=None, update=True): self._pltbr.set_yrange(*([minval,maxval] if minval != None else []))
    def set_y2range(self, minval=None, maxval=None, update=True): self._pltbr.set_y2range(*([minval,maxval] if minval != None else []))
    def set_zrange(self, minval=None, maxval=None, update=True): self._pltbr.set_zrange(*([minval,maxval] if minval != None else []))
    def set_grid(self, val=None, update=True): self._pltbr.set_grid(*([val] if val != None else []))

    def save_png(self, *args, **kwargs):
      ''' Deprecated. Use plotbridge.Plot.set_export_png(True) or plotbridge.Plot.set_export_eps(True) followed by run(). '''
      self._pltbr.set_export_png(True)
      logging.warn('This function is deprecated. Use plotbridge.Plot.set_export_png(True) or plotbridge.Plot.set_export_eps(True) followed by run(). Arguments ignored: %s, %s', args, kwargs)

    def save_eps(self, *args, **kwargs):
      ''' Deprecated. Use plotbridge.Plot.set_export_png(True) or plotbridge.Plot.set_export_eps(True) followed by run(). '''
      self._pltbr.set_export_eps(True)
      logging.warn('This function is deprecated. Use plotbridge.Plot.set_export_png(True) or plotbridge.Plot.set_export_eps(True) followed by run(). Arguments ignored: %s, %s', args, kwargs)


class Plot2D(Plot):
    '''
    2D plot.
    '''

    def __init__(self, *args, **kwargs):
        Plot.__init__(self, *args, **kwargs)

    @cache_result
    def get_ndimensions(self):
        return 2

    def add_data(self, data, coorddim=None, valdim=None, **kwargs):
        '''
        Add Data object to 2D plot.

        Input:
            data (Data):
                Data object
            coorddim (int):
                Which coordinate column to use (0 by default)
            valdim (int):
                Which value column to use for plotting (0 by default)
        '''

        if coorddim is None:
            ncoord = data.get_ncoordinates()
            #FIXME: labels
            if ncoord == 0:
                coorddims = ()
            else:
                coorddims = (0,)
                if ncoord > 1:
                    logging.info('Data object has multiple coordinates, using the first one')
        else:
            coorddims = (coorddim,)

        if valdim is None:
            if data.get_nvalues() > 1:
                logging.info('Data object has multiple values, using the first one')
            valdim = data.get_ncoordinates()

        kwargs['coorddims'] = coorddims
        kwargs['valdim'] = valdim
        Plot.add_data(self, data, **kwargs)

    def add(self, *args, **kwargs):
        '''
        Add data object or list / numpy.array to the current plot.
        '''

        args = _convert_arrays(args)
        coorddim = kwargs.pop('coorddim', None)
        globalx = kwargs.pop('x', None)
        valdim = kwargs.pop('valdim', None)
        update = kwargs.pop('update', True)

        i = 0
        while i < len(args):

            # This is easy
            if isinstance(args[i], Data):
                data = args[i]
                i += 1

            elif isinstance(args[i], numpy.ndarray):
                logging.warn('You are strongly encouraged to use plot_engines/plotbridge.py directly, if you are not plotting qt.Data objects.')
                if len(args[i].shape) == 1:
                    if globalx is not None:
                        y = args[i]
                        data = numpy.column_stack((globalx, y))
                        i += 1
                    elif i + 1 < len(args) and isinstance(args[i+1], numpy.ndarray):
                        x = args[i]
                        y = args[i + 1]
                        data = numpy.column_stack((x, y))
                        i += 2
                    else:
                        data = args[i]
                        i += 1

                elif len(args[i].shape) == 2 and args[i].shape[1] == 2:
                    data = args[i]
                    i += 1

                else:
                    logging.warning('Unable to plot array of shape %r',
                            (args[i].shape))
                    i += 1
                    continue

                if 'yerr' in kwargs:
                    assert len(kwargs['yerr']) == len(data), 'yerr must be a 1D vector of the same length as the data.'
                    data = numpy.column_stack((data, kwargs['yerr']))
                    if coorddim is None: coorddim = 0
                    if valdim is None:   valdim = 1
                    kwargs['yerrdim'] = 2

                data = Data(data=data, tempfile=True, binary=True)

            else:
                logging.warning('Unhandled argument: %r', args[i])
                i += 1
                continue

            # data contains a valid data object, add some options and plot it
            opts = _get_plot_options(i, *args)
            for key, val in opts.iteritems():
                kwargs[key] = val
            i += len(opts)

            self.add_data(data, coorddim=coorddim, valdim=valdim, **kwargs)

        if update:
            self.update()

    def set_labels(self, left='', bottom='', right='', top='', update=True):
        for datadict in self._data:
            data = datadict['data']
            if len(datadict['coorddims']) > 0:
                if 'top' in datadict and top == '':
                    top = data.format_label(datadict['coorddims'][0])
                elif bottom == '':
                    bottom = data.format_label(datadict['coorddims'][0])

            if 'right' in datadict and right == '':
                right = data.format_label(datadict['valdim'])
            elif left == '':
                 left = data.format_label(datadict['valdim'])

        if left == '':
            left = 'Y'
        self.plot.set_ylabel(left, update=False)
        self.plot.set_y2label(right, update=False)
        if bottom == '':
            bottom = 'X'
        self.plot.set_xlabel(bottom, update=False)
        self.plot.set_x2label(top, update=False)

        if update:
            self.plot.update()

class Plot3D(Plot):
    '''
    3D plot.
    '''

    def __init__(self, *args, **kwargs):
        if 'mintime' not in kwargs:
            kwargs['mintime'] = 2
        Plot.__init__(self, *args, **kwargs)

    @cache_result
    def get_ndimensions(self):
        return 3

    def add_data(self, data, coorddims=None, valdim=None, **kwargs):
        '''
        Add data to 3D plot.

        Input:
            data (Data):
                Data object
            coorddim (tuple(int)):
                Which coordinate columns to use ((0, 1) by default)
            valdim (int):
                Which value column to use for plotting (0 by default)
        '''

        if coorddims is None:
            if data.get_ncoordinates() > 2:
                logging.info('Data object has multiple coordinates, using the first two')
            coorddims = (0, 1)

        if valdim is None:
            if data.get_nvalues() > 1:
                logging.info('Data object has multiple values, using the first one')
            valdim = data.get_ncoordinates()
            if valdim < 2:
                valdim = 2

        Plot.add_data(self, data, coorddims=coorddims, valdim=valdim, **kwargs)

    def add(self, *args, **kwargs):
        '''
        Add data object or list / numpy.array to the current plot.
        '''

        args = _convert_arrays(args)
        coorddims = kwargs.pop('coorddims', None)
        valdim = kwargs.pop('valdim', None)
        globalxy = kwargs.pop('xy', None)
        globalx = kwargs.pop('x', None)
        globaly = kwargs.pop('y', None)
        update = kwargs.pop('update', True)

        i = 0
        while i < len(args):

            # This is easy
            if isinstance(args[i], Data):
                data = args[i]
                i += 1

            elif isinstance(args[i], numpy.ndarray):
                logging.warn('You are strongly encouraged to use plot_engines/plotbridge.py directly, if you are not plotting qt.Data objects.')
                if len(args[i].shape) == 1:
                    if globalx is not None and globaly is not None:
                        z = args[i]
                        data = numpy.column_stack((globalx, globaly, z))
                        i += 1
                    elif globalxy is not None:
                        z = args[i]
                        data = numpy.column_stack((globalxy, z))
                        i += 1
                    elif i + 2 < len(args) and \
                            isinstance(args[i+1], numpy.ndarray) and \
                            isinstance(args[i+2], numpy.ndarray):
                        x = args[i]
                        y = args[i + 1]
                        z = args[i + 2]
                        data = numpy.column_stack((x, y, z))
                        i += 3
                    else:
                        data = args[i]
                        i += 1

                elif len(args[i].shape) == 2 and args[i].shape[1] >= 3:
                    data = args[i]
                    i += 1

                else:
                    logging.warning('Unable to plot array of shape %r', \
                            (args[i].shape))
                    i += 1
                    continue

                tmp = self.get_needtempfile()
                if not self.get_support_binary():
                    kwargs['binary'] = False
                elif 'binary' not in kwargs:
                    kwargs['binary'] = True
                data = Data(data=data, tempfile=tmp, binary=kwargs['binary'])

            else:
                logging.warning('Unhandled argument: %r', args[i])
                i += 1
                continue

            # data contains a valid data object, add some options and plot it
            opts = _get_plot_options(i, *args)
            for key, val in opts.iteritems():
                kwargs[key] = val
            i += len(opts)

            self.add_data(data, coorddims=coorddims, valdim=valdim, **kwargs)

        if update:
            self.update()

    def set_labels(self, x='', y='', z='', update=True):
        '''
        Set labels in the plot. Use x, y and z if specified, else let the data
        object create the proper format for each dimensions
        '''

        for datadict in self._data:
            data = datadict['data']
            if x == '' and len(datadict['coorddims']) > 0:
                x = data.format_label(datadict['coorddims'][0])
            if y == '' and len(datadict['coorddims']) > 1:
                y = data.format_label(datadict['coorddims'][1])
            if z == '':
                z = data.format_label(datadict['valdim'])

        if x == '':
            x = 'X'
        self.plot.set_xlabel(x, update=False)
        if y == '':
            y = 'Y'
        self.plot.set_ylabel(y, update=False)
        if z == '':
            z = 'Z'
        self.plot.set_zlabel(z, update=False)
        self.plot.set_cblabel(z, update=False)

        if update:
            self.plot.update()

def _get_plot_options(i, *args):
    if len(args) > i:
        if type(args[i]) is types.StringType:
            return {'style': args[i]}
    return {}

def plot(*args, **kwargs):
    '''
    Plot items.

    Variable argument input:
        Data object(s)
        numpy array(s), size n x 1 (two n x 1 arrays to represent x and y),
            or n x 2
        color string(s), such as 'r', 'g', 'b'

    Keyword argument input:
        name (string): the plot name to use, defaults to 'plot'
        coorddim, valdim: specify coordinate and value dimension for Data
            object.
        ret (bool): whether to return plot object (default: True).
    '''

    plotname = args[0] if (len(args) >= 1 and isinstance(args[0], basestring) and 'name' not in kwargs.keys()) else kwargs.pop('name', 'plot')
    ret = kwargs.pop('ret', True)
    graph = Plot._plot_list[plotname]
    if graph is None:
        graph = Plot2D(name=plotname, **kwargs)

    #set_global_plot_options(graph, kwargs)

    #graph.add(*args, **kwargs)

    if ret:
        return graph

def waterfall(*args, **kwargs):
    '''
    Create a waterfall plot, e.g. 3D data as offseted 2D lines.
    '''
    traceofs = kwargs.get('traceofs', 10)
    kwargs['traceofs'] = traceofs
    return plot(*args, **kwargs)

def plot3(*args, **kwargs):
    '''
    Plot items.

    Variable argument input:
        Data object(s)
        numpy array(s), size n x 1 (three n x 1 arrays to represent x, y and
            z), or n x 3
        color string(s), such as 'r', 'g', 'b'

    Keyword argument input:
        name (string): the plot name to use, defaults to 'plot'
        coorddims, valdim: specify coordinate and value dimensions for Data
            object.
        ret (bool): whether to return plot object (default: True).
    '''

    plotname = kwargs.pop('name', 'plot3d')
    ret = kwargs.pop('ret', True)
    graph = Plot._plot_list[plotname]
    if graph is None:
        graph = Plot3D(name=plotname)

    set_global_plot_options(graph, kwargs)

    graph.add(*args, **kwargs)

    if ret:
        return graph

def replot_all():
    '''
    replot all plots in the plot-list
    '''
    plots = Plot.get_named_list()
    for p in plots:
        plots[p].update()
