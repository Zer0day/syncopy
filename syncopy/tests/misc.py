# -*- coding: utf-8 -*-
#
# Helper methods for testing routines
#
# Created: 2019-04-18 14:41:32
# Last modified by: Stefan Fuertinger [stefan.fuertinger@esi-frankfurt.de]
# Last modification time: <2019-09-06 16:28:43>

import subprocess
import sys
import os
import h5py
import tempfile
import numpy as np

# Local imports
from syncopy.datatype import AnalogData
from syncopy.shared.filetypes import _data_classname_to_extension, FILE_EXT
from syncopy import __plt__
if __plt__:
    import matplotlib.pyplot as plt


def is_win_vm():
    """
    Returns `True` if code is running on virtual Windows machine, `False`
    otherwise
    """

    # If we're not running on Windows abort
    if sys.platform != "win32":
        return False

    # Use the windows management instrumentation command-line to extract machine manufacturer
    out, err = subprocess.Popen("wmic computersystem get manufacturer",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, shell=True).communicate()

    # If the vendor name contains any "virtual"-flavor, we're probably running
    # in a VM - if the above command triggered an error, abort
    if len(err) == 0:
        vendor = out.split()[1].lower()
        vmlist = ["vmware", "virtual", "virtualbox", "vbox", "qemu"]
        return any([virtual in vendor for virtual in vmlist])
    else:
        return False


def is_slurm_node():
    """
    Returns `True` if code is running on a SLURM-managed cluster node, `False`
    otherwise
    """

    # Simply test if the srun command is available
    out, err = subprocess.Popen("srun --version",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, shell=True).communicate()
    if len(out) > 0:
        return True
    else:
        return False

    
def generate_artificial_data(nTrials=2, nChannels=2, equidistant=True, seed=None,
                             overlapping=False, inmemory=True, dimord="default"):
    """
    Parameters
    ----------
    nTrials : int

    Populate `AnalogData` object w/ artificial signal
    """

    # Create dummy 1d signal that will be blown up to fill channels later
    dt = 0.001
    t = np.arange(0, 3, dt, dtype="float32") - 1.0
    sig = np.cos(2 * np.pi * (7 * (np.heaviside(t, 1) * t - 1) + 10) * t)

    # Depending on chosen `dimord` either get default position of time-axis
    # in `AnalogData` objects or use provided `dimord` and reshape signal accordingly
    if dimord == "default":
        dimord = AnalogData._defaultDimord
    timeAxis = dimord.index("time")
    idx = [1, 1]
    idx[timeAxis] = -1
    sig = np.repeat(sig.reshape(*idx), axis=idx.index(1), repeats=nChannels)

    # Initialize random number generator (with possibly user-provided seed-value)    
    rng = np.random.default_rng(seed)    

    # Either construct the full data array in memory using tiling or create
    # an HDF5 container in `__storage__` and fill it trial-by-trial
    # NOTE: use `swapaxes` here to ensure two objects created w/same seed really 
    # are affected w/identical additive noise patterns, no matter their respective 
    # `dimord`.
    out = AnalogData(samplerate=1/dt, dimord=dimord)
    if inmemory:
        idx[timeAxis] = nTrials 
        sig = np.tile(sig, idx)
        shp = [slice(None), slice(None)]
        for iTrial in range(nTrials):
            shp[timeAxis] = slice(iTrial*t.size, (iTrial + 1)*t.size)
            noise = rng.standard_normal((t.size, nChannels)).astype(sig.dtype) * 0.5
            sig[tuple(shp)] += np.swapaxes(noise, timeAxis, 0) 
        out.data = sig
    else:
        with h5py.File(out.filename, "w") as h5f:
            shp = list(sig.shape)
            shp[timeAxis] *= nTrials
            dset = h5f.create_dataset("data", shape=tuple(shp), dtype=sig.dtype)
            shp = [slice(None), slice(None)]
            for iTrial in range(nTrials):
                shp[timeAxis] = slice(iTrial*t.size, (iTrial + 1)*t.size)
                noise = rng.standard_normal((t.size, nChannels)).astype(sig.dtype) * 0.5
                dset[tuple(shp)] = sig + np.swapaxes(noise, timeAxis, 0) 
                dset.flush()
        out.data = h5py.File(out.filename, "r+")["data"]

    # Define by-trial offsets to generate (non-)equidistant/(non-)overlapping trials
    trialdefinition = np.zeros((nTrials, 3), dtype='int')
    if equidistant:
        equiOffset = 0
        if overlapping:
            equiOffset = 100
        offsets = np.full((nTrials,), equiOffset, dtype=sig.dtype)
    else:
        offsets = rng.integers(low=int(0.1*t.size), high=int(0.2*t.size), size=(nTrials,))

    # Using generated offsets, construct trialdef array and make sure initial
    # and end-samples are within data bounds (only relevant if overlapping
    # trials are built)
    shift = (-1)**(not overlapping)
    for iTrial in range(nTrials):
        trialdefinition[iTrial, :] = np.array([iTrial*t.size - shift*offsets[iTrial],
                                               (iTrial + 1)*t.size + shift*offsets[iTrial],
                                               1000])
    if equidistant:
        trialdefinition[0, :2] += equiOffset
        trialdefinition[-1, :2] -= equiOffset
    else:
        trialdefinition[0, 0] = 0
        trialdefinition[-1, 1] = nTrials*t.size
    out.definetrial(trialdefinition)

    return out


def construct_spy_filename(basepath, obj):
    basename = os.path.split(basepath)[1]
    objext = _data_classname_to_extension(obj.__class__.__name__)
    return os.path.join(basepath + FILE_EXT["dir"], basename + objext)

    
def figs_equal(fig1, fig2, tol=None):
    """
    Test if two figures are identical
    
    Parameters
    ----------
    fig1 : matplotlib figure object
        Reference figure
    fig2 : matplotlib figure object
        Template figure
    tol : float
        Positive scalar (b/w 0 and 1) specifying tolerance level for considering 
        `fig1` and `fig2` identical. If `None`, two figures have to be exact 
        pixel-perfect copies to be qualified as identical. 
    
    Returns
    -------
    equal : bool
        `True` if `fig1` and `fig2` are identical, `False` otherwise
        
    Notes
    -----
    This is an auxiliary method that is intended purely for internal use. Thus, 
    no error checking is performed. 
    
    Examples
    --------
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> x = np.linspace(0, 2*np.pi, 100)
    >>> fig1 = plt.figure(); plt.plot(x, np.sin(x))
    >>> figs_equal(fig1, fig1)
    True
    >>> fig2 = plt.figure(); plt.plot(x, np.sin(x), color="red")
    >>> figs_equal(fig1, fig2)
    False
    >>> figs_equal(fig1, fig2, tol=0.9)
    True
    """
    with tempfile.NamedTemporaryFile(suffix='.png') as img1:
        with tempfile.NamedTemporaryFile(suffix='.png') as img2:
            fig1.savefig(img1.name)
            fig2.savefig(img2.name)
            if tol is None:
                return np.array_equal(plt.imread(img1.name), plt.imread(img2.name))
            return np.allclose(plt.imread(img1.name), plt.imread(img2.name), atol=tol)
    