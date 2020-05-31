
from distutils.util import strtobool

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy as sp
from bokeh.plotting import figure, output_notebook, show
from scipy.optimize import fmin

from ch2.data import *
from ch2.data.power import *
from ch2.jupyter.decorator import template
from ch2.lib import bookend
from ch2.names import N
from ch2.pipeline.owners import *


@template
def fit_power_parameters(bookmark, large):

    f'''
    # Fit Power Parameters to {bookmark}

    This notebook allows you to calculate power parameters (CdA - air resistance, Crr - rolling resistance)
    from bookmarked activities.

    Beforehand you should have generated the bookmark by running

        > python -m ch2.data.coasting

    or similar to identify sections of activities with little pedalling.
    See that module for more information.

    The `large` parameter means that each bookmark is taken in its entirety.
    The alternative is that they are divided into small sub-samples reflecting the data sample rate.
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''
    s = session('-v 5')
    large = strtobool(large)
    route = Statistics(s, bookmarks=bookmarks(s, bookmark)). \
        by_name(SegmentReader, N.LATITUDE, N.LONGITUDE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y,
                N.DISTANCE, N.ELEVATION, N.SPEED, N.CADENCE)
    route.sort_index(inplace=True)  # bookmarks are not sorted by time
    if large:
        route, max_gap = bookend(route), None
    else:
        max_gap = 10
    route = add_differentials(route, max_gap=max_gap)
    if large:
        route = route.iloc[1::2]
    route.describe()

    '''
    ## Add Energy Calculations
    '''
    weight = 64+12  # weight of rider + bike / kg  todo - extract weight from db
    route = add_energy_budget(route, weight)
    route = add_air_speed(route)
    route = add_cda_estimate(route)
    route = add_crr_estimate(route, weight)
    route.describe()

    '''
    ## Plot Constraints
    
    The calculations above added an energy budget for each "step" in the data.
    These included values for CdA and Crr that would "explain" the decrease in energy 
    (taking each alone - so the CdA is that required for all energy lost to air resistance, 
    the Crr is that required for all energy lost to rolling resistance).
    
    But we know that both CdA and Crr could be important.
    So what we want is a linear combination of the two.
    For example, maybe the energy loss is 90% due to CdA and 10% due to Crr.
    All these possible linear combinations lie on a line that joins 100% CdA and 0% Crr with 0% CdA and 100% Crr.
    
    So the plot below shows all possible combinations of CdA and Crr.
    And what we are looking for is the most common value.
    So we want to know where the plot is darkest / the lines are most dense. 
    '''
    output_notebook()
    f = figure(plot_width=500, plot_height=400)
    clean = route.loc[route[N.DELTA_ENERGY] < 0].dropna()
    cs = pd.DataFrame({N.CDA: [(0, cda) for cda in clean[N.CDA]],
                       N.CRR: [(crr, 0) for crr in clean[N.CRR]]})
    f.multi_line(xs=N.CDA, ys=N.CRR, source=cs, line_alpha=0.1, line_color='black')
    f.xaxis.axis_label = 'CdA'
    f.yaxis.axis_label = 'Crr'
    show(f)

    '''
    ## CdA Only
    
    If we ignore Crr then we can estimate CdA by looking at the relative number of constraints of CdA
    where Crr is zero.
    
    We do this by fitting to binned data.
    The peak in the fit(s) gives the value of CdA if Crr is unimportant.
    '''
    bins = np.linspace(0, 1.5, 30)
    width = bins[1] - bins[0]
    counts = clean[N.CDA].groupby(pd.cut(clean[N.CDA], bins)).size()
    print(counts.describe())

    cda = pd.DataFrame({N.CDA: 0.5 * (bins[:-1] + bins[1:]), 'n': counts.values})
    f = figure(plot_width=900, plot_height=300)
    f.quad(top=counts, left=bins[:-1]+0.1*width, right=bins[1:]-0.1*width, bottom=0)
    for order in range(2, 20, 2):
        coeff = sp.polyfit(cda[N.CDA], cda['n'], order)
        p = sp.poly1d(coeff)
        print(order, fmin(lambda x: -p(x), 0.6, disp=0)[0])
        f.line(x=cda[N.CDA], y=p(cda[N.CDA]), line_color='orange')
    show(f)

    '''
    ## Sample Constraints
    
    If we want to include Crr then we need to find a way to measure the "peak" in the messy line plot above.
    To do this we convert to a collection of points and then fit a 2D density function.
    
    Conversion to points is done by selecting points at random on each line.
    (You might think that shorter lines should generate less points.
    The way I see it, each line is an observation that constrains CdA and Crr.
    Each observation has equal weight, so each line generates a point.)
    
    Random points avoids any systematic patterns from uniform sampling 
    and allows re-runs to give some idea of noise. 
    '''

    def sample():
        clean.loc[:, 'random'] = np.random.random(size=len(clean))
        clean.loc[:, 'x'] = clean[N.CDA] * clean['random']
        clean.loc[:, 'y'] = clean[N.CRR] * (1 - clean['random'])
        return clean.loc[:, ['x', 'y']]

    s = pd.concat([sample() for _ in range(100 if large else 10)])
    print(s.describe())

    f = figure(plot_width=600, plot_height=600)
    f.scatter(x='x', y='y', source=s)
    show(f)

    '''
    ## Smooth, Find Maximum
    
    We generate and plot a Gaussian kernel density estimate.
    
    See https://towardsdatascience.com/simple-example-of-2d-density-plots-in-python-83b83b934f67
    
    You may want to play around with bandwidth by supplying a second argument to gaussian_kde. 
    See https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html
    '''

    kernel = sp.stats.gaussian_kde(s.transpose())

    xmin, xmax = 0, 1
    ymin, ymax = 0, 0.02
    xx, yy = np.mgrid[xmin:xmax:100j, ymin:ymax:100j]
    xy = np.vstack([xx.ravel(), yy.ravel()])
    smooth = np.reshape(kernel(xy), xx.shape)

    fig = plt.figure(figsize=(8,8))
    ax = fig.gca()
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.contourf(xx, yy, smooth, cmap='coolwarm')
    cset = ax.contour(xx, yy, smooth, colors='k')
    ax.clabel(cset, inline=1, fontsize=10)
    ax.set_xlabel('CdA')
    ax.set_ylabel('Crr')
    plt.title('2D Gaussian Kernel density estimation')

    '''
    For my data this shows (roughly):
    
    * large=True: Crr ~ 0.005-0.006 and CdA ~ 0.40-0.45
    
    * large=False: Crr ~ 0.01 and CdA ~ 0.35-0.40
    
    which supports the idea that Crr isn't well-constrained by the data.
    
    I chose large=True values since I suspect the larger intervals make the elevation values more accurate, 
    
    Since I am loading data with a command like
    
        > ch2 activities -D kit=cotic -- ~/archive/fit/**/*.fit
    
    I define this constant:
    
        > ch2 constants add --single Power.cotic \
            --description 'Bike namedtuple values to calculate power for this kit' \
            --validate ch2.stats.calculate.power.Bike
        > ch2 constants set Power.cotic '{"cda": 0.42, "crr": 0.0055, "weight": 12}'
        
    With that, the standard configuration should calculate power estimates.
    '''
