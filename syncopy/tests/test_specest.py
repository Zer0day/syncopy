# -*- coding: utf-8 -*-
#
# Test spectral estimation methods
#
# Created: 2019-06-17 09:45:47
# Last modified by: Stefan Fuertinger [stefan.fuertinger@esi-frankfurt.de]
# Last modification time: <2019-06-25 17:57:58>

import os
import tempfile
import pytest
import time
import numpy as np
from numpy.lib.format import open_memmap
from syncopy.datatype import AnalogData, SpectralData, StructDict, padding
from syncopy.datatype.base_data import VirtualData
from syncopy.shared.errors import SPYValueError, SPYTypeError
from syncopy.specest import freqanalysis
from syncopy.tests.misc import generate_artifical_data


class TestMTMFFT(object):

    # Construct simple trigonometric signal to check FFT consistency: each
    # channel is a sine wave of frequency `freqs[nchan]` with single unique
    # amplitude `amp` and sampling frequency `fs`
    nChannels = 32
    nTrials = 8
    fs = 1024
    fband = np.linspace(0, fs/2, int(np.floor(fs/2) + 1))
    freqs = np.random.choice(fband[1:-1], size=nChannels, replace=False)
    amp = np.pi
    phases = np.random.permutation(np.linspace(0, 2*np.pi, nChannels))
    t = np.linspace(0, nTrials, nTrials*fs)
    sig = np.zeros((t.size, nChannels), dtype="float32")
    for nchan in range(nChannels):
        sig[:, nchan] = amp*np.sin(2*np.pi*freqs[nchan]*t + phases[nchan])

    trialdefinition = np.zeros((nTrials, 3), dtype="int")
    for ntrial in range(nTrials):
        trialdefinition[ntrial, :] = np.array([ntrial*fs, (ntrial + 1)*fs, 0])

    adata = AnalogData(data=sig, samplerate=fs,
                       trialdefinition=trialdefinition)

    def test_output(self):
        # ensure that output type specification is respected
        spec = freqanalysis(self.adata, method="mtmfft", taper="hann",
                            output="fourier")
        assert "complex" in spec.data.dtype.name
        spec = freqanalysis(self.adata, method="mtmfft", taper="hann",
                            output="abs")
        assert "float" in spec.data.dtype.name
        spec = freqanalysis(self.adata, method="mtmfft", taper="hann",
                            output="pow")
        assert "float" in spec.data.dtype.name

    def test_solution(self):
        # ensure channel-specific frequencies are identified correctly
        spec = freqanalysis(self.adata, method="mtmfft", taper="hann",
                            output="pow")
        amps = np.empty((self.nTrials * self.nChannels,))
        k = 0
        for nchan in range(self.nChannels):
            for ntrial in range(self.nTrials):
                amps[k] = spec.data[ntrial, :, :, nchan].max() / self.t.size
                assert np.argmax(spec.data[ntrial, :, :, nchan]) == self.freqs[nchan]
                k += 1

        # ensure amplitude is consistent across all channels/trials
        assert np.all(np.diff(amps) < 1)

    def test_foi(self):
        # `foi` lims outside valid bounds
        with pytest.raises(SPYValueError):
            freqanalysis(self.adata, method="mtmfft", taper="hann",
                         foi=[0.5, self.fs/3])
        with pytest.raises(SPYValueError):
            freqanalysis(self.adata, method="mtmfft", taper="hann",
                         foi=[1, self.fs])

        foi = self.fband[1:int(self.fband.size / 3)]

        # offset `foi` by 0.1 Hz - resulting freqs must be unaffected
        ftmp = foi + 0.1
        spec = freqanalysis(self.adata, method="mtmfft", taper="hann", foi=ftmp)
        assert np.all(spec.freq == foi)

        # unsorted, duplicate entries in `foi` - result must stay the same
        ftmp = np.hstack([foi, np.full(20, foi[0])])
        spec = freqanalysis(self.adata, method="mtmfft", taper="hann", foi=ftmp)
        assert np.all(spec.freq == foi)

    def test_dpss(self):
        # ensure default setting results in multiple tapers
        spec = freqanalysis(self.adata, method="mtmfft", taper="dpss")
        assert spec.taper.size > 1
        assert np.unique(spec.taper).size == 1

        # specify tapers
        spec = freqanalysis(self.adata, method="mtmfft", taper="dpss",
                            tapsmofrq=7)
        assert spec.taper.size == 7

        # non-equidistant data w/multiple tapers
        cfg = StructDict()
        artdata = generate_artifical_data(nTrials=5, nChannels=16,
                                          equidistant=False, inmemory=False)
        cfg.method = "mtmfft"
        cfg.taper = "dpss"
        cfg.tapsmofrq = 9.3

        # ensure correctness of padding (respecting min. trial length)
        spec = freqanalysis(cfg, artdata)
        timeAxis = artdata.dimord.index("time")
        mintrlno = np.diff(artdata.sampleinfo).argmin()
        tmp = padding(artdata.trials[mintrlno], "zero", spec.cfg.pad,
                      spec.cfg.padlength, prepadlength=True)
        assert spec.freq.size == int(np.floor(tmp.shape[timeAxis] / 2) + 1)

        # same + reversed dimensional order in input object
        cfg.data = generate_artifical_data(nTrials=5, nChannels=16,
                                           equidistant=False, inmemory=False,
                                           dimord=AnalogData().dimord[::-1])
        cfg.output = "abs"
        cfg.keeptapers = False
        spec = freqanalysis(cfg)
        timeAxis = cfg.data.dimord.index("time")
        mintrlno = np.diff(cfg.data.sampleinfo).argmin()
        tmp = padding(cfg.data.trials[mintrlno], "zero", spec.cfg.pad,
                      spec.cfg.padlength, prepadlength=True)
        assert spec.freq.size == int(np.floor(tmp.shape[timeAxis] / 2) + 1)
        assert spec.taper.size == 1

        # same + overlapping trials
        cfg.data = generate_artifical_data(nTrials=5, nChannels=16,
                                           equidistant=False, inmemory=False,
                                           dimord=AnalogData().dimord[::-1],
                                           overlapping=True)
        cfg.keeptapers = False
        spec = freqanalysis(cfg)
        timeAxis = cfg.data.dimord.index("time")
        mintrlno = np.diff(cfg.data.sampleinfo).argmin()
        tmp = padding(cfg.data.trials[mintrlno], "zero", spec.cfg.pad,
                      spec.cfg.padlength, prepadlength=True)
        assert spec.freq.size == int(np.floor(tmp.shape[timeAxis] / 2) + 1)
        assert spec.taper.size == 1

    def test_allocout(self):
        # call ``freqanalysis`` w/pre-allocated output object
        out = SpectralData()
        freqanalysis(self.adata, method="mtmfft", taper="hann", out=out)
        assert len(out.trials) == self.nTrials
        assert out.taper.size == 1
        assert out.freq.size == self.fband.size
        assert out.channel.size == self.nChannels

        # build `cfg` object for calling
        cfg = StructDict()
        cfg.method = "mtmfft"
        cfg.taper = "hann"
        cfg.keeptrials = "no"
        cfg.output = "abs"
        cfg.out = SpectralData()

        # throw away trials
        freqanalysis(self.adata, cfg)
        assert len(cfg.out.time) == 1
        assert len(cfg.out.time[0]) == 1
        assert np.all(cfg.out.sampleinfo == [0, 1])

        # keep trials but throw away tapers
        out = SpectralData()
        freqanalysis(self.adata, method="mtmfft", taper="dpss",
                     keeptapers=False, output="abs", out=out)
        assert out.sampleinfo.shape == (self.nTrials, 2)
        assert out.taper.size == 1

        # re-use `cfg` from above and additionally throw away `tapers`
        cfg.dataset = self.adata
        cfg.out = SpectralData()
        cfg.taper = "dpss"
        cfg.keeptapers = False
        freqanalysis(cfg)
        assert cfg.out.taper.size == 1

    def test_slurm(self):
        pass

    def test_vdata(self):
        # test constant padding w/`VirtualData` objects (trials have identical lengths)
        with tempfile.TemporaryDirectory() as tdir:
            npad = 10
            fname = os.path.join(tdir, "dummy.npy")
            np.save(fname, self.sig)
            dmap = open_memmap(fname, mode="r")
            vdata = VirtualData([dmap, dmap])
            avdata = AnalogData(vdata, samplerate=self.fs,
                                trialdefinition=self.trialdefinition)
            spec = freqanalysis(avdata, method="mtmfft", taper="dpss",
                                keeptapers=False, output="abs", pad="relative",
                                padlength=npad)
            assert (np.diff(avdata.sampleinfo)[0][0] + npad)/2 + 1 == spec.freq.size

    # FIXME: check polyorder/polyremoval once supported
