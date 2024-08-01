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
import pycuda.autoinit
import cupy as cp
import cutensor as ct
from urllib.request import urlopen
import json
import pandas as pd

# Retrieve COST507R JSON file
url = 'https://raw.githubusercontent.com/LongleafMaterials/lmr-tdc/main/tdb/COST507R.json'
tdb = json.loads(urlopen(url).read())

# Load JSON thermo data into dataframes
def loadData(tdb):
    # Load element data
    elem = pd.DataFrame(tdb['elements'])
    
    # Load and prepare parameter data
    param = []
    for i in tdb['phases']:
        param += i['parameters']
    param = pd.DataFrame(param)    
    
    # Load function data
    func = []
    fName = []
    for i in tdb['functions']:
        func += i['functions']
        fName += len(i['functions']) * [i['name']]
    func = pd.DataFrame(func)
    func.insert(0, 'name', fName)
    for c in ['min_temp', 'max_temp']:
        func[c] = func[c].astype(float)
    
    return (elem, param, func)

# Run thermo function with specified name and temperature
def fCalc(name, T):
    # Retrieve function matching specified name and temperature
    f = func.loc[(func['name'] == name) & 
                 (func['min_temp'] <= T) &
                 (func['max_temp'] >= T)]['function'].values[0]    

    

# Test variables
name = 'GHSERBB'
temp = 1215

# Load data into dataframes
elem, param, func = loadData(tdb)

#%%

T = temp
f = func.loc[(func['name'] == name) & 
             (func['min_temp'] <= temp) &
             (func['max_temp'] >= temp)]['function'].values[0]
    
eval(f)

### Equilibrium for binary system
# For a binary system:
#  G = Σ(xi * Gi0) + RT*Σ(xi*ln(xi)) + Gex
#  xi = Mole fraction of constituent i
#  Gi0 = Reference state of element i (molar Gibb's energy)
#  Gex = Excess Gibb's energy
#
# Going to use Al-Cu as an example/test case
#