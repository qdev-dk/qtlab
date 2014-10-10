#ToDo global relative gates
from numpy import pi, random, arange, size, mod, zeros, array, diff, exp, roll, argmax, argmin,nonzero, sign, polyfit,sign,linspace,correlate,mean
from numpy import abs,concatenate,int,mat,linalg,convolve,reshape,round_,sqrt,append,inf,nan,exp,round
from time import time, sleep, ctime, localtime
from shutil import copyfile,copytree
from operator import itemgetter #for sorting keys
from types import *
from bisect import bisect,bisect_left,bisect_right
import os
import inspect

global iterator
iterator=0
global iterator2
iterator2=0

import qt
reload(qt)

settings=qt.instruments.get('measurement_settings')

def execute_function_list(function_list):
    for function_tuple in function_list:
        function=function_tuple[0]
        arguments=function_tuple[1]
        function(*arguments)
        
def terminate_scan():
    '''
    Calls all the functions selected by the user in settings._end_scan parameter. 
    To set a function in the list: settings.add_func_end_scan(function)
    To set the list of functions: settings.set_end_scan(<list of functions>)
    To get the list of functions: settings.get_end_scan()
    '''
    function_list=settings.get_end_scan()
    execute_function_list(function_list)
    
def terminate_sweep():
    '''
    Calls all the functions selected by the user in settings._init_sweep parameter. 
    To set a function in the list: settings.add_func_end_sweep(function)
    To set the list of functions: settings.set_end_sweep(<list of functions>)
    To get the list of functions: settings.get_end_sweep()
    '''
    function_list=settings.get_end_sweep()
    execute_function_list(function_list)

    
def initialize_scan():
    '''
    Calls all the functions selected by the user in settings._init_scan parameter. 
    To set a function in the list: settings.add_func_init_scan(function)
    To set the list of functions: settings.set_init_scan(<list of functions>)
    To get the list of functions: settings.get_init_scan()
    '''
    function_list=settings.get_init_scan()
    execute_function_list(function_list)
    
def initialize_sweep():
    '''
    Calls all the functions selected by the user in settings._init_sweep parameter. 
    To set a function in the list: settings.add_func_init_sweep(function)
    To set the list of functions: settings.set_init_sweep(<list of functions>)
    To get the list of functions: settings.get_init_sweep()
    '''
    function_list=settings.get_init_sweep()
    execute_function_list(function_list)
    
def execute_function_list_point():
    '''
    Calls all the functions selected by the user in settings._func_list_point parameter. 
    To set a function in the list: settings.add_func_point(function)
    To set the list of functions: settings.set_func_list_point(<list of functions>)
    To get the list of functions: settings.get_func_list_point()
    '''
    function_list=settings.get_func_list_point()
    execute_function_list(function_list)
    
def write_coordinates_to_data(data,channel):
    '''
    Sets the coordinates of the qt.data files for channel "channel"
    Input: 'data' <qt.data>
           'channel': <string>, 'x' or 'y' or 'z'
    Output: 
        None
    '''
    
    #Get functions get_coordinates and get_npoints for channel "channel"
    get_coord=getattr(settings,'get_coordinates_'+channel)
    get_npoints=getattr(settings,'get_npoints_'+channel)
    
    #Create all coordinates in data
    for coordinate in get_coord():
        #Get options of the instrument.parameter described in the current coordinate
        instrument=qt.instruments.get(coordinate[0])
        options=instrument.get_parameter_options(coordinate[1])
        #Create Name from instrument and parameters
        name=coordinate[0].capitalize()+coordinate[1].capitalize()
        #Create Option for data.add_coordinate
        kwargs={}
        kwargs['size']=get_npoints()        # Number of points along that axis
        kwargs['instrument']=coordinate[0]  #Instrument used
        kwargs['parameter']=coordinate[1]   #Parameter varied
        kwargs['start']=coordinate[2]       #Start value of the sweep
        kwargs['stop']=coordinate[3]        #Stop value of the sweep
        kwargs['axis']=channel              #Axis corresponding to current coordinate ('x','y' or 'z')
        if 'units' in options:
            kwargs['units']=options['units']#Units
        data.add_coordinate(name,**kwargs)
 
def write_values_to_data(data):
    '''
    Sets the coordinates of the qt.data files for channel "channel"
    Input: 'data' <qt.data>
           'channel': <string>, 'x' or 'y' or 'z'
    Output: 
        None
    '''
    #Get Values from settings instruments
    values=settings.get_values()
    for value in settings.get_values():
        #Get instrument, parameter, and options from the instrument
        instrument=qt.instruments.get(value[0])
        options=instrument.get_parameter_options(value[1])
        
        
        #Create name for the data.value
        name=value[0]+'_'+value[1]
        
        kwargs={}
        kwargs['instrument']=value[0]
        kwargs['parameter']=value[1]
        kwargs['type']='value'
        kwargs['units']=options.get('units')
        data.add_value(name,**kwargs)
            
def write_statusfile(data):
    '''
    Creates a file with the current status of all the instruments in the data directory
    Input:data <qt.data>
    '''
    statusfilename=data._dir+'\\comments.txt'
    statusfile=file(statusfilename,'w')
    status=getinstrumentstatus()
    statusfile.write(status)
    statusfile.close()

def create_measurement_datafile(dimension,measurement_name):
    '''
    Creates a new data file for a measurement of dimension 'dim', with title 'title'
    Input: 
        dimension <string>: '2D' or '3D'
        measurement_name <string>: name for the measurement data
    '''
    data = qt.Data(name=dimension+'_'+measurement_name)     #Create Data
    write_coordinates_to_data(data,'x')                       #Create x coordiantes
    if dimension=='3D':
        write_coordinates_to_data(data,'y')                   #Create x coordiantes
    write_values_to_data(data)                                #Create values
    data.create_file()                                      #Write Data File on Disk
    data.emit('new-data-point')         
    #write_statusfile(data)                                  #Write Comments (Status of all the instruments) in the data directory
    return data
    
def initialize_settings(data,dimension):
    '''
    Writes current class file as "classes" parameters of the settings instruments
    Saves the modules and scripts of the measurement
    Sets the "path" attribute of the value instruments to the data path
    Input: data <qt.data>
    '''
    settings.set_current_data(data.get_name())                         #Register "data" as current data object
    settings.set_filename_classes(inspect.getfile(inspect.currentframe()))    #Set Current File as Classes Files
    settings.save_scriptfiles()                             #Save "script", "classes" and "settings" files onto the data directory
    settings.set_dimensions(dimension)
    
    #Sets the path attribute of all the value instruments
    for value in settings.get_values():
        try: 
            value.set_path(data._dir)
        except:
            pass
    
def launch2Dmeasurement(measurement_name):
    '''
    Performs a 2D measurement: y=f(x)
    Input: measurement_name <string>: name of the measurement
    '''
    initialize_instruments()
    #################################################################
    #Qt.Data File Creation
    #################################################################
    data=create_measurement_datafile('2D',measurement_name) #Create the data file for a 2D measurement
    initialize_settings(data,dimension=2) #Save current scripts and modules in the data directory
    print '2D Measurement'
    print data
    print 'Saved in: '+data.get_dir()
    #################################################################
    #Run the list of functions user-selected in settings._init_sweep
    #################################################################
    initialize_sweep()
    #################################################################
    # Measure
    #################################################################
    points=arange(0.0,settings.get_npoints_x()+1,1.0) # points: array of steps, including hysteresis
    if settings.get_hysteretic_x():
        points=concatenate((points,points[::-1]))
    qt.mstart() #Send Start signal to qt
    #Measurement Loop
    for point in points:
        result=list() #list to fill with data point (x1,x2,x3,y1,y2,y3,...)
        # set all the coordinates
        for coordinate in settings.get_coordinates_x():
            #Calculate value to set
            setvalue=((coordinate[3]-coordinate[2])*point)/settings.get_npoints_x()+coordinate[2]
            result.append(setvalue)
            setdevicevalue(coordinate[0],coordinate[1], setvalue)
        # wait for result 
        qt.msleep(settings.get_waittime())
        # execute the functions to prepare the reading
        execute_function_list_point
        # read out all the values
        for value in settings.get_values():
            y=getdevicevalue(value[0],value[1])
            result.append(y)
        # save the data point
        data.add_data_point(*result)
        data.emit('new-data-point')
    
    #################################################################
    # Closing
    #################################################################    
    terminate_sweep()
    data.close_file()
    qt.msleep(3)
    settings.copy_tree()
 
def launch3Dmeasurement(measurement_name):
    '''
    Performs a 3D measurement: z=f(x,y)
    Input: measurement_name <string>: name of the measurement
    '''
    
    #################################################################
    #Create qt.data file
    #################################################################
    data=create_measurement_datafile('3D',measurement_name) #Create the data file for a 2D measurement
    print '3D Measurement'
    print data
    print 'Saved in: '+data.get_dir()
    
    #Save current scripts and modules in the data directory
    initialize_settings(data,dimension=3) 
    #Run the list of functions user-selected in settings._init_sweep
    initialize_scan()
    
    
    #################################################################
    # Measure
    #################################################################
    qt.mstart() #Send Start signal to qt
    # points: array of steps, including hysteresis
    points_x=arange(0.0,settings.get_npoints_x()+1,1.0) 
    points_y=arange(0.0,settings.get_npoints_y()+1,1.0) 
    if settings.get_hysteretic_x():
        points_x=concatenate((points_x,points_x[::-1]))
    if settings.get_hysteretic_y():
        points_y=concatenate((points_y,points_y[::-1]))    
    data_mem=zeros((len(points_x),len(settings.get_values())+len(settings.get_coordinates_y())+len(settings.get_coordinates_x()))) #allocate memory for one data block
    
    #Outer-Loop
    for j,point_y in enumerate(points_y):
        #Set the y_coordinates according to point_y in points_y
        for index,coordinate in enumerate(settings.get_coordinates_y()):
            #Calculate value to set
            setvalue=((coordinate[3]-coordinate[2])*point_y)/settings.get_npoints_y()+coordinate[2]
            setdevicevalue(coordinate[0],coordinate[1], setvalue)
            data_mem[:,len(settings.get_coordinates_x())+index]=setvalue
        #Run the list of functions in settings._init_sweep
        initialize_sweep()
        
        #Inner-Loop
        for i,point_x in enumerate(points_x):  #start sweep loop
            #Set the x_coordinates according to point_x in points_x
            for index,coordinate in enumerate(settings.get_coordinates_x()):
                #Calculate value to set
                setvalue=((coordinate[3]-coordinate[2])*point_x)/settings.get_npoints_x()+coordinate[2]
                setdevicevalue(coordinate[0],coordinate[1], setvalue)
                data_mem[i,index]=setvalue             
            
            # wait for result 
            qt.msleep(settings.get_waittime())
            # execute the functions to prepare the reading
            execute_function_list_point
            
            # read out all the values
            for index,value in enumerate(settings.get_values()):
                y=getdevicevalue(value[0],value[1])
                data_mem[i,index+len(settings.get_coordinates_y())+len(settings.get_coordinates_x())]=y
        
        #Indicate Remaining Time
        if j==0: starttime=time()
        elif j==1:
            timenow=time()
            runtime=(timenow-starttime)*len(points_y)
            print 'The 3D scan takes %d min and will be finished at %s.' % (runtime/60, ctime(2*starttime+runtime-timenow))
            print ''
            
        #For Serpentine Measurement: reverse x axis.
        if settings.get_serpentine() and not settings.get_hysteretic_x(): 
            data_mem=array(sorted(data_mem, key=itemgetter(len(settings.get_coordinates_x()),0))) #in serpentine mode the data block has to be sort otherwise live plotting does not work
            points_x=points_x[::-1]# reverse step order when measuring with serpentine=True
        #Save Data Point
        data.add_data_point(*(data_mem.transpose())) #the data block is saved
        data.new_block() #this is a marker for the end of the data block that is required for gnuplot
        terminate_sweep()
    #################################################################
    # Closing
    #################################################################    
    terminate_scan()
    data.close_file()
    qt.msleep(3)
    settings.copy_tree()
    
def launch4Dmeasurement(measurement_basename):
    '''
    Performs a 4D measurement: a=f(x,y,z) as a series of 3D measurement [a_i=f(x,y) with z_i]
    Input: measurement_basename <string>: base of the name of the measurement
    The complete name for each 3D measurement performed is basename+string_z_instrument+z_value
    '''
    print 'New 4D Measurement'
    print ''
    for index in range(settings.get_npoints_z()):
        #Preparing Measurement: setting outerloop voltage
        coordinate_index=0
        measurement_name=measurement_basename
        for coord_index,coordinate in enumerate(settings.get_coordinates_z()):
            #Set the z coordinate to the desired value
            outerloopvalue=coordinate[2]+index*(coordinate[3]-coordinate[2])/settings.get_npoints_z()
            setdevicevalue(coordinate[0],coordinate[1],outerloopvalue)
            if coord_index==0:
                #Creation of the measurement name from basename and z_coordinate
                instrument=settings.get_coordinates_z()[0][0].capitalize()
                parameter=settings.get_coordinates_z()[0][1].capitalize()
                string_z_instrument=instrument+parameter
                measurement_name=measurement_name+'_'+string_z_instrument+'_'+str(outerloopvalue)
        #Run 3D measurement
        launch3Dmeasurement(measurement_name)
 
def setdevicevalue(device_name,parameter_name, value):
    '''
    Sets the parameter with name "parameter_name" of device of name "device_name" to the value "value"
    Input: 
        device_name: <string>: name of a device (should exist in qt.instruments)
        parameter_name: <string> name of the parameter to be set
        value: value to set to device.set_parameter
    '''
    
    device=qt.instruments.get(device_name) #Get instrument 
    attribute=getattr(device,'set_'+parameter_name) #get the relevant "get_parameter" function of the instrument
    attribute(value) #execute the "set_parameter function and return its value"
    return

def getdevicevalue(device_name,parameter_name):
    '''
    Gets the parameter with name "parameter_name" of device of name "device_name" to the value "value"
    Input: 
        device_name: <string>: name of a device (should exist in qt.instruments)
        parameter_name: <string> name of the parameter to be gotten
    '''
    try:
        device=qt.instruments.get(device_name) #Get instrument
        attribute=getattr(device,'get_'+parameter_name) #get the relevant "get_parameter" function of the instrument
        return attribute() #execute the "get_parameter function and return its value"
    except:
        return -1
        
def getinstrumentstatus():
    '''
    Gets the current status of all the parameters of all the instruments
    Output: text <string>: text giving one line per value
    
    eg: 
    
    IVVI
            dac1:   10 mV
            dac2:   10 mV
    DUMMY
            power:  0 dBm
    
    '''
    text=''
    device_names=qt.instruments.get_instrument_names()
    for device_name in device_names:
        text+=device_name.upper()+'\n'
        device=qt.instruments.get(device_name)
        parameter_names=device.get_parameter_names()
        for parameter_name in parameter_names:
            options=device.get_parameter_options(parameter_name)
            units=''
            if 'units' in options.keys():
                units=options['units']
            device_value=getdevicevalue(device_name,parameter_name)
            if type(device_value) is FloatType:
                text+='\t\t'+'%s = %.2f %s' % (parameter_name, device_value,units)+'\n'
            else:
                text+='\t\t'+'%s = %s %s' % (parameter_name, device_value,units)+'\n'
    return text

def measure_vs_time(measurement_name,measuretime):
    '''
    measuretime time to measure in seconds
    which_value_inst is a tuple of instrument strings to be saved
    waittime=0.1 wait time in seconds after each point
    plotting={'keithley1':1,'keithley2':2} #dictinary of nth graph in which the y-value is plotted (omitted -> not plotted)
    multiplication_factor={'keithley1':100000,'keithley2':100000} #dictinary of multiplication value for each instrument (omitted -> 1)
    description={'keithley1':'current (pA)','keithley2':'current (pA)'} #description of the measured value (omitted -> instrument name)
    title is a string to describe the measurement in the protocol file
    '''
    title=measurement_name+'_vs_time'
    
    #create filename and check dac-names
    comment='%s:\nstart measure vs time %s for %.3f seconds:' % (ctime(),title, measuretime)
    datum='%d/%d/%d' % (localtime()[2],localtime()[1],localtime()[0])
    print comment
    
    
    #################################################################
    #Qt.Data File Creation and Management
    #################################################################
    data = qt.Data(title)    #Create Data
    data.add_coordinate('time (s)')
    set_values_to_data(data)            #Create values
    data.create_file()                  #Write Data File on Disk
    data.emit('new-data-point')         
    write_commentfile(data)             #Write Comments (Status of all the instruments) in the data directory
    
    settings=qt.instruments.get('settings') #Get Settings Instruments
    settings.set_current_data(data)     #Register "data" as current data object
    settings.set_filename('classes',inspect.getfile(inspect.currentframe()))    #Set Current File as Classes Files
    settings.save_scriptfiles()         #Save "script", "classes" and "settings" files onto the data directory
    
    #################################################################
    # Measure
    #################################################################
    starttime=time()
    while starttime+measuretime>time():
        result=list() #list to fill with data point (x1,x2,x3,y1,y2,y3,...)
        # set all the x values
        result.append(time()-starttime)
        # wait for result 
        qt.msleep(waittime)
        # read out all the y values
        for value in settings.get_values():
            y=getdevicevalue(values[0],value[1])
            result.append(y)
        # save the data point
        data.add_data_point(*result)
    #-----------------------

    #Closing
    data._write_settings_file()
    for i in range(graphnumber):
        plot2d[i].save_png()
        plot2d[i].save_gp()
        plot2d[i].clear()
    data.close_file()
    return data_filename
