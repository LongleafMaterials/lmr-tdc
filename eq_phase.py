# -*- coding: utf-8 -*-
"""
Experimenting with GPU-accelerated thermodynamic calculations for
calculation of equilibrium phase fractions

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
# json - handling TDB data
import pycuda.autoinit
import cupy as cp
import cutensor as ct
from urllib.request import urlopen
import json

# Retrieve COST507R JSON file
url = 'https://raw.githubusercontent.com/LongleafMaterials/lmr-tdc/main/tdb/COST507R.json'
tdb = json.loads(urlopen(url).read())
