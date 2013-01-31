# dataview.py, class for post-processing measurement data
# Joonas Govenius <joonas.govenius@aalto.fi>
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
import os
import os.path
import time
import numpy as np
from numpy import ma
import types
import re
import logging
import copy
import shutil
import itertools

from gettext import gettext as _L

from lib import namedlist, temp
from lib.misc import dict_to_ordered_tuples, get_arg_type
from lib.config import get_config
config = get_config()
in_qtlab = config.get('qtlab', False)
from lib.network.object_sharer import SharedGObject, cache_result

if in_qtlab:
    import qt

class DataView():
    '''
    class for post-processing measurement data
    '''

    def __init__(self, data, deep_copy=True, source_column_name='data_source', **kwargs):
        '''
        Create a new view of an existing data object for post-processing.
        The original data object will not be modified.

        args:
          data -- qt.Data object(s)
        
        kwargs input:
          deep_copy          -- specifies whether the underlying data is copied or 
                                only referenced (more error prone, but memory efficient)
          source_column_name -- specifies the name of the (virtual) column that tells which
                                data object the row originates from. Specify None, if
                                you don't want this column to be added.
        '''

        self._virtual_dims = {}

        if isinstance(data, DataView): # clone
          self._dimensions = data._dimensions
          self._dimension_indices = data._dimension_indices
          if deep_copy:
            self._masked_data = ma.masked_array(data._masked_data.data, fill_value=data._masked_data.fill_value)
            self._masked_data.mask = data._masked_data.mask.copy()
          else:
            self._masked_data = ma.masked_array(data._masked_data.data, fill_value=data._masked_data.fill_value)
            self._masked_data.mask = data._masked_data.mask.copy()

          for name, fn in data._virtual_dims.items():
              self._virtual_dims[name] = fn

          return

        try: # see if a single Data object
          self._dimension_names = data.get_dimension_names()
          unmasked = data.get_data().copy() if deep_copy else data.get_data()
          
          if source_column_name != None:
            n = data.get_name()
            source_col = [n for i in range(len(data.get_npoints()))]

        except: # probably a sequence of Data objects then
          self._dimensions = data[0].get_dimension_names()
          
          unmasked = {}
          for dim in self._dimensions:
            unmasked[dim] = []
            for dat in data:
              try:
                unmasked[dim].append(dat[dim])
              except:
                # ignore dimensions that don't exist in all data objects
                del unmasked[dim]
                logging.warn("Dimensions '%s' does not exist in Data object '%s'." % (dim, str(dat)))
                break

            # concatenate rows from all files
            if dim in unmasked.keys():
              unmasked[dim] = np.concatenate(unmasked[dim])
          
          # add a column that specifies the source data file
          if source_column_name != None:
            names = [ '%s_(%s)' % (dat.get_name(), dat.get_filename().strip('.dat')) for dat in data ]
            lens = [ dat.get_npoints() for dat in data ]
            source_col = [ [n for jj in range(l)] for n,l in zip(names,lens) ]
            source_col = itertools.chain.from_iterable(source_col) # flatten
          
          # keep only dimensions that could be parsed from all files
          self._dimensions = unmasked.keys()
          unmasked = np.array([unmasked[k] for k in self._dimensions]).T

        try:
          self._masked_data = ma.masked_array(unmasked, fill_value=np.NaN)
        except ValueError:
          # fill_value=np.NaN does not work for non-float data
          self._masked_data = ma.masked_array(unmasked)

        self._dimension_indices = dict([(n,i) for i,n in enumerate(self._dimensions)])
        self.set_mask(False)

        if source_column_name != None:
          self.add_virtual_dimension(source_column_name, lambda d: itertools.compress(source_col, d._masked_data.mask[:,0]), returns_masked_array=False)

    def __getitem__(self, index):
        '''
        Access the unmasked data.

        index may be a slice or a string, in which case it is interpreted
        as a dimension name.
        '''
        if isinstance(index, basestring):
            return self.get_column(index)
        else:
            return self.get_data()[index]

    def copy(self, copy_data=False):
        '''
        Make a deep copy of the view.
        
        copy_data -- whether the underlying data is also deep copied.
        '''
        return DataView(self, deep_copy=copy_data)

    def clear_mask(self):
        '''
        Unmask all data (i.e. make all data in the initially
        provided Data object visible again).
        '''
        self._masked_data.mask = False

    def set_mask(self, mask):
        '''
        Set an arbitrary mask for the data. Should have the same dimension
        as the data, or simply True/False for masking/unmasking all data.

        See also mask_rows().
        '''
        # although np.ma.mask can be just False, it's a PITA to
        # handle the case separately later so convert it
        # to [False, False,...] here.
        try:
          if mask:
            m = np.ones( self._masked_data.shape, dtype=np.bool)
          else:
            m = np.zeros(self._masked_data.shape, dtype=np.bool)
        except:
            m = mask
        self._masked_data.mask = m

    def mask_rows(self, row_mask, or_with_old_mask=False, and_with_old_mask=False):
        '''
        Mask rows in the data. row_mask should be a boolean vector with a
        length equal to the number of previously unmasked rows, unless either

        or_with_old_mask  -- mask rows where either old or new mask is True
        and_with_old_mask -- mask rows where both old and new mask are True

        is set, in which case row_mask should be equal to the original data length.

        The old mask is determined from the mask of the first column.

        Example:
          d = DataView(...)
          # ignore points where source current exceeds 1 uA.
          d.mask_rows(np.abs(d['I_source']) > 1e-6)
        '''
        if or_with_old_mask and and_with_old_mask:
            logging.warn('You cannot both AND and OR with the old mask.')

        old_mask = self._masked_data.mask[:,0]
        if or_with_old_mask or and_with_old_mask:
            assert row_mask.shape == old_mask.shape, 'The length of the new mask must be equal to the number of rows in the data, if you AND or OR with the old mask.'
            logical_opp = np.logical_or if or_with_old_mask else np.logical_and
            self._masked_data.mask[logical_opp(old_mask, row_mask),:] = True
        else:
            assert row_mask.shape == ((~old_mask).sum(),), 'The length of the new mask must be equal to the number of previously unmasked rows.'
            new_masked_entries = (np.arange(len(old_mask),dtype=np.int)[~old_mask])[row_mask]
            self._masked_data.mask[new_masked_entries,:] = True


    def divide_into_sweeps(self, sweep_dimension):
        '''
        Divide the rows into "sweeps" based on changing direction of column 'sweep_dimension'.
        
        Returns a sequence of tuples indicating the start and end of each sweep.
        '''
        sdim = self[sweep_dimension]
        dx = np.sign(sdim[1:] - sdim[:-1])
        change_in_sign = np.array(np.where(dx[1:] * dx[:-1] < 0),dtype=np.int).reshape((-1)).tolist()
        
        # the direction changing twice in a row means that sweeps are being done repeatedly
        # in the same direction.
        for i in range(len(change_in_sign)-1, 0, -1):
          if change_in_sign[i]-change_in_sign[i-1] == 1: del change_in_sign[i]

        if len(change_in_sign) == 0: return np.array([[0, len(sdim)]])

        start_indices = np.concatenate(([0], change_in_sign))
        stop_indices  = np.concatenate((change_in_sign, [len(sdim)]))

        sweeps = np.concatenate((start_indices, stop_indices)).reshape((2,-1)).T
        
        return sweeps
        

    def mask_sweeps(self, sweep_dimension, sl, unmask_instead=False):
        '''
        Mask entire sweeps (see divide_into_sweeps()).

        sl can be a single integer or any slice object compatible with a 1D numpy.ndarray (list of sweeps).

        unmask_instead -- unmask the specified sweeps instead, mask everything else
        '''
        sweeps = self.divide_into_sweeps(sweep_dimension)
        row_mask = np.zeros(len(self[sweep_dimension]), dtype=np.bool)
        for start,stop in ([sweeps[sl]] if isinstance(sl, int) else sweeps[sl]):
            logging.debug("%smasking start: %d, stop %d" % ('un' if unmask_instead else '',start, stop))
            row_mask[start:stop] = True
        self.mask_rows(~row_mask if unmask_instead else row_mask)


    def unmask_sweeps(self, sweep_dimension, sl):
        '''
        Mask all rows except the specified sweeps (see divide_into_sweeps()).

        sl can be a single integer or any slice object compatible with a 1D numpy.ndarray (list of sweeps).
        '''
        self.mask_sweeps(sweep_dimension, sl, unmask_instead=True)


    def get_data(self, masked=False, fill=False, deep_copy=False):
        '''
        Get the non-masked data as a 2D ndarray.

        kwargs:
          masked    -- return the data as a masked array instead of ndarray
          fill      -- fill the masked entries with a fill_value (type dependent,
                       np.NaN for floats) instead of skipping them.
          deep_copy -- copy the returned data so that it is safe to modify it.
        '''
        if masked and fill:
            logging.warn('Specifying both "masked" and "fill" does not make sense.')
        
        if masked: d = self._masked_data
        elif fill: d = self._masked_data.filled()
        else:
            d = self._masked_data[~self._masked_data.mask]
            try:
                d = d.reshape((-1,self._masked_data.shape[1]))
            except:
                logging.warn('Could not reshape the masked data into the original columns.')
                pass # the reshaping fails if the mask is not a simple row mask

        if deep_copy: d = d.copy()

        return d

    def get_column(self, name, masked=False, fill=False, deep_copy=False):
        '''
        Get the non-masked entries of dimension 'name' as a 1D ndarray.
        name is the dimension name.

        kwargs:
          masked    -- return the data as a masked array instead of ndarray
          fill      -- fill the masked entries with a fill_value (type dependent,
                       np.NaN for floats) instead of skipping them.
          deep_copy -- copy the returned data so that it is safe to modify it.
        '''
        if masked and fill:
            logging.warn('Specifying both "masked" and "fill" does not make sense.')

        if name in self._virtual_dims.keys():
            d = self._virtual_dims[name]['fn'](self)
            if not self._virtual_dims[name]['returns_ma']: return d
        else:
            d = self._masked_data[:,self._dimension_indices[name]]
        
        if masked: pass
        elif fill: d = d.filled()
        else:      d = d[~d.mask]

        if deep_copy: d = d.copy()

        return d

    def add_virtual_dimension(self, name, fn, returns_masked_array=True):
        '''
        Makes the vector fn[self] accessible as self[name].

        It is advisable that fn[data].shape == data.shape.
        
        kwargs:
          returns_masked_array -- fn returns a masked array, so that the
                                  usual arguments passed to get_column are
                                  automatically handled. Otherwise, no
                                  masking is done to fn[data]
        '''
        logging.debug('adding virtual dimension "%s"' % name)
        self._virtual_dims[name] = {'fn': fn, 'returns_ma': returns_masked_array}

    def remove_virtual_dimension(self, name):
        if name in self._virtual_dims.keys():
            del self._virtual_dims[name]
        else:
            logging.warn('Virtual dimension "%s" does not exist.' % name)

    def remove_virtual_dimensions(self):
        self._virtual_dims = {}
