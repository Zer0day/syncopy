# -*- coding: utf-8 -*-
# 
# Outsourced plotting class methods from respective parent classes
# 
# Created: 2020-05-06 13:32:40
# Last modified by: Stefan Fuertinger [stefan.fuertinger@esi-frankfurt.de]
# Last modification time: <2020-09-23 14:21:35>

import numpy as np
import os 

from syncopy.shared.errors import SPYValueError, SPYTypeError, SPYWarning
from syncopy.plotting.spy_plotting import (pltConfig, _layout_subplot_panels, 
                                           _prep_toilim_avg, _setup_figure, _prep_plots)
from syncopy import __plt__
if __plt__:
    import matplotlib.pyplot as plt

__all__ = []


def singlepanelplot(self, trials="all", channels="all", toilim=None, avg_channels=True,
                    title=None, grid=None, fig=None, **kwargs):
    """
    Plot contents of :class:`~syncopy.AnalogData` objects using single-panel figure(s)
    
    Please refer to :func:`syncopy.singlepanelplot` for detailed usage information. 
    
    Examples
    --------
    Use :func:`~syncopy.tests.misc.generate_artificial_data` to create two synthetic 
    :class:`~syncopy.AnalogData` objects. 
    
    >>> from syncopy.tests.misc import generate_artificial_data
    >>> adata = generate_artificial_data(nTrials=10, nChannels=32) 
    >>> bdata = generate_artificial_data(nTrials=5, nChannels=16) 
    
    Plot an average of the first 16 channels, averaged across trials 2, 4, and 6:
    
    >>> fig = spy.singlepanelplot(adata, channels=range(16), trials=[2, 4, 6])
   
    Overlay average of latter half of channels, averaged across trials 1, 3, 5: 

    >>> fig = spy.singlepanelplot(adata, channels=range(16,32), trials=[1, 3, 5], fig=fig)
    
    Do not average channels:
    
    >>> fig = spy.singlepanelplot(adata, channels=range(16,32), trials=[1, 3, 5], avg_channels=False)
    
    Plot `adata` and `bdata` simultaneously in two separate figures:
    
    >>> fig1, fig2 = spy.singlepanelplot(adata, bdata, overlay=False)
    
    Overlay `adata` and `bdata`; use channel and trial selections that are valid 
    for both datasets:
    
    >>> fig3 = spy.singlepanelplot(adata, bdata, channels=range(16), trials=[1, 2, 3])
    
    See also
    --------
    syncopy.singlepanelplot : visualize Syncopy data objects using single-panel plots
    """
    
    # Collect input arguments in dict `inputArgs` and process them
    inputArgs = locals()
    inputArgs.pop("self")
    dimArrs, dimCounts, idx, timeIdx, chanIdx = _prep_analog_plots(self, "singlepanelplot", **inputArgs)
    (nTrials, nChan) = dimCounts
    (trList, chArr) = dimArrs
    
    # If we're overlaying a multi-channel plot, ensure settings match up; also, 
    # do not try to overlay on top of multi-panel plots
    if hasattr(fig, "multipanelplot"):
        lgl = "single-panel figure generated by `singleplot`"
        act = "multi-panel figure generated by `multipanelplot`"
        raise SPYValueError(legal=lgl, varname="fig", actual=act)
    if hasattr(fig, "chanOffsets"):
        if avg_channels:
            lgl = "multi-channel plot"
            act = "channel averaging was requested for multi-channel plot overlay"
            raise SPYValueError(legal=lgl, varname="channels/avg_channels", actual=act)
        if nChan != len(fig.chanOffsets):
            lgl = "channel-count matching existing multi-channel panels in figure"
            act = "{} channels per panel but {} channels for plotting".format(len(fig.chanOffsets), 
                                                                              nChan)
            raise SPYValueError(legal=lgl, varname="channels/channels per panel", actual=act)

    # Ensure provided timing selection can actually be averaged (leverage 
    # the fact that `toilim` selections exclusively generate slices)
    if nTrials > 0:
        tLengths = _prep_toilim_avg(self)

    # Generic titles for figures
    overlayTitle = "Overlay of {} datasets"

    # Either create new figure or fetch existing
    if fig is None:
        if nTrials > 0:
            xLabel = "Time [s]"
        else:
            xLabel = "Samples"
        fig, ax = _setup_figure(1, xLabel=xLabel, grid=grid)
        fig.analogPlot = True
    else:
        ax, = fig.get_axes()        

    # Single-channel panel        
    if avg_channels:
        
        # Set up pieces of generic figure titles
        if nChan > 1:
            chanTitle = "Average of {} channels".format(nChan)
        else:
            chanTitle = chArr[0]
        
        # Plot entire timecourse
        if nTrials == 0:
            
            # Do not fetch entire dataset at once, but channel by channel
            chanSec = np.arange(self.channel.size)[self._selection.channel]
            pltArr = np.zeros((self.data.shape[timeIdx],), dtype=self.data.dtype)
            for chan in chanSec:
                idx[chanIdx] = chan
                pltArr += self.data[tuple(idx)].squeeze()
            pltArr /= nChan
            
            # The actual plotting command...
            ax.plot(pltArr)
            
            # Set plot title depending on dataset overlay
            if fig.objCount == 0:
                if title is None:
                    title = chanTitle
                ax.set_title(title, size=pltConfig["singleTitleSize"])
            else:
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles, labels)
                if title is None:
                    title = overlayTitle.format(len(handles))
                ax.set_title(title, size=pltConfig["singleTitleSize"])
                
        # Average across trials
        else:
        
            # Compute channel-/trial-average time-course: 2D array with slice/list
            # selection does not require fancy indexing - no need to check this here
            pltArr = np.zeros((tLengths[0],), dtype=self.data.dtype)
            for k, trlno in enumerate(trList):
                idx[timeIdx] = self._selection.time[k]
                pltArr += self._get_trial(trlno)[tuple(idx)].mean(axis=chanIdx).squeeze()
            pltArr /= nTrials
            
            # The actual plotting command is literally one line...
            time = self.time[trList[0]][self._selection.time[0]]
            ax.plot(time, pltArr, label=os.path.basename(self.filename))
            ax.set_xlim([time[0], time[-1]])
        
            # Set plot title depending on dataset overlay
            if fig.objCount == 0:
                if title is None:
                    if nTrials > 1:
                        trTitle = "{0}across {1} trials".format("averaged " if nChan == 1 else "",
                                                                nTrials)
                    else:
                        trTitle = "Trial #{}".format(trList[0])
                    title = "{}, {}".format(chanTitle, trTitle)
                ax.set_title(title, size=pltConfig["singleTitleSize"])
            else:
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles, labels)
                if title is None:
                    title = overlayTitle.format(len(handles))
                ax.set_title(title, size=pltConfig["singleTitleSize"])
    
    # Multi-channel panel
    else:

        # "Raw" data, do not respect any trials
        if nTrials == 0:
        
            # If required, compute max amplitude across provided channels
            if not hasattr(fig, "chanOffsets"):
                maxAmps = np.zeros((nChan,), dtype=self.data.dtype)
                tickOffsets = maxAmps.copy()
                chanSec = np.arange(self.channel.size)[self._selection.channel]
                for k, chan in enumerate(chanSec):
                    idx[chanIdx] = chan
                    pltArr = np.abs(self.data[tuple(idx)].squeeze())
                    maxAmps[k] = pltArr.max()
                    tickOffsets[k] = pltArr.mean()
                fig.chanOffsets = np.cumsum([0] + [maxAmps.max()] * (nChan - 1))
                fig.tickOffsets = fig.chanOffsets + tickOffsets.mean()

            # Do not plot all at once but cycle through channels to not overflow memory            
            for k, chan in enumerate(chanSec):
                idx[chanIdx] = chan
                ax.plot(self.data[tuple(idx)].squeeze() + fig.chanOffsets[k],
                        color=plt.rcParams["axes.prop_cycle"].by_key()["color"][fig.objCount],
                        label=os.path.basename(self.filename))
                if grid is not None:
                    ax.grid(grid)
                    
            # Set plot title depending on dataset overlay
            if fig.objCount == 0:
                if title is None:
                    if nChan > 1:
                        title = "Entire Data Timecourse of {} channels".format(nChan)
                    else:
                        title = "Entire Data Timecourse of {}".format(chArr[0])
                ax.set_yticks(fig.tickOffsets)
                ax.set_yticklabels(chArr)
                ax.set_title(title, size=pltConfig["singleTitleSize"])
            else:
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles[ : : (nChan + 1)], 
                          labels[ : : (nChan + 1)])
                if title is None:
                    title = overlayTitle.format(len(handles))
                ax.set_title(title, size=pltConfig["singleTitleSize"])

        # Average across trial(s)
        else:

            # Compute trial-average                
            pltArr = np.zeros((tLengths[0], nChan), dtype=self.data.dtype)
            for k, trlno in enumerate(trList):
                idx[timeIdx] = self._selection.time[k]
                pltArr += np.swapaxes(self._get_trial(trlno)[tuple(idx)], timeIdx, 0)
            pltArr /= nTrials

            # If required, compute offsets for multi-channel plot
            if not hasattr(fig, "chanOffsets"):
                fig.chanOffsets = np.cumsum([0] + [np.abs(pltArr).max()] * (nChan - 1))
                fig.tickOffsets = fig.chanOffsets + np.abs(pltArr).mean()

            # Plot the entire trial-averaged array at once
            time = self.time[trList[0]][self._selection.time[0]]
            ax.plot(time, 
                    (pltArr + fig.chanOffsets.reshape(1, nChan)).reshape(time.size, nChan),
                    color=plt.rcParams["axes.prop_cycle"].by_key()["color"][fig.objCount],
                    label=os.path.basename(self.filename))
            if grid is not None:
                ax.grid(grid)
                    
            # Set plot title depending on dataset overlay
            if fig.objCount == 0:
                if title is None:
                    title = "{0} channels {1}across {2} trials".format(nChan, 
                                                                       "averaged " if nTrials > 1 else "",
                                                                       nTrials)
                ax.set_title(title, size=pltConfig["singleTitleSize"])
            else:
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles[ : : (nChan + 1)], 
                          labels[ : : (nChan + 1)])
                if title is None:
                    title = overlayTitle.format(len(handles))
                ax.set_title(title, size=pltConfig["singleTitleSize"])
    
    # Increment overlay-counter and draw figure
    fig.objCount += 1
    plt.draw()
    self._selection = None
    return fig


def multipanelplot(self, trials="all", channels="all", toilim=None, avg_channels=False, 
              avg_trials=True, title=None, grid=None, fig=None, **kwargs):
    """
    Plot contents of :class:`~syncopy.AnalogData` objects using multi-panel figure(s)
    
    Please refer to :func:`syncopy.multipanelplot` for detailed usage information. 
    
    Examples
    --------
    Use :func:`~syncopy.tests.misc.generate_artificial_data` to create two synthetic 
    :class:`~syncopy.AnalogData` objects. 
    
    >>> from syncopy.tests.misc import generate_artificial_data
    >>> adata = generate_artificial_data(nTrials=10, nChannels=32) 
    >>> bdata = generate_artificial_data(nTrials=5, nChannels=16) 
    
    Show overview of first 5 channels, averaged across trials 2, 4, and 6:
    
    >>> fig = spy.multipanelplot(adata, channels=range(5), trials=[2, 4, 6])
   
    Overlay last 5 channels, averaged across trials 1, 3, 5: 

    >>> fig = spy.multipanelplot(adata, channels=range(27, 32), trials=[1, 3, 5], fig=fig)
    
    Do not average trials:
    
    >>> fig = spy.multipanelplot(adata, channels=range(27, 32), trials=[1, 3, 5], avg_trials=False)
    
    Plot `adata` and `bdata` simultaneously in two separate figures:
    
    >>> fig1, fig2 = spy.multipanelplot(adata, bdata, channels=range(5), overlay=False)
    
    Overlay `adata` and `bdata`; use channel and trial selections that are valid 
    for both datasets:
    
    >>> fig3 = spy.multipanelplot(adata, bdata, channels=range(5), trials=[1, 2, 3], avg_trials=False)
    
    See also
    --------
    syncopy.multipanelplot : visualize Syncopy data objects using multi-panel plots
    """
    
    # Collect input arguments in dict `inputArgs` and process them
    inputArgs = locals()
    inputArgs.pop("self")
    dimArrs, dimCounts, idx, timeIdx, chanIdx = _prep_analog_plots(self, "singlepanelplot", **inputArgs)
    (nTrials, nChan) = dimCounts
    (trList, chArr) = dimArrs

    # Get trial/channel count ("raw" plotting constitutes a special case)
    if trials is None:
        nTrials = 0
        if avg_trials:
            msg = "`trials` is `None` but `avg_trials` is `True`. " +\
                "Cannot perform trial averaging without trial specification - " +\
                "setting ``avg_trials = False``. " 
            SPYWarning(msg)
            avg_trials = False
        if avg_channels:
            msg = "Averaging across channels w/o trial specifications results in " +\
                "single-panel plot. Please use `singlepanelplot` instead"
            SPYWarning(msg)
            return

    # If we're overlaying, ensure settings match up
    if hasattr(fig, "singlepanelplot"):
        lgl = "overlay-figure generated by `multipanelplot`"
        act = "figure generated by `singlepanelplot`"
        raise SPYValueError(legal=lgl, varname="fig/singlepanelplot", actual=act)
    if hasattr(fig, "nTrialPanels"):
        if nTrials != fig.nTrialPanels:
            lgl = "number of trials to plot matching existing panels in figure"
            act = "{} panels but {} trials for plotting".format(fig.nTrialPanels, 
                                                                nTrials)
            raise SPYValueError(legal=lgl, varname="trials/figure panels", actual=act)
        if avg_trials:
            lgl = "overlay of multi-trial plot"
            act = "trial averaging was requested for multi-trial plot overlay"
            raise SPYValueError(legal=lgl, varname="trials/avg_trials", actual=act)
        if trials is None:
            lgl = "`trials` to be not `None` to append to multi-trial plot"
            act = "multi-trial plot overlay was requested but `trials` is `None`"
            raise SPYValueError(legal=lgl, varname="trials/overlay", actual=act)
        if not avg_channels and not hasattr(fig, "chanOffsets"):
            lgl = "single-channel or channel-averages for appending to multi-trial plot"
            act = "multi-trial multi-channel plot overlay was requested"
            raise SPYValueError(legal=lgl, varname="avg_channels/overlay", actual=act)
    if hasattr(fig, "nChanPanels"):
        if nChan != fig.nChanPanels:
            lgl = "number of channels to plot matching existing panels in figure"
            act = "{} panels but {} channels for plotting".format(fig.nChanPanels, 
                                                                  nChan)
            raise SPYValueError(legal=lgl, varname="channels/figure panels", actual=act)
        if avg_channels:
            lgl = "overlay of multi-channel plot"
            act = "channel averaging was requested for multi-channel plot overlay"
            raise SPYValueError(legal=lgl, varname="channels/avg_channels", actual=act)
        if not avg_trials:
            lgl = "overlay of multi-channel plot"
            act = "mulit-trial plot was requested for multi-channel plot overlay"
            raise SPYValueError(legal=lgl, varname="channels/avg_trials", actual=act)
    if hasattr(fig, "chanOffsets"):
        if avg_channels:
            lgl = "multi-channel plot"
            act = "channel averaging was requested for multi-channel plot overlay"
            raise SPYValueError(legal=lgl, varname="channels/avg_channels", actual=act)
        if nChan != len(fig.chanOffsets):
            lgl = "channel-count matching existing multi-channel panels in figure"
            act = "{} channels per panel but {} channels for plotting".format(len(fig.chanOffsets), 
                                                                              nChan)
            raise SPYValueError(legal=lgl, varname="channels/channels per panel", actual=act)

    # Generic title for overlay figures
    overlayTitle = "Overlay of {} datasets"

    # Either construct subplot panel layout/vet provided layout or fetch existing
    if fig is None:
        
        # Determine no. of required panels
        if avg_trials and not avg_channels:
            npanels = nChan 
        elif not avg_trials and avg_channels:
            npanels = nTrials
        elif not avg_trials and not avg_channels:
            npanels = int(nTrials == 0) * nChan + nTrials
        else:
            msg = "Averaging across both trials and channels results in " +\
                "single-panel plot. Please use `singlepanelplot` instead"
            SPYWarning(msg)
            return
        
        # Although, `_setup_figure` can call `_layout_subplot_panels` for us, we 
        # need `nrow` and `ncol` below, so do it here
        if nTrials > 0:
            xLabel = "Time [s]"
        else:
            xLabel = "Samples"
        nrow = kwargs.get("nrow", None)
        ncol = kwargs.get("ncol", None)
        nrow, ncol = _layout_subplot_panels(npanels, nrow=nrow, ncol=ncol)
        fig, ax_arr = _setup_figure(npanels, nrow=nrow, ncol=ncol, xLabel=xLabel, grid=grid)
        fig.analogPlot = True

    # Get existing layout
    else:
        ax_arr = fig.get_axes()
        nrow, ncol = ax_arr[0].numRows, ax_arr[0].numCols
        
    # Panels correspond to channels
    if avg_trials and not avg_channels:
        
        # Ensure provided timing selection can actually be averaged (leverage 
        # the fact that `toilim` selections exclusively generate slices)
        tLengths = _prep_toilim_avg(self)

        # Compute trial-averaged time-courses: 2D array with slice/list
        # selection does not require fancy indexing - no need to check this here
        pltArr = np.zeros((tLengths[0], nChan), dtype=self.data.dtype)
        for k, trlno in enumerate(trList):
            idx[timeIdx] = self._selection.time[k]
            pltArr += np.swapaxes(self._get_trial(trlno)[tuple(idx)], timeIdx, 0)
        pltArr /= nTrials
                
        # Cycle through channels and plot trial-averaged time-courses (time-
        # axis must be identical for all channels, set up `idx` just once)
        idx[timeIdx] = self._selection.time[0]
        time = self.time[trList[k]][self._selection.time[0]]
        for k, chan in enumerate(chArr):
            ax_arr[k].plot(time, pltArr[:, k], label=os.path.basename(self.filename))
            
        # If we're overlaying datasets, adjust panel- and sup-titles: include
        # legend in top-right axis (note: `ax_arr` is row-major flattened)
        if fig.objCount == 0:
            for k, chan in enumerate(chArr):
                ax_arr[k].set_title(chan, size=pltConfig["multiTitleSize"])
            fig.nChanPanels = nChan
            if title is None:
                if nTrials > 1:
                    title = "Average of {} trials".format(nTrials)
                else:
                    title = "Trial #{}".format(trList[0])
            fig.suptitle(title, size=pltConfig["singleTitleSize"])
        else:
            for k, chan in enumerate(chArr):
                ax_arr[k].set_title("{0}/{1}".format(ax_arr[k].get_title(), chan))
            ax = ax_arr[ncol - 1]
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles, labels)
            if title is None:
                title = overlayTitle.format(len(handles))
            fig.suptitle(title, size=pltConfig["singleTitleSize"])
            
    # Panels correspond to trials
    elif not avg_trials and avg_channels:
                
        # Cycle through panels to plot by-trial channel-averages
        for k, trlno in enumerate(trList):
            idx[timeIdx] = self._selection.time[k]
            time = self.time[trList[k]][self._selection.time[k]]
            ax_arr[k].plot(time, 
                           self._get_trial(trlno)[tuple(idx)].mean(axis=chanIdx).squeeze(),
                           label=os.path.basename(self.filename))

        # If we're overlaying datasets, adjust panel- and sup-titles: include
        # legend in top-right axis (note: `ax_arr` is row-major flattened)
        if fig.objCount == 0:
            for k, trlno in enumerate(trList):
                ax_arr[k].set_title("Trial #{}".format(trlno), size=pltConfig["multiTitleSize"])
            fig.nTrialPanels = nTrials
            if title is None:
                if nChan > 1:
                    title = "Average of {} channels".format(nChan)
                else:
                    title = chArr[0]
            fig.suptitle(title, size=pltConfig["singleTitleSize"])
        else:
            for k, trlno in enumerate(trList):
                ax_arr[k].set_title("{0}/#{1}".format(ax_arr[k].get_title(), trlno))
            ax = ax_arr[ncol - 1]
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles, labels)
            if title is None:
                title = overlayTitle.format(len(handles))
            fig.suptitle(title, size=pltConfig["singleTitleSize"])

    # Panels correspond to channels (if `trials` is `None`) otherwise trials
    elif not avg_trials and not avg_channels:
        
        # Plot each channel in separate panel
        if nTrials == 0:
            chanSec = np.arange(self.channel.size)[self._selection.channel]
            for k, chan in enumerate(chanSec):
                idx[chanIdx] = chan
                ax_arr[k].plot(self.data[tuple(idx)].squeeze(),
                               label=os.path.basename(self.filename))
                    
            # If we're overlaying datasets, adjust panel- and sup-titles: include
            # legend in top-right axis (note: `ax_arr` is row-major flattened)
            if fig.objCount == 0:
                for k, chan in enumerate(chArr):
                    ax_arr[k].set_title(chan, size=pltConfig["multiTitleSize"])
                fig.nChanPanels = nChan
                if title is None:
                    title = "Entire Data Timecourse"
                fig.suptitle(title, size=pltConfig["singleTitleSize"])
            else:
                for k, chan in enumerate(chArr):
                    ax_arr[k].set_title("{0}/{1}".format(ax_arr[k].get_title(), chan))
                ax = ax_arr[ncol - 1]
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles, labels)
                if title is None:
                    title = overlayTitle.format(len(handles))
                fig.suptitle(title, size=pltConfig["singleTitleSize"])
        
        # Each trial gets its own panel w/multiple channels per panel
        else:

            # If required, compute max amplitude across provided trials + channels
            if not hasattr(fig, "chanOffsets"):
                maxAmps = np.zeros((nTrials,), dtype=self.data.dtype)
                tickOffsets = maxAmps.copy()
                for k, trlno in enumerate(trList):
                    idx[timeIdx] = self._selection.time[k]
                    pltArr = np.abs(self._get_trial(trlno)[tuple(idx)])
                    maxAmps[k] = pltArr.max()
                    tickOffsets[k] = pltArr.mean()
                fig.chanOffsets = np.cumsum([0] + [maxAmps.max()] * (nChan - 1))
                fig.tickOffsets = fig.chanOffsets + tickOffsets.mean()
            
            # Cycle through panels to plot by-trial multi-channel time-courses
            for k, trlno in enumerate(trList):
                idx[timeIdx] = self._selection.time[k]
                time = self.time[trList[k]][self._selection.time[k]]
                pltArr = np.swapaxes(self._get_trial(trlno)[tuple(idx)], timeIdx, 0)
                ax_arr[k].plot(time, 
                               (pltArr + fig.chanOffsets.reshape(1, nChan)).reshape(time.size, nChan), 
                               color=plt.rcParams["axes.prop_cycle"].by_key()["color"][fig.objCount],
                               label=os.path.basename(self.filename))

            # If we're overlaying datasets, adjust panel- and sup-titles: include
            # legend in top-right axis (note: `ax_arr` is row-major flattened)
            # Note: y-axis is shared across panels, so `yticks` need only be set once
            if fig.objCount == 0:
                for k, trlno in enumerate(trList):
                    ax_arr[k].set_title("Trial #{}".format(trlno), size=pltConfig["multiTitleSize"])
                ax_arr[0].set_yticks(fig.tickOffsets)
                ax_arr[0].set_yticklabels(chArr)
                fig.nTrialPanels = nTrials
                if title is None:
                    if nChan > 1:
                        title = "{} channels".format(nChan)
                    else:
                        title = chArr[0]
                fig.suptitle(title, size=pltConfig["singleTitleSize"])
            else:
                for k, trlno in enumerate(trList):
                    ax_arr[k].set_title("{0}/#{1}".format(ax_arr[k].get_title(), trlno))
                ax_arr[0].set_yticklabels([" "] * chArr.size)
                ax = ax_arr[ncol - 1]
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles[ : : (nChan + 1)], 
                          labels[ : : (nChan + 1)])
                if title is None:
                    title = overlayTitle.format(len(handles))
                fig.suptitle(title, size=pltConfig["singleTitleSize"])
    
    # Increment overlay-counter, draw figure and wipe data-selection slot
    fig.objCount += 1
    plt.draw()
    self._selection = None
    return fig


def _prep_analog_plots(self, name, **inputArgs):
    """
    Local helper that performs sanity checks and sets up data selection

    Parameters
    ----------
    self : :class:`~syncopy.AnalogData` object
        Syncopy :class:`~syncopy.AnalogData` object that is being processed by 
        the respective :meth:`.singlepanelplot` or :meth:`.multipanelplot` class methods
        defined in this module. 
    name : str
        Name of caller (i.e., "singlepanelplot" or "multipanelplot")
    inputArgs : dict
        Input arguments of caller (i.e., :meth:`.singlepanelplot` or :meth:`.multipanelplot`)
        collected in dictionary
        
    Returns
    -------
    dimArrs : tuple
        Tuple containing (in this order) `trList`, list of (selected) 
        trials to visualize and `chArr`, 1D :class:`numpy.ndarray` of channel specifiers
        based on provided user selection. Note that `"all"` and `None` selections 
        are converted to arrays ready for indexing. 
    dimCounts : tuple
        Tuple holding sizes of corresponding selection arrays comprised
        in `dimArrs`. Elements are `nTrials`, number of (selected) trials and `nChan`, 
        number of (selected) channels. 
    idx : list
        Three element indexing list (respecting non-default `dimord`s) intended 
        for use with trial-array data. 
    timeIdx : int
        Position of time-axis within indexing list `idx` (either 0 or 1). 
    chanIdx : int
        Position of channel-axis within indexing list `idx` (either 0 or 1). 
        
    Notes
    -----
    This is an auxiliary method that is intended purely for internal use. Please
    refer to the user-exposed methods :func:`~syncopy.singlepanelplot` and/or
    :func:`~syncopy.multipanelplot` to actually generate plots of Syncopy data objects. 
        
    See also
    --------
    :meth:`syncopy.plotting.spy_plotting._prep_plots` : General basic input parsing for all Syncopy plotting routines
    """
    
    # Basic sanity checks for all plotting routines w/any Syncopy object
    _prep_plots(self, name, **inputArgs)
    
    # Ensure our binary flags are actually binary
    if not isinstance(inputArgs["avg_channels"], bool):
        raise SPYTypeError(inputArgs["avg_channels"], varname="avg_channels", expected="bool")
    if not isinstance(inputArgs.get("avg_trials", True), bool):
        raise SPYTypeError(inputArgs["avg_trials"], varname="avg_trials", expected="bool")

    # Pass provided selections on to `Selector` class which performs error 
    # checking and generates required indexing arrays
    self._selection = {"trials": inputArgs["trials"],
                       "channels": inputArgs["channels"],
                       "toilim": inputArgs["toilim"]}

    # Ensure any optional keywords controlling plotting appearance make sense
    if inputArgs["title"] is not None:
        if not isinstance(inputArgs["title"], str):
            raise SPYTypeError(inputArgs["title"], varname="title", expected="str")
    if inputArgs["grid"] is not None:
        if not isinstance(inputArgs["grid"], bool):
            raise SPYTypeError(inputArgs["grid"], varname="grid", expected="bool")

    # Get trial and channel counts
    if inputArgs["trials"] is None:
        trList = []
        nTrials = 0
        if inputArgs["toilim"] is not None:
            lgl = "`trials` to be not `None` to perform timing selection"
            act = "`toilim` was provided but `trials` is `None`"
            raise SPYValueError(legal=lgl, varname="trials/toilim", actual=act)
    else:    
        trList = self._selection.trials
        nTrials = len(trList)
    chArr = self.channel[self._selection.channel]
    nChan = chArr.size

    # Collect arrays and counts in tuples
    dimCounts = (nTrials, nChan)
    dimArrs = (trList, chArr)

    # Prepare indexing list respecting potential non-default `dimord`s
    idx = [slice(None), slice(None)]
    chanIdx = self.dimord.index("channel")
    timeIdx = self.dimord.index("time")
    idx[chanIdx] = self._selection.channel

    return dimArrs, dimCounts, idx, timeIdx, chanIdx
