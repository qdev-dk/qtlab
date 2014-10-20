First Time User Guide
=====================

Contents
--------
1. Instalation

2: First time configurations


1) Instalation
----------------
Consult the instalation guide INSTALL.md

2) First time configurations:
----------------------------
### 2.1 User Config
First thing you want to do is go to userconfig.py located at the root of qtlab.
Here you want to set the path for where you want to store your data, and a few other options.

### 2.2 Loading instruments
Next you want to go to the scrip called XX_create_instruments.py in the init folder, and add the instruments of your setup.

Create a new instrument is a simple matter:

    qt.instruments.create('<name>', '<instrument type>', <parameters>)

For example:

    qt.instruments.create('dmm1', 'Keithley_2700', address='GPIB::12')

Check out the instrument drivers in the folder instrument_plugins to see what drivers are availible.


3 Basics
--------
The instruments collection can be accessed easily by typing:

    qt.instruments
