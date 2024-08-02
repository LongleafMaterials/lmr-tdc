# -*- coding: utf-8 -*-
"""
Created on Thu Aug  1 21:01:00 2024

Takes path to JSON TDB and returns dataframes with
elements, parameters, and functions

@author: Colin-LMR
"""
import pandas as pd
import json
from urllib.request import urlopen

# Load JSON thermo data into dataframes
def loadData(url):
    # Read JSON
    tdb = json.loads(urlopen(url).read())
    
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