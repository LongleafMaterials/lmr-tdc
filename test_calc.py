# -*- coding: utf-8 -*-
"""
Experimenting with GPU-accelerated thermodynamic calculations

Created on Fri Jul 19 19:22:53 2024
@author: Colin-LMR

Note for others - install via anaconda prompt:
 conda install conda-forge::pycuda
 conda install conda-forge::cupy
 conda install conda-forge::cutensor (may need cutensor-cu12)

cudf (GPU-accelerated dataframes, analagous to pandas) can be used with WSL2
"""

### Load packages
# pycuda - access to CUDA from python
# cupy - CUDA-processed numpy and scipy
# cutensor - tensor linear algebra
# urllib - retrieving TDB data
# json - reading TDB data
# pandas - data handling/access
# re - Identification of function names within another function
import pycuda.autoinit
import cupy as cp
#import cutensor as ct
from urllib.request import urlopen
import json
import pandas as pd
import re
import sys

# Add local working directory to PATH
wd = 'C:\\Users\\Colin-LMR\\OneDrive - Longleaf Materials Research\\Documents\\Longleaf Materials Research\\Projects\\lmr-tdc\\'
sys.path.append(wd)

# TDC Functions
from load_data import loadData

# Path to COST507R JSON file
url = 'https://raw.githubusercontent.com/LongleafMaterials/lmr-tdc/main/tdb/COST507R.json'

# Load data into dataframes
elem, param, func = loadData(url)

# Run thermo function with specified name and temperature
def fCalc(name, T):
    None





#%% Test Section
import time
import os
import numpy as np
import re
import math

# Test variables
name = 'GLIQAL'
temp = 1215


def method1(T):
    try:
        f = func.loc[(func['name'] == name) & 
                     (func['min_temp'] <= T) &
                     (func['max_temp'] >= T)]['function'].values[0]
    except:
        msg = 'No function found for ' + name + ' at ' + str(temp) + 'K'
    
    # Look for referenced functions
    rf = re.findall(r'([A-Z]{2,})', f)
    
    # Substitute named function(s) into original
    for r in rf:
        f = f.replace(r, func.loc[(func['name'] == r) & 
                                  (func['min_temp'] <= T) &
                                  (func['max_temp'] >= T)]['function'].values[0])
    
    eval(f)


def buildFunctions(temps):
    functions = []
    for T in temps:
        try:
            f = func.loc[(func['name'] == name) & 
                         (func['min_temp'] <= T) &
                         (func['max_temp'] >= T)]['function'].values[0]
        except:
            msg = 'No function found for ' + name + ' at ' + str(temp) + 'K'
        
        # Look for referenced functions
        rf = re.findall(r'([A-Z]{2,})', f)
        
        # Substitute named function(s) into original
        for r in rf:
            f = f.replace(r, func.loc[(func['name'] == r) & 
                                      (func['min_temp'] <= T) &
                                      (func['max_temp'] >= T)]['function'].values[0])
        
        functions.append(f)
    return functions
       
def method2(f):
    eval(f)

start = time.time()
for T in range(300, 1501):
    method1(T)
end = time.time()
msg = 'Method 1 elapsed time: ' + str(end-start) + ' seconds'
print(msg)

# Note - it's slightly faster (~5%) to prebuild the functions then evaluate all at once,
# but almost all the time is spent building functions/looking up. Could be worth
# prebuilding all of them into a separate file.
start = time.time()
temps = range(300, 1501)
funcs = buildFunctions(temps)
[method2(f) for f, T in zip(funcs, temps)]
end = time.time()
msg = 'Method 2 elapsed time: ' + str(end-start) + ' seconds'
print(msg)

### Equilibrium for binary system
# For a binary system:
#  G = Σ(xi * Gi0) + RT*Σ(xi*ln(xi)) + Gex
#  xi = Mole fraction of constituent i
#  Gi0 = Reference state of element i (molar Gibb's energy)
#  Gex = Excess Gibb's energy
#
# Going to use Al-Cu as an example/test case
#