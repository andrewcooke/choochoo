import React, {useEffect, useState} from 'react';
import {FormatValueUnits, Layout, OSMap, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {last} from "../../../common/functions";
import {Grid, Link, Radio, Slider, Tooltip, useTheme} from "@material-ui/core";
import {handleJson} from "../../functions";
import {FMT_DAY_TIME} from "../../../constants";
import {format, parse} from 'date-fns';
import log from "loglevel";
import {sprintf} from 'sprintf-js';
import {Group, LinePath, Area, AxisLeft, AxisRight, AxisBottom} from '@visx/visx';
import {scaleLinear} from "d3-scale";
import {useDimensions} from "react-recipes";


function Plot(props) {

    const {width, height, fast, slow, fColour, sColour, n=100,
        margin={top: 10, bottom: 40, left: 30, right: 30}} = props;
    log.debug(`height ${height}`)
    const zfast = zip(fast);
    const zslow = zip(slow);
    const max_distance = Math.max(...fast.distance, ...slow.distance);
    const max_time = Math.max(...fast.time, ...slow.time);
    const elevation = fast.elevation.concat(slow.elevation);
    const min_elevation = Math.min(...elevation);
    const max_elevation = Math.max(...elevation);

    const [slider, setSlider] = useState(0);
    const sfast = interpolate(zfast, slider * max_distance, 'distance');
    const sslow = interpolate(zslow, sfast.time, 'time');

    const distanceScale = scaleLinear([0, max_distance], [margin.left, width-margin.right]);
    // note inversion of y axis
    const timeScale = scaleLinear([0, max_time], [height-margin.bottom, margin.top]);
    const elevationScale = scaleLinear([min_elevation, max_elevation], [height-margin.bottom, margin.top]);

    const theme = useTheme();
    const fg = theme.palette.text.secondary;
    function tlp(anchor, dy=0) {
        return () => ({fill: fg, fontSize: 9, textAnchor: anchor, dy: dy});
    }

    return (<svg width='100%' height={height}>
        <Group>
            <Area data={zfast}
                  x={fast => distanceScale(fast.distance)}
                  y1={fast => elevationScale(fast.elevation)}
                  y0={fast => height-margin.bottom}
                  fill={fColour} opacity={0.2}
            />
            <Area data={sfast}
                  x={slow => distanceScale(slow.distance)}
                  y1={slow => elevationScale(slow.elevation)}
                  y0={slow => height-margin.bottom}
                  fill={sColour} opacity={0.2}
            />
            <LinePath data={zfast}
                      x={fast => distanceScale(fast.distance)}
                      y={fast => timeScale(fast.time)}
                      stroke={fColour}
            />
            <LinePath data={zslow}
                      x={slow => distanceScale(slow.distance)}
                      y={slow => timeScale(slow.time)}
                      stroke={sColour}
            />
            <AxisLeft scale={timeScale} left={margin.left} stroke={fg}
                      tickStroke={fg} tickLabelProps={tlp('end', '0.25em')}/>
            <text x={0} y={0} transform={`translate(${margin.left+15},${margin.top})\nrotate(-90)`} fontSize={9}
                  textAnchor='end' fill={fg}>Time / s</text>
            <AxisRight scale={elevationScale} left={width-margin.right} stroke={fg}
                       tickStroke={fg} tickLabelProps={tlp('start', '0.25em')}/>
            <text x={0} y={0} transform={`translate(${width-margin.right-10},${margin.top})\nrotate(-90)`} fontSize={9}
                  textAnchor='end' fill={fg}>Elevation / m</text>
            <AxisBottom scale={distanceScale} top={height-margin.bottom} stroke={fg}
                        tickStroke={fg} tickLabelProps={tlp('middle')}
                        labelProps={{fill: fg, fontSize: 9, textAnchor: 'middle'}} label='Distance / km'/>
        </Group>
    </svg>);
            {/*<ComposedChart width={500} height={300} margin={{top:10, bottom: 10, left:10, right: 10}}>*/}
            {/*    <XAxis xAxisId='distance' dataKey='distance' unit='km'*/}
            {/*           type='number' domain={[0, max_distance]} scale='linear'*/}
            {/*           tickFormatter={x => sprintf('%.2f', x)}*/}
            {/*           stroke={theme.palette.text.primary}*/}
            {/*           label={{value: 'Distance', position: 'insideBottom',*/}
            {/*                   fill: theme.palette.text.secondary, offset: -10}}/>*/}
            {/*    <YAxis yAxisId='elevation' unit='m' orientation='right'*/}
            {/*           type='number' domain={[min_elevation, max_elevation]} scale='linear'*/}
            {/*           stroke={theme.palette.text.primary}>*/}
            {/*        <Label angle={-90} position='insideRight' fill={theme.palette.text.secondary} offset={0}>*/}
            {/*            <XText value='Foo' textAnchor='middle'/>*/}
            {/*        </Label>*/}
            {/*    </YAxis>*/}
            {/*    <Area data={zslow} dataKey='elevation' dot={false} xAxisId='distance' yAxisId='elevation'*/}
            {/*          stroke={null} fill={sColour} fillOpacity={0.1} animationDuration={0}/>*/}
            {/*    <Area data={zfast} dataKey='elevation' dot={false} xAxisId='distance' yAxisId='elevation'*/}
            {/*          stroke={null} fill={fColour} fillOpacity={0.1} animationDuration={0}/>*/}
            {/*    <YAxis yAxisId='time' unit='s'*/}
            {/*           type='number' domain={[0, max_time]} scale='linear'*/}
            {/*           stroke={theme.palette.text.primary}*/}
            {/*           label={{value: 'Time', angle:-90, position: 'insideLeft',*/}
            {/*                   fill: theme.palette.text.secondary, offset: 0}}/>*/}
            {/*    <Scatter data={[sslow]} dataKey='time' xAxisId='distance' yAxisId='time'*/}
            {/*             stroke={sColour} strokeOpacity={1} strokeWidth={2}*/}
            {/*             fill={sColour} animationDuration={0}/>*/}
            {/*    <Line data={zslow} dataKey='time' dot={false} xAxisId='distance' yAxisId='time'*/}
            {/*          stroke={sColour} strokeOpacity={1} strokeWidth={2} animationDuration={0}/>*/}
            {/*    <Scatter data={[sfast]} dataKey='time' xAxisId='distance' yAxisId='time'*/}
            {/*             stroke={fColour} strokeOpacity={1} strokeWidth={2}*/}
            {/*             fill={fColour} animationDuration={0}/>*/}
            {/*    <Line data={zfast} dataKey='time' dot={false} xAxisId='distance' yAxisId='time'*/}
            {/*          stroke={fColour} strokeOpacity={1} strokeWidth={2} animationDuration={0}/>*/}
            {/*</ComposedChart>*/}
        {/*<Slider value={slider} onChange={(event, value) => setSlider(value)}*/}
        {/*        min={0} max={1} step={1/n}/>*/}
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


function WidthPlot(props) {
    const {fast, slow, fColour, sColour} = props;
    const [ref, dim] = useDimensions();
    // if we pass width/height directly we get a loop with progressive growth
    // if we pass height-5 alone we get progressive shrinkage
    // this hack appears to be stable
    return (<div ref={ref} style={{height: dim.height ? dim.height : 300}}>
        <Plot width={dim.width} height={dim.height-5} fast={fast} slow={slow} fColour={fColour} sColour={sColour}/>
    </div>);
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

    return  (<ColumnCard><Grid item xs={12}>
        <WidthPlot fast={fast} slow={slow} fColour={colours.get(fast)} sColour={colours.get(slow)}/>
    </Grid></ColumnCard>);
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
