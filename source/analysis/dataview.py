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
    Class for post-processing measurement data. Main features are:
      * Concatenating multiple qt.Data objects
      * Creating "virtual" columns by parsing comments or applying arbitrary functions to the data
      * Dividing the rows into sweeps.

    Features not yet implemented but that might be useful:
      * Parsing virtual columns from the measurement .cfg files.

    See qtlab/examples/analysis_with_dataview.py for example use.
    '''

    def __init__(self, data, deep_copy=False, source_column_name='data_source', **kwargs):
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
          # these private variables should be immutable so no need to deep copy
          self._dimensions = data._dimensions
          self._dimension_indices = data._dimension_indices
          self._source_col = data._source_col
          self._comments = data._comments
          
          if deep_copy:
            self._data = data._data.copy()
          else:
            self._data = data._data

          # Always deep copy the mask
          self._mask = data._mask.copy()

          for name, fn in data._virtual_dims.items():
              self._virtual_dims[name] = fn

          return

        try: # see if a single Data object
          self._dimensions = data.get_dimension_names()
          unmasked = data.get_data().copy() if deep_copy else data.get_data()
          
          if source_column_name != None:
            n = data.get_name()
            self._source_col = [n for i in range(data.get_npoints())]

          self._comments = data.get_comment(include_row_numbers=True)

        except MemoryError as e:
          raise e

        except Exception as e: # probably a sequence of Data objects then
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
          lens = [ dat.get_npoints() for dat in data ]
          if source_column_name != None:
            names = [ '%s_(%s)' % (dat.get_name(), dat.get_filename().strip('.dat')) for dat in data ]
            self._source_col = [ [n for jj in range(l)] for n,l in zip(names,lens) ]
            #self._source_col = [ jj for jj in itertools.chain.from_iterable(self._source_col) ] # flatten
            self._source_col = list(itertools.chain.from_iterable(self._source_col)) # flatten
          
          # keep only dimensions that could be parsed from all files
          self._dimensions = unmasked.keys()
          unmasked = np.array([unmasked[k] for k in self._dimensions]).T

          # concatenate comments, adjusting row numbers from Data object rows to the corresponding dataview rows
          lens = np.array(lens)
          self._comments = [ dat.get_comment(include_row_numbers=True) for dat in data ]
          all_comments = []
          for jj,comments in enumerate(self._comments):
              all_comments.append([ (rowno + lens[:jj].sum(), commentstr) for rowno,commentstr in comments ])
          self._comments = list(itertools.chain.from_iterable(all_comments)) # flatten by one level

        self._data = unmasked
        self._mask = np.zeros(len(unmasked), dtype=np.bool)

        self._dimension_indices = dict([(n,i) for i,n in enumerate(self._dimensions)])
        self.set_mask(False)

        if source_column_name != None:
          self.add_virtual_dimension(source_column_name, arr=np.array(self._source_col))

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

    def get_data_source(self):
        '''
        Returns a list of strings that tell which Data object each of the unmasked rows originated from.
        '''
        return [ i for i in itertools.compress(self._source_col, ~(self._mask)) ]

    def clear_mask(self):
        '''
        Unmask all data (i.e. make all data in the initially
        provided Data object visible again).
        '''
        self._mask[:] = False

    def get_mask(self):
        '''
        Get a vector of booleans indicating which rows are masked.
        '''
        return self._mask.copy()

    def get_dimensions(self):
        '''
        Returns a list of all dimensions, both real and virtual.
        '''
        return list(itertools.chain(self._dimension_indices.keys(), self._virtual_dims.keys()))

    def get_comments(self, include_row_numbers=True):
        '''
        Return the comments parsed from the data files.
        '''
        return self._comments if include_row_numbers else [ commentstr for rowno,commentstr in self._comments ]

    def get_continuous_ranges(self, masked_ranges=False):
        '''
        Returns a list of (start,stop) tuples that indicate continuous ranges of (un)masked data.
        '''
        m = self.get_mask() * (-1 if masked_ranges else 1)
        
        dm = m[1:] - m[:-1]
        starts = 1+np.where(dm < 0)[0]
        stops = 1+np.where(dm > 0)[0]

        if not m[0]:
            starts = np.concatenate(( [0], starts ))
        if not m[-1]:
            stops = np.concatenate(( stops, [len(m)] ))

        return zip(starts, stops)

    def set_mask(self, mask):
        '''
        Set an arbitrary mask for the data. Should be a vector of booleans of
        the same length as the number of data points.
        Alternatively, simply True/False masks/unmasks all data.

        See also mask_rows().
        '''
        try:
          if mask:
            self._mask[:] = True
          else:
            self._mask[:] = False
        except:
          m = np.zeros(len(self._mask), dtype=np.bool)
          m[mask] = True
          self._mask = m

    def mask_rows(self, row_mask, unmask_instead=False):
        '''
        Mask rows in the data. row_mask can be a slice or a boolean vector with
        length equal to the number of previously unmasked rows.

        The old mask is determined from the mask of the first column.

        Example:
          d = DataView(...)
          # ignore points where source current exceeds 1 uA.
          d.mask_rows(np.abs(d['I_source']) > 1e-6)
        '''
        old_mask = self._mask
        n = (~old_mask).astype(np.int).sum() # no. of previously unmasked entries
        #logging.debug("previously unmasked rows = %d" % n)

        # new mask for the previously unmasked rows
        new_mask = np.empty(n, dtype=np.bool); new_mask[:] = unmask_instead
        new_mask[row_mask] = (not unmask_instead)
        #logging.debug("new_mask.sum() = %d" % new_mask.sum())

        # combine the old and new masks
        full_mask = old_mask.copy()
        full_mask[~old_mask] = new_mask

        logging.debug("# of masked/unmasked rows = %d/%d" % (full_mask.astype(np.int).sum(), (~full_mask).astype(np.int).sum()))
        self.set_mask(full_mask)


    def divide_into_sweeps(self, sweep_dimension, use_sweep_direction = None):
        '''
        Divide the rows into "sweeps" based on a changing value of column 'sweep_dimension'
        or based on changing direction of 'sweep_dimension'. If use_sweep_direction is None,
        the method tries to figure out which one is more reasonable.

        Sequences of four or more points with a constant value of 'sweep_dimension' are also
        considered a sweep.
        
        Returns a sequence of tuples indicating the start and end of each sweep.

        Note that the indices are relative to the currently _unmasked_ rows only.
        '''
        sdim = self[sweep_dimension]
        dx = np.sign(sdim[1:] - sdim[:-1])

        if use_sweep_direction == None:
          use_sweep_direction = ( np.abs(dx).astype(np.int).sum() > len(dx)/4. )

        if use_sweep_direction:
          logging.info("Assuming '%s' is swept." % sweep_dimension)
        else:
          logging.info("Assuming '%s' stays constant within a sweep." % sweep_dimension)

        if use_sweep_direction:
          for i in range(1,len(dx)):
              if dx[i] == 0: dx[i]=dx[i-1] # this is necessary to detect changes in direction, when the end point is repeated
          change_in_sign = (1 + np.array(np.where(dx[1:] * dx[:-1] < 0),dtype=np.int).reshape((-1))).tolist()

          # the direction changing twice in a row means that sweeps are being done repeatedly
          # in the same direction.
          for i in range(len(change_in_sign)-1, 0, -1):
            if change_in_sign[i]-change_in_sign[i-1] == 1: del change_in_sign[i-1]

          if len(change_in_sign) == 0: return np.array([[0, len(sdim)]])

          start_indices = np.concatenate(([0], change_in_sign))
          stop_indices  = np.concatenate((change_in_sign, [len(sdim)]))

          sweeps = np.concatenate((start_indices, stop_indices)).reshape((2,-1)).T
        else:
          change_in_sdim = 1 + np.array(np.where(dx != 0)).reshape((-1))
          if len(change_in_sdim) == 0: return np.array([[0, len(sdim)]])

          start_indices = np.concatenate(([0], change_in_sdim))
          stop_indices  = np.concatenate((change_in_sdim, [len(sdim)]))
        
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


    def get_data(self, deep_copy=False):
        '''
        Get the non-masked data as a 2D ndarray.

        kwargs:
          deep_copy -- copy the returned data so that it is safe to modify it.
        '''
        d = self._data[~(self._mask)]
        if deep_copy: d = d.copy()
        return d

    def get_column(self, name, deep_copy=False):
        '''
        Get the non-masked entries of dimension 'name' as a 1D ndarray.
        name is the dimension name.

        kwargs:
          deep_copy -- copy the returned data so that it is safe to modify it.
        '''
        if name in self._virtual_dims.keys():
            d = self._virtual_dims[name]['fn'](self)
            if len(d) == len(self._mask): d = d[~(self._mask)] # The function may return masked or unmasked data...
            return d
        else:
            d = self._data[~(self._mask),self._dimension_indices[name]]
        
        if deep_copy: d = d.copy()
        return d

    def add_virtual_dimension(self, name, fn=None, arr=None, comment_regex=None, cache_fn_values=True):
        '''
        Makes a computed vector accessible as self[name].
        The computed vector depends on whether fn, arr or comment_regex is specified.

        It is advisable that the computed vector is of the same length as
        the real data columns.
        
        kwargs:
          fn            -- the function applied to the DataView object, i.e self[name] returns fn(self)
          arr           -- specify the column directly as an array, i.e. self[name] returns arr
          comment_regex -- for each row, take the value from the last match in a comment, otherwise np.NaN

          cache_fn_values -- evaluate fn(self) immediately for the entire (unmasked) array and cache the result
        '''
        logging.debug('adding virtual dimension "%s"' % name)

        assert (fn != None) + (arr != None) + (comment_regex != None) == 1, 'You must specify exactly one of "fn", "arr", or "comment_regex".'

        if arr != None:
            assert arr.shape == tuple([len(self._mask)]), '"arr" must be a 1D vector of the same length as the real data columns. If you want to do something fancier, specify your own fn.'

            self.add_virtual_dimension(name,
                                       (lambda dd,arr=arr: arr),
                                       cache_fn_values=False)
            return

        if comment_regex != None:
            # construct the column by parsing the comments
            vals = np.empty(len(self._mask)) + np.nan

            prev_match_on_row = 0
            prev_val = np.nan

            #logging.debug(self._comments)

            for rowno,commentstr in self._comments:
                m = re.search(comment_regex, commentstr)
                if m == None: continue
                #logging.debug('Match on row %d: "%s"' % (rowno, commentstr))

                if len(m.groups()) != 1:
                  logging.warn('Did not get a unique match (%s) in comment (%d): %s' % (str(groups), rowno, commentstr))

                new_val = float(m.group(1))
                vals[prev_match_on_row:rowno] = prev_val
                logging.debug('Setting value for rows %d:%d = %g' % (prev_match_on_row, rowno, prev_val))

                prev_match_on_row = rowno
                prev_val = new_val

            logging.debug('Setting value for (remaining) rows %d: = %g' % (prev_match_on_row, prev_val))
            vals[prev_match_on_row:] = prev_val

            self.add_virtual_dimension(name, arr=vals)
            return

        if cache_fn_values:
            old_mask = self.get_mask().copy() # backup the mask
            self.clear_mask()
            vals = fn(self)
            self.mask_rows(old_mask) # restore the mask

            self.add_virtual_dimension(name, arr=vals, cache_fn_values=False)
            return

        self._virtual_dims[name] = {'fn': fn}

    def remove_virtual_dimension(self, name):
        if name in self._virtual_dims.keys():
            del self._virtual_dims[name]
        else:
            logging.warn('Virtual dimension "%s" does not exist.' % name)

    def remove_virtual_dimensions(self):
        self._virtual_dims = {}
