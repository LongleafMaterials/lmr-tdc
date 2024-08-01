# -*- coding: utf-8 -*-
"""
*** Functioning work-in-progress ***

Read thermodynamic database (.TDB) file and convert to JSON
NOTE: This was intended to parse COST507R. TDB formats are inconsistent, 
      so other databases may not parse properly or at all. 

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
            elem['functions'].append({'min_temp': float(text[i-1]), 
                                      'max_temp': float(text[i+1]),
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
        ## Extract information in parentheses
        # L is L-Parameter (L0, L1, L2)
        paren = item[item.find('(')+1:item.find(';')]
        L = int(item[item.find(';')+1:item.find(')')])
        
        # Extract letter ahead of parentheses 
        # Means unary or mixing, but does not seem consistent for CALPHAD software
        mix = item[0]
        
        # Replace comma with colon and split
        paren = paren.replace(',',':')
        paren = paren.split(':')
        
        # First item in split list is the phase name
        phaseName = paren[0]
        
        # The rest of the split list are species for each lattice site
        species = []
        for i, s in enumerate(paren[1:]):
            species.append({i: s})
        
        ## Extract function and temperatures
        # Extract text after parentheses and clean semicolons(';')
        text = item[item.find(')')+1:]
        text = text.replace(';',' ')
            
        # Break into word/character groups
        text = [i for i in text.split(' ') if len(i)>0]
        #text = re.findall(r'([\S]+)', text)
        
        # Check text for 'REF' and note, if present
        for t in text:
            if 'REF' in t:
                ref = t
            else:
                ref = None
        
        # Delete any items in the list after, and including, "N" (may not be present)
        text = text[:text.index('N')]
        
        # First and last items in remaining list should be lower and upper temperatures, respectively
        # Second item should be function
        lowTemp = float(text[0])
        highTemp = float(text[2])
        function = text[1]
    
        # Initialize data element with name of function
        functions = {'phase': phaseName,
                     'mixing': mix,
                     'species': species,
                     'L': L,
                     'lower_temp': lowTemp,
                     'upper_temp': highTemp,
                     'function': function,
                     'ref': ref}
        
        # Add data element to structure
        dataStruct.append(functions)

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
    ## Retrieve phase parameter data (will be added to each entry) and 
    ## create dataframe for reference
    parameters = getParameters(tdbLines)
    phaseNames = [i['phase'] for i in parameters]
    phaseData = pd.DataFrame({'name': phaseNames,
                              'params': parameters})
    
    # Reduce list to rows which contain phases and constituents
    tdbLines = [r for r in tdbLines if any([r[:5] == 'PHASE', r[:5] == 'CONST'])]
    
    # Initialize data structure
    dataStruct = []
    
    # Lines defining phase and constituents appear in pairs, with CONSTITUENT line
    # following a PHASE line. Isolate each type and then process in pairs.
    phases = [tdbLines[i][5:].strip() for i in range(0,len(tdbLines),2)]
    constituents = [tdbLines[i][11:].replace(' ','') for i in range(1,len(tdbLines),2)] 
    
    # Iterature through each phase/constituent combination and extract relevant information
    for p, c in zip(phases, constituents):
        # Split phase information into list
        phaseList = [i for i in p.split(' ') if len(i)>0]
        
        ## Extract sublattice information
        # List of dictionaries:
        # [{site: <site #>, stoichiometry: <site stoichometry>, constituents: <[elements]>}, ...]
        
        # Initialize sublattice list
        sublattice = []
        
        # Retrieve number of sublattices
        try:
            index = phaseList.index('%') + 1
            numSublattices = int(phaseList[index])
        except:
            # Error handling if '%' is grouped with another character
            index = [phaseList.index(i) for i in phaseList if '%' in i][0] + 1
            numSublattices = int(phaseList[index])
    
        # Split constituent entries
        const = [i for i in c.split(':') if len(i)>0] 
    
        # Place sublattice site information in dictionaries
        for i in range(1,numSublattices+1):
            # Get stoichiometry for sublattice
            sublattice.append({'site': i,
                               'constituents': const[i].replace('%','').split(','),
                               'stoichiometry': phaseList[i+1]})
            
        ## Extract information from phase data
        phaseName = phaseList[0]
        if phaseName == 'LIQUID:L':
            phaseName = 'LIQUID'
       
        ## Extract information from constituents
        # Split constituents using colon ":"
        const = [i.strip() for i in c.split(':')]
        
        # Remove blank/empty list items
        const = [i for i in const if len(i)>0]
            
        # Remove phase from constituents
        const = [i for i in const[1:]]
        
        # Identify major constituents and remove '%'
        majConst = []
        for i in const:
            # Split each group of constituents and look for major
            temp = i.split(',')
            for j in temp:
                # Add to list if '%' is found (indicates major constituent)
                if '%' in j:
                    majConst.append(j.replace('%',''))
        
        # Create a list of dictionaries for constituents
        # May need to strip remaining '%' from list items ***
        const = [i.replace('%','') for i in const]
        const = [{'constituent': [i]} for i in const]
    
        # Change major constituent value if empty
        if len(majConst) == 0:
            majConst = None
        
        # Find matching parameter data
        param = phaseData[phaseData['name'] == phaseName]['params'].tolist()
        
        # Add data to data structure
        data = {'phase': phaseName,
                'sublattice': sublattice,
                'constituents': const, # Redundant to site constituents - is this necessary or helpful?
                'major_constituents': majConst,
                'parameters': param}
        #print(data)
    
        dataStruct.append(data)
            
    return dataStruct

### Compile TDB data in JSON format
def buildJSON(tdb):
    # Clean TDB for processing
    tdbLines = cleanTDB(tdb)
    
    # Retrieve data from TDB
    elements = getElements(tdbLines)
    functions = getFunctions(tdbLines)
    #params = getParameters(tdbLines)
    phases = getPhases(tdbLines)
    
    data = {'elements': elements, 
            'phases': phases,
            'functions': functions}
    
    return data
   
#%% Test section
import io
import requests
import pandas as pd
import re
import json

# Retrieve COST507R TDB file
url = 'https://raw.githubusercontent.com/colin-lmr/lmr-tdc/main/tdb/cost507R.TDB'
tdb = requests.get(url).text
 
# Clean TDB for processing
#tdbLines = cleanTDB(tdb)

# Retrieve data from TDB
#elems = getElements(tdbLines)
#fns = getFunctions(tdbLines)
#params = getParameters(tdbLines)
#phases = getPhases(tdbLines)

# Combine data and save as TDJ, (T)hermo(D)ynamic (J)SON
# Data structure is expected to change once computation code develops
# Need to add data citations if using this as a file format ***
data = buildJSON(tdb)

path = 'C:\\Users\\Fletcher\\OneDrive - Longleaf Materials Research\\Documents\\Longleaf Materials Research\\Projects\\lmr-tdc\\tdb\\'
with open(path + 'COST507R.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

