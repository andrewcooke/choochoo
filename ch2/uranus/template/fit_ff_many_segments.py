
from math import log10

from bokeh.io import output_file, show
from bokeh.palettes import Dark2
from bokeh.plotting import figure

from ch2.data import *
from ch2.data.impulse import impulse_10
from ch2.data.response import *
from ch2.squeal import *
from ch2.squeal.database import connect
from ch2.stoats.calculate.impulse import HRImpulse
from ch2.uranus.decorator import template


@template
def fit_ff_many_segments(*segment_names):

    f'''
    # Fit FF Parameters to {', '.join(segment_names)}

    This notebook allows you to estimate a personal time scale (decay period) for the
    [FF model](https://andrewcooke.github.io/choochoo/impulse) using your times (more exactly, the speed)
    on the named segments.

    The resulting value can be used in the configuration so that the Fitness parameter more accurately
    reflects your personal rate of adaption.
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''

    s = session('-v2')
    hr10_data = statistics(s, HR_IMPULSE_10, with_sources=True)
    print(hr10_data.describe())
    segment_journals = s.query(SegmentJournal).join(Segment).filter(Segment.name == segment_name).all()
    st_data = statistics(s, SEGMENT_TIME, sources=segment_journals)
    print(st_data.describe())


    '''
    ## Define Initial Model
    
    Define an initial model and resample the data to hours (for faster fitting).
    
    Note that model scale and period are in log units so that the fitter cannot explore negative values.
    
    The default scale is 10 because there are 10 seconds between impulses (I wrote this a long time ago
    and honestly am no longer sure of the logic there).
    
    The default period is 42 days, as used by Training Peaks (note that units are hours because that is
    what we resample the data to).
    '''

    model = DecayModel(1e-10, 0, log10(10), log10(42 * 24), HR_IMPULSE_10, FITNESS)

    '''
    ## Plot Initial Model
    
    Trim and resample data; evaluate and plot our initial model.
    '''

    hr3600_data = pre_calc(hr10_data, model)
    hr3600_data = calc(hr3600_data, model)

    output_file(filename='/dev/null')
    palette = Dark2[3]

    f = figure(plot_width=500, plot_height=450, x_axis_type='datetime')
    f.line(x=hr3600_data.index, y=hr3600_data[FITNESS], color=palette[1], legend=f'new {FITNESS}')
    f.legend.location = 'top_left'
    show(f)

    '''
    ## Fit Model
    
    Trim data and resample data; calculate the target values (speed);
    do an initial evaluation to set the scaling; and then fit.
    '''

    st3600_data = st_data.set_index(st_data.index.round('1H'))
    print(st3600_data.describe())
    hr3600_data = pre_calc(hr10_data, model, target=st3600_data)
    print(hr3600_data.describe())
    data = hr3600_data.join(st3600_data, how='outer')
    data[SPEED] = 1/data[SEGMENT_TIME]

    # for stability we do a progressive adjustment
    model = fit(SPEED, FITNESS, data, model, calc, 'log10_scale', tol=1e-10)
    print(model)
    model = fit(SPEED, FITNESS, data, model, calc, 'log10_scale', 'log10_period', tol=1e-10)
    print(model)
    model = fit(SPEED, FITNESS, data, model, calc, 'log10_scale', 'log10_period', 'zero', tol=1e-10)
    print(model)
    print(f'\nFitted time scale {10**model.log10_period} hr')
    print(f'                  {10**model.log10_period / 24} days')

    '''
    ## Plot Fit
    '''

    results = calc(data, model)

    f = figure(plot_width=500, plot_height=450, x_axis_type='datetime')
    f.line(x=results.index, y=results[FITNESS], color=palette[1], legend=f'new {FITNESS}')
    f.circle(x=st_data.index, y=1.0/st_data[SEGMENT_TIME], fill_color=palette[2], size=10, legend='Speed')
    f.legend.location = 'top_left'
    show(f)

    '''
    ## Stop Here
    
    If running all cells, what follows is not what we want...
    '''

    raise Exception()

    '''
    ## Alternative Impulse Parameters
    
    So, for example, below has gamma=1 instead of the default 2.
    '''

    _, db = connect(['-v5'])
    impulse = HRImpulse(dest_name='Test Impulse', gamma=1.0, zero=2, one=6, max_secs=60)
    hr_data = statistics(s, HR_ZONE)
    print(hr_data.describe())
    #print(hr_data)
    impulse_data = impulse_10(hr_data, impulse)
    print(impulse_data.describe())
    #print(impulse_data)

    '''
    Fit to that data.
    '''

    model = DecayModel(1e-10, 0, log10(10), log10(42 * 24), 'Test Impulse', FITNESS)

    tmp_data = pre_calc(impulse_data, model, target=st3600_data)
    print(tmp_data.describe())
    data = tmp_data.join(st3600_data, how='outer')
    data[SPEED] = 1/data[SEGMENT_TIME]

    model = fit(SPEED, FITNESS, data, model, calc, 'log10_scale', tol=1e-10)
    print(model)
    model = fit(SPEED, FITNESS, data, model, calc, 'log10_scale', 'log10_period', tol=1e-10)
    print(model)
    model = fit(SPEED, FITNESS, data, model, calc, 'log10_scale', 'log10_period', 'zero', tol=1e-10)
    print(model)
    print(f'\nFitted time scale {10**model.log10_period} hr')
    print(f'                  {10**model.log10_period / 24} days')

    '''
    And plot the fit.
    '''

    results = calc(data, model)

    f = figure(plot_width=500, plot_height=450, x_axis_type='datetime')
    f.line(x=results.index, y=results[FITNESS], color=palette[1], legend=f'new {FITNESS}')
    f.circle(x=st_data.index, y=1.0/st_data[SEGMENT_TIME], fill_color=palette[2], size=10, legend='Speed')
    f.legend.location = 'top_left'
    show(f)
