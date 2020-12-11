import React, {useEffect, useState} from 'react';
import {FormatValueUnits, Layout, OSMap, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {last} from "../../../common/functions";
import {Grid, Link, Radio, Slider, Tooltip, useTheme} from "@material-ui/core";
import {handleJson} from "../../functions";
import {FMT_DAY_TIME} from "../../../constants";
import {format, parse} from 'date-fns';
import log from "loglevel";
import {Area, AxisBottom, AxisLeft, AxisRight, Group, LinePath, Line, Circle} from '@visx/visx';
import {scaleLinear} from "d3-scale";
import {useDimensions} from "react-recipes";
import {sprintf} from "sprintf-js";


function Plot(props) {

    const {width, height, slider, fast, slow, min, max, fColour, sColour, n=100,
        margin={top: 10, bottom: 40, left: 30, right: 30}} = props;

    const slider_fast = interpolate(fast, slider * last(fast).distance, 'distance');
    const slow_at_time = interpolate(slow, slider_fast.time, 'time');
    const slow_at_distance = interpolate(slow, slider_fast.distance, 'distance');

    const distanceScale = scaleLinear([0, max.distance], [margin.left, width-margin.right]);
    // note inversion of y axis
    const timeScale = scaleLinear([0, max.time], [height-margin.bottom, margin.top]);
    const elevationScale = scaleLinear([min.elevation, max.elevation], [height-margin.bottom, margin.top]);

    const theme = useTheme();
    const fg = theme.palette.text.secondary;
    const fs = 10;
    function tlp(anchor, dy=0) {
        return () => ({fill: fg, fontSize: fs, textAnchor: anchor, dy: dy});
    }

    log.debug(`rendering at height ${height}`)

    return (<svg width='100%' height={height}>
        <Group>
            <Area data={slow} fill={sColour} opacity={0.05}
                  x={slow => distanceScale(slow.distance)}
                  y1={slow => elevationScale(slow.elevation)} y0={slow => height-margin.bottom}/>
            <Area data={fast} fill={fColour} opacity={0.05}
                  x={fast => distanceScale(fast.distance)}
                  y1={fast => elevationScale(fast.elevation)} y0={fast => height-margin.bottom}/>
            <LinePath data={slow} stroke={sColour} strokeWidth={2}
                      x={slow => distanceScale(slow.distance)} y={slow => timeScale(slow.time)}/>
            <LinePath data={fast} stroke={fColour} strokeWidth={2}
                      x={fast => distanceScale(fast.distance)} y={fast => timeScale(fast.time)}/>
            <Line stroke={sColour} opacity={0.5}
                  from={{x: distanceScale(slow_at_time.distance), y: margin.top}}
                  to={{x: distanceScale(slow_at_time.distance), y: height-margin.bottom}}/>
            <Circle fill={sColour} cx={distanceScale(slow_at_time.distance)} cy={timeScale(slow_at_time.time)} r={3}/>
            <Line stroke={sColour} opacity={0.5}
                  from={{x: margin.left, y: timeScale(slow_at_distance.time)}}
                  to={{x: width-margin.right, y: timeScale(slow_at_distance.time)}}/>
            <Circle fill={sColour} cx={distanceScale(slow_at_distance.distance)} cy={timeScale(slow_at_distance.time)} r={3}/>
            <Line stroke={fColour} opacity={0.5}
                  from={{x: distanceScale(slider_fast.distance), y: margin.top}}
                  to={{x: distanceScale(slider_fast.distance), y: height-margin.bottom}}/>
            <Line stroke={fColour} opacity={0.5}
                  from={{x: margin.left, y: timeScale(slider_fast.time)}}
                  to={{x: width-margin.right, y: timeScale(slider_fast.time)}}/>
            <Circle fill={fColour} cx={distanceScale(slider_fast.distance)} cy={timeScale(slider_fast.time)} r={3}/>
            <text x={0.9 * width} y={0.8 * height} fontSize={fs} fill={fg} textAnchor='end'>
                {sprintf('%.1fs / %.1fm', slow_at_distance.time - slider_fast.time,
                    1000 * (slider_fast.distance - slow_at_time.distance))}
            </text>
            <AxisLeft scale={timeScale} left={margin.left} stroke={fg}
                      tickStroke={fg} tickLabelProps={tlp('end', '0.25em')}/>
            <text x={0} y={0} transform={`translate(${margin.left+15},${margin.top})\nrotate(-90)`} fontSize={fs}
                  textAnchor='end' fill={fg}>Time / s</text>
            <AxisRight scale={elevationScale} left={width-margin.right} stroke={fg}
                       tickStroke={fg} tickLabelProps={tlp('start', '0.25em')}/>
            <text x={0} y={0} transform={`translate(${width-margin.right-10},${margin.top})\nrotate(-90)`} fontSize={fs}
                  textAnchor='end' fill={fg}>Elevation / m</text>
            <AxisBottom scale={distanceScale} top={height-margin.bottom} stroke={fg}
                        tickStroke={fg} tickLabelProps={tlp('middle')}
                        labelProps={{fill: fg, fontSize: fs, textAnchor: 'middle'}} label='Distance / km'/>
        </Group>
    </svg>);
}


function interpolate(data, value, key) {
    const [i, j, norm, iweight, jweight] = bracket(data, value, key);
    log.debug(i, j, norm, iweight, jweight);
    const result = {};
    Object.keys(data[0]).forEach(key => {
        result[key] = (data[i][key] * iweight + data[j][key] * jweight) / norm;
    })
    return result;
}


function bracket(data, value, key) {
    log.debug(value, key);
    let a = 0;
    let c = data.length-1;
    while (c - a > 1) {
        const b = Math.floor(0.5 + 0.5 * (a + c));
        if (data[b][key] > value) {
            c = b;
        } else {
            a = b;
        }
    }
    return [a, c, data[c][key] - data[a][key], data[c][key] - value, value - data[a][key]];
}


function WidthPlot(props) {

    const {slider, fast, slow, min, max, fColour, sColour} = props;
    const [ref, dim] = useDimensions();

    // if we pass width/height directly we get a loop with progressive growth
    // if we pass height-5 alone we get progressive shrinkage
    // this hack appears to be stable
    return (<div ref={ref} style={{height: dim.height ? dim.height : 300}}>
        <Plot width={dim.width ? dim.width : 500} height={dim.height-5}
              slider={slider} fast={fast} slow={slow} min={min} max={max} fColour={fColour} sColour={sColour}/>
    </div>);
}


function SliderPlot(props) {

    const {fast, slow, min, max, fColour, sColour, n=100} = props;
    const [slider, setSlider] = useState(0);
    const theme = useTheme();

    return (<>
        <Grid item xs={12}>
            <WidthPlot slider={slider} fast={fast} slow={slow} min={min} max={max} fColour={fColour} sColour={sColour}/>
        </Grid>
        <Grid item xs={12}>
            <Slider value={slider} onChange={(event, value) => setSlider(value)}
                    min={0} max={1} step={1 / n}
                    color={fColour === theme.palette.primary.main ? 'primary' : 'secondary'}/>
        </Grid>
    </>);
}


function zip(input) {
    const output = [];
    Object.keys(input).forEach(key => {
        if (output.length === 0) {
            input[key].forEach(x => {
                const obj = {};
                obj[key] = x;
                output.push(obj)
            });
        } else {
            input[key].forEach((x, i) => output[i][key] = x);
        }
    });
    return output;
}


function LoadPlot(props) {

    const {sector1, sector2, history} = props;
    const [data1, setData1] = useState(null);
    const [data2, setData2] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const theme = useTheme();

    useEffect(() => {
        fetch('/api/route/edt/sector/' + sector1)
            .then(handleJson(history, setData1, setError));
    }, [sector1]);

    useEffect(() => {
        fetch('/api/route/edt/sector/' + sector2)
            .then(handleJson(history, setData2, setError));
    }, [sector2]);

    if (data1 === null || data2 === null) return <Loading/>;

    const fast = last(data1.time) > last(data2.time) ? data2 : data1;
    const slow = last(data1.time) > last(data2.time) ? data1 : data2;
    const colours = new Map();
    colours.set(data1, theme.palette.secondary.main);
    colours.set(data2, theme.palette.primary.main);

    log.debug(`fast ends at ${last(fast.time)}; slow ends at ${last(slow.time)}`);

    const zfast = zip(fast);
    const zslow = zip(slow);
    const elevation = fast.elevation.concat(slow.elevation);
    const min = {distance: 0, time: 0, elevation:  Math.min(...elevation)};
    const max = {distance: Math.max(...fast.distance, ...slow.distance),
        time: Math.max(...fast.time, ...slow.time),
        elevation: Math.max(...elevation)};

    log.debug(`fast ends at ${last(zfast).time}; slow ends at ${last(zslow).time}`);

    return  (<ColumnCard>
        <SliderPlot fast={zfast} slow={zslow} min={min} max={max}
                    fColour={colours.get(fast)} sColour={colours.get(slow)}/>
    </ColumnCard>);
}


function LoadMap(props) {

    const {sector, history} = props;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/route/latlon/sector/' + sector)
            .then(handleJson(history, setData, setError));
    }, [sector]);

    return  (data === null ? <Loading/> :
        <ColumnCard><Grid item xs={12}>
            <OSMap latlon={data['latlon']} routes={<Route latlon={data['latlon']}/>}/>
        </Grid></ColumnCard>);
}


function SectorJournal(props) {

    const {json, sort, i, setI, j, setJ} = props;

    return (<ColumnCard>
        <Grid item xs={9}>
            <Tooltip title='Sort by name' placement='top'>
                <Link onClick={() => sort('name')}><Text variant='h3'>{json.name}</Text></Link>
            </Tooltip>
        </Grid>
        <Grid item xs={2}>
            <Tooltip title='Sort by activity group' placement='top'>
                <Link onClick={() => sort('activity_group')}><Text>{json.activity_group}</Text></Link>
            </Tooltip>
        </Grid>
        <Grid item xs={1}><Radio checked={i == json.index} onChange={() => setI(json.index)} color='secondary'/></Grid>
        <Grid item xs={5}>
            <Tooltip title='Sort by date' placement='top'>
                <Link onClick={() => sort('date')}><Text>{format(json.date, FMT_DAY_TIME)}</Text></Link>
            </Tooltip>
        </Grid>
        <Grid item xs={2}>
            <Tooltip title='Sort by distance' placement='top'>
                <Link onClick={() => sort('distance')}><FormatValueUnits value={json.distance} units='km'/></Link>
            </Tooltip>
        </Grid>
        <Grid item xs={2}>
            <Tooltip title='Sort by time' placement='top'>
                <Link onClick={() => sort('time')}><FormatValueUnits value={json.time} units='s'/></Link>
            </Tooltip>
        </Grid>
        <Grid item xs={2}>
            <Tooltip title='Sort by elevation' placement='top'>
                <Link onClick={() => sort('elevation')}><FormatValueUnits value={json.elevation} units='m'/></Link>
            </Tooltip>
        </Grid>
        <Grid item xs={1}><Radio checked={j == json.index} onChange={() => setJ(json.index)} color='primary'/></Grid>
    </ColumnCard>);
}


function Introduction(props) {
    return (<ColumnCard header='Introduction'><Grid item xs={12}>
        <Text>
            <p>A sector is defined from an activity.
                Other activities match if they enter / leave the same area and spend a large portion of time
                close to the original activity's route.</p>
            <p>The plots here show the observed data for each activity.
                GPS errors and small variations in routes mean that matching activities have different total
                distances (as well as different times because of different speeds).</p>
            <p>Moving the slider selects a point on the faster activity and displays the time and distance
                difference to the slower activity at the same distance or time, respectively.</p>
        </Text>
    </Grid></ColumnCard>);
}


function SectorContent(props) {

    // todo - what if 0 or 1 sectors matched?
    const {sector, data, history} = props;
    const [sectors, setSectors] = useState(data['sector_journals']);
    const [showDistance, setShowDistance] = useState(true);
    const [i, setI] = useState(0);
    const [j, setJ] = useState(1);

    function sort(key, reverse = false) {
        let copy = sectors.slice();
        copy.sort((a, b) => a[key] instanceof String ?
            a[key].localeCompare(b[key]) :
            (a[key] - b[key]) * (reverse ? -1 : 1));
        setSectors(copy);
    }

    const sectorJournals = sectors.map((sector, k) =>
        <SectorJournal json={sector} sort={sort} key={k} i={i} setI={setI} j={j} setJ={setJ}/>);

    return (<ColumnList>
        <Introduction/>
        <LoadPlot sector1={data.sector_journals[i].db} sector2={data.sector_journals[j].db}
                  history={history}/>
        {sectorJournals}
        <LoadMap sector={sector} history={history}/>
    </ColumnList>);
}


export default function Sector(props) {

    const {match, history} = props;
    const {id} = match.params;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    function setJson(json) {
        setData(fixData(json));
    }

    function fixData(json) {
        if (json !== null && json.sector_journals !== undefined) {
            json.sector_journals = json.sector_journals.map(fixDatum)
        }
        return json;
    }

    function fixDatum(row, i) {
        row.date = parse(row.date, FMT_DAY_TIME, new Date());
        row.index = i;
        return row;
    }

    useEffect(() => {
        fetch('/api/sector/' + id)
            .then(handleJson(history, setJson, setError));
    }, [id]);

    const content = data === null ? <Loading/> :
        <SectorContent sector={id} data={data} history={history}/>;

    return <Layout title='Sector Analysis' content={content} errorState={errorState}/>;
}
