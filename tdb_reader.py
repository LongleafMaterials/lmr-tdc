# -*- coding: utf-8 -*-
"""
*** INCOMPLETE ***

Read and parse thermodynamic database (.TDB) files
NOTE: TDB formats are inconsistent, so this does not need to be able to handle
      everything. Method can read COST507R, a common TDB.

Created on Mon Jul 29 20:46:37 2024

@author: Colin-LMR
"""
import io
import requests
import pandas as pd
import re
import json

## Clean data
def cleanTDB(tdb):
    # Split tdb into lines by '\n'
    tdbLines = tdb.split('\n')
    
    # Add space around semicolons then delete - helps capture groups
    #tdbLines = [r.replace(';',' ; ') for r in tdbLines]
    #tdbLines = [r.replace(';','') for r in tdbLines]
    
    # Remove dollar signs and whitespace from beginning of each row
    tdbLines = [r.replace('$','').lstrip() for r in tdbLines]
    
    # Recombine lines and split by exclamation points
    tdbLines =  ''.join(tdbLines).split('!')
    
    # Remove remaining white space after rejoining
    tdbLines = [r.lstrip() for r in tdbLines]
    
    return tdbLines

### Extract elements, phase names, and parameters
# Data structure for a single element entry:
# {
# 'element': <element name>,
# 'phase': <phase name>,
# 'atomic_mass': <atomic mass of element>,
# 'H298-H0': <standard enthalpy relative to 298K for element>,
# 'S298': <standard absolute entropy for element>
# }
#
def getElements(tdbLines):
    # Extract lines containing element data
    tdbLines = [line[8:] for line in tdbLines if line[:7] == 'ELEMENT']
    
    # Convert cleaned TDB to IO so it can be read by pandas
    buffer = io.StringIO('\n'.join(tdbLines))
    
    # Read lines into dataframe
    elements = pd.read_fwf(buffer, header=None, colspecs='infer')

    # Rename columns
    elements.columns = ['element',
                        'phase',
                        'atomic_mass',
                        'H298-H0',
                        'S298']
    
    # Create structured data
    dataStruct = []
    for i in elements.index:
        item = elements.iloc[i]
        dataStruct.append({'element': item.element,
                           'phase': item.phase,
                           'atomic_mass': item.atomic_mass,
                           'H298-H0': item['H298-H0'],
                           'S298': item.S298})
    return dataStruct

### Extract functions
# Data structure for a single function entry:
# {
# 'name': <function name>,
# 'functions': [{'function': <calculation function>,      
#                'max_temp': <upper temperature bound for function>,
#                'min_temp': <lower temperature bound for function>},
#               ...]
# }
#
def getFunctions(tdbLines):
    # Remove "FUNCT" and "FUNCTION" from beginning of lines (may not be necessary)
    tdbLines = [x.replace('FUNCT ', 'FUNCTION ')[9:] for x in [line.replace('\n','') for line in tdbLines if line[:5] == 'FUNCT']]
       
    # Add space ahead of semicolons to help capture groups
    tdbLines = [x.replace(';', ' ;') for x in tdbLines]
    
    # Replace unnecessary characters to facilitate parsing
    chars = ['Y', ';']
    for c in chars:
        tdbLines = [x.replace(c, '') for x in tdbLines]
    
    # Create structured data
    dataStruct = []
    
    for item in tdbLines:
        # Break into word/character groups
        text = re.findall(r'([\S]+)', item)
        
        # Delete any items in the list after, and including, "N"
        text = text[:text.index('N')]
        
        # Initialize data element with name of function
        elem = {'name': text[0],
                'functions': []}
        
        # Extract temperature ranges and functions for remaining entries
        # Based on format, even index are functions, and adjacent indices are bounding temperatures
        for i in list(range(2,len(text),2)):
            elem['functions'].append({'min_temp': text[i-1], 
                                      'max_temp': text[i+1],
                                      'function': text[i]})
        
        # Add data element to structure
        dataStruct.append(elem)
    
    # Return data
    return dataStruct

### Extract parameters
# Data structure for a single parameter entry:
# {
# 'name': <parameter name>,
# 'parameters': [{'function': <calculation function>,      
#                 'max_temp': <upper temperature bound for function>,
#                 'min_temp': <lower temperature bound for function>},
#                ...]
# }
#
def getParameters(tdbLines):
    # Remove "PARAMETER" from beginning of lines
    tdbLines = [x.replace('PARAM ', 'PARAMETER ')[10:] for x in [line.replace('\n','') for line in tdbLines if line[:5] == 'PARAM']]
  
    # Replace unnecessary characters to facilitate parsing
    chars = ['Y']
    for c in chars:
        tdbLines = [x.replace(c, '') for x in tdbLines]
    
    # Create structured data
    dataStruct = []
        
    for item in tdbLines:
        # Replace semicolons after the closing parentheses to split groups
        item = item[:item.find(')')] + item[item.find(')'):].replace(';',' ')
        
        # Break into word/character groups
        text = re.findall(r'([\S]+)', item)
        
        # Delete any items in the list after, and including, "N" (may not be present)
        text = text[:text.index('N')]
        
        # Initialize data element with name of function
        elem = {'name': text[0],
                'parameters': []}
        
        # Extract temperature ranges and functions for remaining entries
        # Based on format, even index are functions, and adjacent indices are bounding temperatures
        for i in list(range(2,len(text),2)):
            elem['parameters'].append({'min_temp': text[i-1], 
                                       'max_temp': text[i+1],
                                       'function': text[i]})
        
        # Add data element to structure
        dataStruct.append(elem)

    return dataStruct

### Extract phases and constituents
# Data structure for a single phase entry:
#   {
#   'phase': <phasename>,
#   'sublattices': <number of sublattices>,
#   'stoichiomery': [<stoichiometry for each sublattice>],
#   'constituents': [{'constituent': <element(s)>},
#                    {'constituent': <element(s)>},
#                    ...]
#   }
#
def getPhases(tdbLines):
    # Reduce list to rows which contain phases and constituents
    tdbLines = [r for r in tdbLines if any([r[:5] == 'PHASE', r[:5] == 'CONST'])]
    
    # Initialize data structure
    dataStruct = []
    
    # Lines defining phase and constituents appear in pairs, with CONSTITUENT line
    # following a PHASE line. Isolate each type and then process in pairs.
    phases = [tdbLines[i][5:].strip() for i in range(0,len(tdbLines),2)]
    constituents = [tdbLines[i][11:].strip() for i in range(1,len(tdbLines),2)] 
    for p, c in zip(phases, constituents):
        #print(p, c)
        # Split phase information into list
        phaseList = [i for i in p.split(' ') if len(i)>0]
        
        ## Extract information from phase data
        phaseName = phaseList[0]
        try:
            numSubl = phaseList[phaseList.index('%')+1]
            stoich = phaseList[phaseList.index('%')+2:]
        except:
            # Handle error if '%' is paired with another symbol/character
            # Instead of finding exact match '%', find index of list item that
            # contains '%'
            ind = [phaseList.index(i) for i in phaseList if i.find('%')>=0][0]
            numSubl = phaseList[ind+1]
            stoich = phaseList[ind+2:]
        
        ## Extract information from constituents
        # Split constituents using colon ":"
        c = [i.strip() for i in c.split(':')]
        
        # Remove blank/empty list items
        c = [i for i in c if len(i)>0]
            
        # Create a list of dictionaries for constituents
        # May need to strip remaining '%' from list items ***
        const = [{'constituent': i} for i in c]
        
        # Add data to data structure
        data = {'phase': phaseName,
                'sublattices': numSubl,
                'stoichiometry': stoich,
                'constituents': const}
        
        dataStruct.append(data)
    
#%%   
# Retrieve COST507R TDB file
url = 'https://raw.githubusercontent.com/colin-lmr/lmr-tdc/main/tdb/cost507R.TDB'
tdb = requests.get(url).text
 
# Clean TDB for processing
tdbLines = cleanTDB(tdb)

# Retrieve data from TDB
elems = getElements(tdbLines)
fns = getFunctions(tdbLines)
params = getParameters(tdbLines)
phases = getPhases(tdbLines)

# Combine data and save as TDJ, (T)hermo(D)ynamic (J)SON
# Data structure is expected to change once computation code develops
# Need to add data citations if using this as a file format ***
tdj = {'elements': elems,
       'functions': fns,
       'parameters': params,
       'phases': phases}
path = 'C:\\Users\\Fletcher\\OneDrive - Longleaf Materials Research\\Documents\\Longleaf Materials Research\\Projects\\lmr-tdc\\tdb\\'
with open(path + 'COST507R.json', 'w', encoding='utf-8') as f:
    json.dump(tdj, f, ensure_ascii=False, indent=4)


#%% Function time testing
import timeit
#e = re.compile('([\S]+)')
def test():
    #[x.replace('FUNCT ', 'FUNCTION ')[9:] for x in [line for line in tdbLines if line[:5] == 'FUNCT']]
  
    for item in tdbLines:
        name = re.findall('([\S]+)', item)
        #name = [it for it in item.split(' ') if len(it)>1]
        print(name)

timeit.timeit('test()', setup='from __main__ import test', number=10000)

