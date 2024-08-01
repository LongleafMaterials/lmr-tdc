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
import pycuda.autoinit
import cupy as cp
import cutensor as ct

