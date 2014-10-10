import qt
import inspect
from instrument import Instrument
import types
from shutil import copyfile,copytree
import os

class measurement_settings(Instrument):
    def __init__(self,name):
        Instrument.__init__(self, name)
        #################################################
        #Private Attributes
        #################################################
        # Hysteresis and Serpentine Settings
        self._serpentine=False
        self._hysteretic={'x':False,'y':False}
        #Coordinates:
        self._coordinates={'x':[],'y':[],'z':[]}
        #Values:
        self._values=[]
        #Number of points
        self._npoints={'x':10,'y':10,'z':10}
        #Waittime
        self._waittime=0.05
        #Current Data File
        self._current_data=None
        #Copy Path
        self._copy=True
        self._path_copy='C:\\qtlab_pierre\\tmp'
        #Filenames
        self._filenames={'classes':None,'settings':inspect.getfile(inspect.currentframe()),'script':None}
        #Dimension of the measurement
        self._dimensions=2
        
        self._init_sweep=[]         #list of functions to be executed at the beginning of each sweep
        self._init_scan=[]          #list of functions to be executed at the end of each sweep
        self._end_sweep=[]          #list of functions to be executed at the beginning of each scan
        self._end_scan=[]           #list of functions to be executed at the end of each scan
        self._func_list_point=[]    #list of functions to be executed at each point
        
        self._background=[]         #list (use: stack-like: append/pop) of attribute dictionnary for saving current status
        
        #################################################
        #Instrument Parameters
        #################################################
        self.add_parameter('serpentine',type=types.BooleanType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('hysteretic_',channels=('x','y'),type=types.BooleanType,flags=Instrument.FLAG_GETSET)
        
        self.add_parameter('coordinates_',channels=('x','y','z'),type=types.ListType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('values',type=types.ListType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('npoints_',channels=('x','y','z'),type=types.IntType,flags=Instrument.FLAG_GETSET)
        
        self.add_parameter('current_data',type=types.StringType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('copy',type=types.BooleanType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('path_copy',type=types.StringType,flags=Instrument.FLAG_GETSET)
        
        self.add_parameter('filename_',channels=('script','classes','settings'),type=types.StringType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('dimensions',type=types.IntType)
        
        self.add_parameter('init_scan',type=types.ListType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('init_sweep',type=types.ListType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('end_scan',type=types.ListType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('end_sweep',type=types.ListType,flags=Instrument.FLAG_GETSET)
        self.add_parameter('func_list_point',type=types.ListType,flags=Instrument.FLAG_GETSET)
        
        self.add_parameter('waittime',type=types.FloatType)
        #################################################
        #Instrument Functions
        #################################################
        self.add_function('save_scriptfiles')
        self.add_function('add_coordinates')
        self.add_function('add_values')
        self.add_function('copy_tree')
        
        self.add_function('add_func_init_scan')
        self.add_function('add_func_end_scan')
        self.add_function('add_func_init_sweep')
        self.add_function('add_func_end_sweep')
        self.add_function('add_func_point')
        
        self.add_function('send_to_background')
        self.add_function('retrieve_from_background')
        #self.add_function('dummy_function')
        #Get All
        self.get_all()
    
    def get_all(self):
        
        self.get_coordinates_x()
        self.get_coordinates_y()
        self.get_coordinates_z()
        
        self.get_npoints_x()
        self.get_npoints_y()
        self.get_npoints_z()
        
        self.get_values()
        self.get_hysteretic_x()
        self.get_hysteretic_y()
        
        self.get_serpentine()
        self.get_current_data()
        self.get_dimensions()
        self.get_copy()
        self.get_path_copy()
        self.get_filename_classes()
        self.get_filename_settings()
        self.get_filename_script()
        self.get_waittime()
		
        self.get_init_scan()
        self.get_init_sweep()
    ######################################
    # Set/Get Values
    ######################################
    def do_get_values(self):
        '''
        Returns the values for the measurement
        Output: values: <List of <Tuples>>: [(Instrument,Parameter)]
        Eg: [(keithley1,readlastval)]
        '''
        return self._values
        
    def do_set_values(self,values):
        '''
        Returns the values for the measurement
        Input: values: <List of <Dict>>: [{name:'keithley1',multiplication_factor:1000,description:'QPC Current (pA)'}]
        '''
        self._values=values
        
    
    def add_values(self,value):
        '''
        Appends "value" to the list of values self._values
        Input:
            value: <Dict> or <List of <Dict>>
        '''
        self._values.append(new_value)
    
    ######################################
    # Set/Get Coordinates
    ######################################
        
    def do_set_coordinates_(self,coordinates,channel):
        '''
        Sets the coordinates of the measurement for axis "channel" to "coordinates"
        Input:  
                coordinates <List of <tuples>>. 
                channel <string> 'x' or 'y' or 'z'
        Output: 
                None
        Eg: [(IVVI,DAC1,10,100),(IVVI,DAC2,100,0)] would correspond to sweeping the IVVI.DAC1 parameter from 10mV to 100mV, while sweeping
        IVVI.DAC2 at the same time between 100mV and 0mV.
        '''
        self._coordinates[channel]=coordinates
        
    def do_get_coordinates_(self,channel):
        '''
        Returns the coordinates for axis "channel"
        Input:  
                channel <string> 'x' or 'y' or 'z'
        Output: 
                coordinates <List of <tuples>>. 
        Eg: [(IVVI,DAC1,10,100),(IVVI,DAC2,100,0)] would correspond to sweeping the IVVI.DAC1 parameter from 10mV to 100mV, while sweeping
        IVVI.DAC2 at the same time between 100mV and 0mV.
        '''
        
        return self._coordinates[channel]
    
    def add_coordinates(self,coordinate,channel):
        '''
        Adds the coordinate "coordinate" to the axis "channel"
        Input: coordinate: <tuple> or list of tuples. 
               channel <string> 'x' or 'y' or 'z'
        '''
        if type(coordinate) is TupleType:
            self._coordinates[channel].append(coordinate)
        elif type(coordinate) is ListType:
            for coord in coordinate:
                self._coordinates[channel].append(coord)
    
    ######################################
    # Set/Get Number of Points per sweep
    ######################################
    
    def do_get_npoints_(self,channel):
        '''
        Returns the number of points for the axis "channel"
        Input:
            channel: <string> 'x' or 'y' or 'z'
        '''
        return self._npoints[channel]
    
    def do_set_npoints_(self,npoints,channel):
        '''
        Sets the number of points for the axis "channel" to "npoints
        Input:
            npoints: <Int>: number of points
            channel: <string>: 'x' or 'y' or 'z'
        '''
        self._npoints[channel]=npoints
    
    def do_get_waittime(self):
        '''
        Get Waittime: time to wait between two consecutive measurements
        Output: 
            waittime <float>
        '''
        return self._waittime
    def do_set_waittime(self,time):
        '''
        Set Waittime: time to wait between two consecutive measurements
        Input: 
            time <float>
        '''
        self._waittime=time
    
    
    ######################################
    # Set/Get Flags
    ######################################
    
    def do_set_serpentine(self,serpentine_flag):
        '''
        Sets the serpentine parameters 
        Input:  
                serpentine_flag: <Boolean>
        Usage:
                If serpentine_flag=True, consecutive sweeps of the 'x' coordinates have to be done in opposite direction. 
        ex: 
        
        coordinate_x=[(IVVI,DAC1,0,3)]
        coordinate_y=[(IVVI,DAC2,0,3)]
        In the case that serpentine_flag==True,
        the measurement will be done: 
        (DAC1,DAC2): (0,0) (1,0) (2,0) (3,0)
                     (5,1) (4,1) (3,1) (2,1)
                     (0,2) (1,2) (2,2) (3,2)
        '''
        self._serpentine=serpentine_flag
    
    def do_get_serpentine(self):
        '''
        Sets the serpentine parameters.
        Output:
                serpentine_flag: <Boolean>
        '''
        return self._serpentine
    
    def do_set_hysteretic_(self,hysteretic_flag,channel):
        '''
        Sets the hysteresic parameters for measurement along the axis "channel". 
        Input:  
                hysteretic_flag: <Boolean>
                channel:         <string>: 'x' or 'y'
        Usage: 
                self.set_hysteretic(True,'x') means that the measurement has to be done sweeping the 'x' coordinates back and forth
                self.set_hysteretic(False,'y') means that the measurement has to be done stepping the 'y' coordinates only in one direction
        ex:     
                coordinate_x=[(IVVI,DAC1,0,3)]
                coordinate_y=[(IVVI,DAC2,0,3)]
                In the case that hyseretic_flag==True for 'x':
                (DAC1,DAC2):    (0,0) (1,0) (2,0) (3,0) (3,0) (2,0) (1,0) (0,0)
                                (0,1) (1,1) (2,1) (3,1) (3,1) (2,1) (1,1) (0,1)
                                (0,2) (1,2) (2,2) (3,2) (3,2) (2,2) (1,2) (0,2)
        '''
        
        self._hysteretic[channel]=hysteretic_flag
    
    def do_get_hysteretic_(self,channel):
        '''
        Sets the hysteresic parameters for measurement along the axis "channel". 
        Input:  
                channel:         <string>: 'x' or 'y'
        Output:
                hysteretic_flag: <Boolean>
        '''
        return self._hysteretic[channel]
    
    ######################################
    # Set/Get Dimensions
    ######################################
    
    def do_get_dimensions(self):
        '''
        Returns the dimensions of the current measurement
        Output: dimension <int>
                    if dimension==2, measurement is of dimension 2: value=f(coordinate_x)
                    if dimension==3, measurement is of dimension 3: value=f(coordinate_x,coordinate_y)
                    if dimension==4, measurement is of dimension 4: value=f(coordinate_x,coordinate_y,coordinate_z)
        '''
        return self._dimensions
        
    def do_set_dimensions(self,dimensions):
        '''
        Sets the dimensions of the current measurement
        Output: dimension <int>
                    if dimension==2, measurement is of dimension 2: value=f(coordinate_x)
                    if dimension==3, measurement is of dimension 3: value=f(coordinate_x,coordinate_y)
                    if dimension==4, measurement is of dimension 4: value=f(coordinate_x,coordinate_y,coordinate_z)
        '''
        self._dimensions=dimensions
    
    
    ######################################
    # Set/Get Current Data
    ######################################
    
    def do_set_current_data(self,data):
        '''
        Set the currently active data
        Input: data <qt.data>
        '''
        self._current_data=data
        
    def do_get_current_data(self):
        '''
        Returns the currently active data
        Output: data <qt.data>
        '''
        return self._current_data
    
    ######################################
    # Set/Get Path_copy / Filename
    ######################################
    def do_get_copy(self):
        '''
        Get the "copy" flag. If self._copy is true, the measurement data directory get copied onto the self._path_copy path.
        Input: 
            flag: <Boolean>
        '''
        return self._copy
    
    def do_set_copy(self,flag):
        '''
        Set the "copy" flag. If self._copy is true, the measurement data directory get copied onto the self._path_copy path.
        Input: 
            flag: <Boolean>
        '''
        self._copy=flag
    
    def do_set_path_copy(self,path):
        '''
        Sets the path on the server for copying data
        Input: path <string>: valid path on the server 
        '''
        self._path_copy=path
        
    def do_get_path_copy(self):
        return self._path_copy
        
    def do_get_filename_(self,channel):
        '''
        Gets the name of the "settings" or "classes" or "script" file
        Input: channel: <string>: "settings" or "classes" or "script"
        Output: <string>: name of the "settings" or "classes" or "script" file
        '''
        return self._filenames[channel]
    
    def do_set_filename_(self,filename,channel):
        '''
        Sets the name of the "settings" or "classes" or "script" file
        Input: 
            filename: <string>: name of the file
            channel: <string>: "settings" or "classes" or "script"
        
        '''
        self._filenames[channel]=filename
    
    ######################################
    # Set/Get init_scan and _init_sweep, ...
    ######################################
    def do_get_init_scan(self):
        '''
        Returns the list of functions to be runned at the beginning of each scan (3D measurement)
        Output: function_list: <List of <functions>>
        '''
        return self._init_scan
    
    def do_get_init_sweep(self):
        '''
        Returns the list of functions to be runned at the beginning of each sweep (line in 3D measurement / 2D measurement)
        Output: function_list: <List of <functions>>
        '''
        return self._init_sweep
    
    def do_set_init_scan(self,function_list):
        '''
        Sets the list of functions to be runned at the beginning of each scan (3D measurement)
        Input: function_list: <List of <functions>>
        '''
        self._init_scan=[]
        for function in function_list:
            self._init_scan.append(function)
            
    def do_set_init_sweep(self,function_list):
        '''
        Sets the list of functions to be runned at the beginning of each sweep (line in 3D measurement / 2D measurement)
        Input: function_list: <List of <functions>>
        '''
        self._init_sweep=[]
        for function in function_list:
            self._init_sweep.append(function)
    
    def do_get_end_scan(self):
        '''
        Returns the list of functions to be runned at the beginning of each scan (3D measurement)
        Output: function_list: <List of <functions>>
        '''
        return self._end_scan
    
    def do_get_end_sweep(self):
        '''
        Returns the list of functions to be runned at the beginning of each sweep (line in 3D measurement / 2D measurement)
        Output: function_list: <List of <functions>>
        '''
        return self._end_sweep
    
    def do_set_end_scan(self,function_list):
        '''
        Sets the list of functions to be runned at the beginning of each scan (3D measurement)
        Input: function_list: <List of <functions>>
        '''
        self._end_scan=[]
        for function in function_list:
            self._end_scan.append(function)
            
    def do_set_end_sweep(self,function_list):
        '''
        Sets the list of functions to be runned at the beginning of each sweep (line in 3D measurement / 2D measurement)
        Input: function_list: <List of <functions>>
        '''
        self._end_sweep=[]
        for function in function_list:
            self._end_sweep.append(function)
            
    def do_set_func_list_point(self,function_list)
        '''
        Sets the list of functions to be runned at the beginning of each sweep (line in 3D measurement / 2D measurement)
        Input: function_list: <List of <functions>>
        '''
        self._func_list_point=[]
        for function in function_list:
            self._func_list_point.append(function)
    
    def do_get_func_list_point(self):
        '''
        Returns the list of functions to be runned at each point
        Output: function_list: <List of <functions>>
        '''
        return self._func_list_point   
    
    def add_func_point(self,function):
        self._func_list_point.append(function)
    def add_func_init_sweep(self,function):
        self._init_sweep.append(function)    
    def add_func_end_sweep(self,function):
        self._end_sweep.append(function)    
    def add_func_init_scan(self,function):
        self._init_scan.append(function)    
    def add_func_end_scan(self,function):
        self._end_scan.append(function)
    
    ######################################
    # Misc.
    ######################################
    
    def save_scriptfiles(self):
        '''
        Saves the Script file, the Classes file, and the Settings file in the "_current_data" data directory
        '''
        if self._current_data:
            if self._filenames['script']: 
                copyfile(self._filenames['script'],("%s\\script.copy" % qt.data[self._current_data]._dir)) 
            if self._filenames['settings']:
                copyfile(self._filenames['settings'],("%s\\settings.copy" % qt.data[self._current_data]._dir))
            if self._filenames['classes']:        
                copyfile(self._filenames['classes'],("%s\\classes.copy" % qt.data[self._current_data]._dir))
        else: 
            raise ValueError('Current Data not defined in Settings')
    
    def copy_tree(self):
        '''
        Copy Measurement Data onto the servers
        '''
        if self._copy and self._path_copy:
            path_data=os.path.dirname(qt.data[self._current_data].get_filepath()) #Get directory name of the _current_data data file
            path_data_split=path_data.split(os.path.sep) #Split Directory to get date and time of data
            copy_dir=os.path.join(self._path_copy,path_data_split[-2],path_data_split[-1]) #Data Path on the servers
            copytree(path_data,copy_dir) #Copy Directory onto Server
    
    def send_to_background(self):
        '''
        Saves the current settings to the background to allow another measurement in the foreground
        '''
        background={}
        for attribute in ['_serpentine','_hysteretic','_coordinates','_values','_npoints','_waittime','_current_data','_path_copy','_filenames','_dimensions']:
            attribute_value=getattr(self,attribute)
            background[attribute]=attribute_value
        self._background.append(background)
        
    def retrieve_from_background(self):
        '''
        Retrieves the settings from the background.
        '''
        background=self._background.pop()
        for attribute in ['_serpentine','_hysteretic','_coordinates','_values','_npoints','_waittime','_current_data','_path_copy','_filenames','_dimensions']:
            attribue_value=background[attribute]
            setattr(self,attribute,attribue_value)
        self.get_all()
        
    def dummy_function(self):
        print 'dummy'