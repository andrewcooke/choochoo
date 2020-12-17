import React, {useEffect, useState} from 'react';
import {FormatValueUnits, Layout, OSMap, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {last} from "../../../common/functions";
import {Grid, Link, Radio, Slider, Tooltip, useTheme} from "@material-ui/core";
import {handleJson} from "../../functions";
import {FMT_DAY_TIME} from "../../../constants";
import {format, parse} from 'date-fns';
import log from "loglevel";
import {Area, AxisBottom, AxisLeft, AxisRight, Brush, Circle, Group, Line, LinePath, ParentSize, PatternLines} from '@visx/visx';
import {scaleLinear, scaleTime} from "d3-scale";
import {sprintf} from "sprintf-js";
import {useLocation} from "react-router-dom";


function hms(seconds) {
    const s = seconds % 60;
    const m = Math.round(((seconds - s) / 60) % 60);
    const h = Math.round(((seconds - s) / 60 - m) / 60);
    if (h > 0) return sprintf('%0d:%02d:%02d', h, m, s);
    if (m > 0) return sprintf('%d:%02d', m, s);
    return sprintf('%d', s);
}


function between(start, date, finish) {
    return (start === null || start <= date) && (finish === null || date <= finish);
}


function Scatter(props) {

    const {width, height, sectors, sector1=null, sector2=null,
        start=null, finish=null, brush=false, setRange=null,
        margin={top: 10, bottom: 20, left: 40, right: 40}} = props;

    function speed(s) {return 1000 * s.distance / s.time;}
    const groups = [];
    if (sector1) groups.push(sector1.activity_group);
    if (sector2) groups.push(sector2.activity_group);

    const filtered = sectors.filter(s => between(start, s.date, finish));
    const min = {speed: Math.min(...filtered.map(s => speed(s))), date: Math.min(...filtered.map(s => s.date))};
    const max = {speed: Math.max(...filtered.map(s => speed(s))), date: Math.max(...filtered.map(s => s.date))};
    const speedScale = scaleLinear([min.speed, max.speed], [height-margin.bottom, margin.top]);
    const dateScale = scaleTime([start ? start : min.date, finish ? finish : max.date],
        [margin.left, width-margin.right]);

    // brush doesn't handle margins correctly, so we do it ourselves (see Group)
    const brushWidth = width - margin.left - margin.right;
    const brushScale = scaleTime([start ? start : min.date, finish ? finish : max.date], [0, brushWidth]);

    const theme = useTheme();
    const fg = theme.palette.text.secondary;
    const fs = 10;
    function tlp(anchor, dy=0) {
        return () => ({fill: fg, fontSize: fs, textAnchor: anchor, dy: dy});
    }
    function fill(s) {
        if (sector1 && sector1.db === s.db) return theme.palette.secondary.main;
        if (sector2 && sector2.db === s.db) return theme.palette.primary.main;
        if (!groups.length || groups.includes(s.activity_group)) return fg;
        return null;
    }

    return (<svg width='100%' height={height}>
        {filtered.map(s => <Circle fill={fill(s)} cx={dateScale(s.date)} cy={speedScale(speed(s))} r={3}/>)}
        {brush ? (<Group left={margin.left}>
                <PatternLines id='pattern' height={8} width={8} stroke={fg} strokeWidth={1}
                              orientation={['diagonal']}/>
                <Brush xScale={brushScale} yScale={speedScale} width={brushWidth} height={height}
                       margin={margin} handleSize={8} resizeTriggerAreas={['left', 'right']}
                       brushDirection="horizontal"
                       initialBrushPosition={{start: {x: brushScale(min.date)}, end: {x: brushScale(max.date)}}}
                       onChange={(domain) => {if (domain) setRange([domain.x0, domain.x1]);}}
                       onClick={() => setRange([min.date, max.date])}
                       selectedBoxStyle={{fill: 'url(#pattern)', stroke: fg}}/>
            </Group>) : (<>
                <AxisLeft scale={speedScale} left={margin.left} stroke={fg}
                          tickStroke={fg} tickLabelProps={tlp('end', '0.25em')}/>
                <text x={0} y={0} transform={`translate(${margin.left+15},${margin.top})\nrotate(-90)`} fontSize={fs}
                      textAnchor='end' fill={fg}>Speed / m/s</text>
                <AxisBottom scale={dateScale} top={height-margin.bottom} stroke={fg}
                            tickStroke={fg} tickLabelProps={tlp('middle')}
                            labelProps={{fill: fg, fontSize: fs, textAnchor: 'middle'}}/>
            </>)}
    </svg>);
}


function BrushScatter(props) {
    const {sectors, sector1, sector2} = props;
    const [range, setRange] = useState([null, null]);
    return (<ColumnCard><Grid item xs={12}>
        <Scatter height={300} width={500} sectors={sectors} sector1={sector1} sector2={sector2}
                 start={range[0]} finish={range[1]}/>
        <Scatter height={50} width={500} sectors={sectors} sector1={sector1} sector2={sector2}
                 setRange={setRange} brush={true} margin={{top: 10, bottom: 0, left: 40, right: 40}}/>
    </Grid></ColumnCard>);
}


function Comparison(props) {

    const {width, height, slider, fast, slow, min, max, fColour, sColour, n=100,
        margin={top: 10, bottom: 40, left: 40, right: 40}} = props;

    const sliderFast = interpolate(fast, slider * last(fast).distance, 'distance');
    const slowAtTime = interpolate(slow, sliderFast.time, 'time');
    const slowAtDistance = interpolate(slow, sliderFast.distance, 'distance');

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
        <Area data={fast} fill={fg} opacity={0.05}
              x={fast => distanceScale(fast.distance)}
              y1={fast => elevationScale(fast.elevation)} y0={fast => height-margin.bottom}/>
        <LinePath data={fast} stroke={fg} strokeWidth={1} opacity={0.2}
                  x={fast => distanceScale(fast.distance)} y={fast => elevationScale(fast.elevation)}/>
        <LinePath data={slow} stroke={sColour} strokeWidth={2}
                  x={slow => distanceScale(slow.distance)} y={slow => timeScale(slow.time)}/>
        <LinePath data={fast} stroke={fColour} strokeWidth={2}
                  x={fast => distanceScale(fast.distance)} y={fast => timeScale(fast.time)}/>
        <Line stroke={sColour} opacity={0.5}
              from={{x: distanceScale(slowAtTime.distance), y: margin.top}}
              to={{x: distanceScale(slowAtTime.distance), y: height-margin.bottom}}/>
        <Circle fill={sColour} cx={distanceScale(slowAtTime.distance)} cy={timeScale(slowAtTime.time)} r={3}/>
        <Line stroke={sColour} opacity={0.5}
              from={{x: margin.left, y: timeScale(slowAtDistance.time)}}
              to={{x: width-margin.right, y: timeScale(slowAtDistance.time)}}/>
        <Circle fill={sColour} cx={distanceScale(slowAtDistance.distance)} cy={timeScale(slowAtDistance.time)}
                r={3}/>
        <Line stroke={fColour} opacity={0.5}
              from={{x: distanceScale(sliderFast.distance), y: margin.top}}
              to={{x: distanceScale(sliderFast.distance), y: height-margin.bottom}}/>
        <Line stroke={fColour} opacity={0.5}
              from={{x: margin.left, y: timeScale(sliderFast.time)}}
              to={{x: width-margin.right, y: timeScale(sliderFast.time)}}/>
        <Circle fill={fColour} cx={distanceScale(sliderFast.distance)} cy={timeScale(sliderFast.time)} r={3}/>
        <text x={0.87 * width} y={0.8 * height} fontSize={fs+2} fill={fg} textAnchor='end'>
            {sprintf('%.1fs / %.1fm', slowAtDistance.time - sliderFast.time,
                1000 * (sliderFast.distance - slowAtTime.distance))}
        </text>
        <AxisLeft scale={timeScale} left={margin.left} stroke={fg}
                  tickStroke={fg} tickLabelProps={tlp('end', '0.25em')} tickFormat={hms}/>
        <text x={0} y={0} transform={`translate(${margin.left+15},${margin.top})\nrotate(-90)`} fontSize={fs}
              textAnchor='end' fill={fg}>Time / hms</text>
        <AxisRight scale={elevationScale} left={width-margin.right} stroke={fg}
                   tickStroke={fg} tickLabelProps={tlp('start', '0.25em')}/>
        <text x={0} y={0} transform={`translate(${width-margin.right-10},${margin.top})\nrotate(-90)`} fontSize={fs}
              textAnchor='end' fill={fg}>Elevation / m</text>
        <AxisBottom scale={distanceScale} top={height-margin.bottom} stroke={fg}
                    tickStroke={fg} tickLabelProps={tlp('middle')}
                    labelProps={{fill: fg, fontSize: fs, textAnchor: 'middle'}} label='Distance / km'/>
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


function zip(input) {
    const [first, ...rest] = Object.keys(input);
    const output = input[first].map(value => ({[first]: value}));
    rest.forEach(key => input[key].forEach((x, i) => output[i][key] = x));
    return output;
}


function SliderComparison(props) {

    const {sector1, sector2, n=100} = props;
    const [slider, setSlider] = useState(0);
    const theme = useTheme();
    const [fast, zfast, fColour, slow, zslow, sColour] = last(sector1.edt.time) > last(sector2.edt.time) ?
        [sector2.edt, sector2.zipped_edt, theme.palette.primary.main,
         sector1.edt, sector1.zipped_edt, theme.palette.secondary.main] :
        [sector1.edt, sector1.zipped_edt, theme.palette.secondary.main,
         sector2.edt, sector2.zipped_edt, theme.palette.primary.main];
    const elevation = fast.elevation.concat(slow.elevation);
    const min = {distance: 0, time: 0, elevation: Math.min(...elevation)};
    const max = {distance: Math.max(...fast.distance, ...slow.distance),
        time: Math.max(...fast.time, ...slow.time),
        elevation: Math.max(...elevation)};

    return (<ColumnCard>
        <Grid item xs={12}>
            <ParentSize>
                {({ width: visWidth, height: visHeight }) =>
                    <Comparison width={visWidth} height={300} slider={slider} fast={zfast} slow={zslow}
                                min={min} max={max} fColour={fColour} sColour={sColour}/>}
            </ParentSize>
        </Grid>
        <Grid item xs={12}>
            <Slider value={slider} onChange={(event, value) => setSlider(value)}
                    min={0} max={1} step={1 / n}
                    color={fColour === theme.palette.primary.main ? 'primary' : 'secondary'}/>
            <Text>
                <p>Moving the slider selects a point on the faster activity and displays the time and distance
                    difference to the slower activity at the same distance or time, respectively.</p>
            </Text>
        </Grid>
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
                <Link onClick={() => sort('date', true)}><Text>{format(json.date, FMT_DAY_TIME)}</Text></Link>
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
        </Text>
    </Grid></ColumnCard>);
}


function SectorContent(props) {

    // todo - what if 0 or 1 sectors matched?
    const {sector, data, history, from} = props;
    const [sectors, setSectors] = useState(data.sector_journals);
    const [showDistance, setShowDistance] = useState(true);
    const [i, setI] = useState(-1);
    const [j, setJ] = useState(-1);

    if (i === -1) {  // set to fastest
        let [fastest, fastest_time] = [0, last(sectors[0].edt.time)];
        sectors.forEach((sj, i) => {
            const time = last(sj.edt.time);
            if (time < fastest_time) {
                fastest = i;
                fastest_time = time;
            }});
        setI(fastest);
    }

    if (j === -1) {
        let found = false;
        if (from) {  // set to source
            sectors.forEach((sj, i) => {
                if (sj.db === parseInt(from)) {
                    setJ(i);
                    found = true;
                }
            });
        }
        if (! found) {
            log.warn(`Could not find from (${from})`)
            setJ(0);
        }
    }

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
        <BrushScatter sectors={data.sector_journals}
                      sector1={data.sector_journals[i]} sector2={data.sector_journals[j]}/>
        <SliderComparison sector1={data.sector_journals[i]} sector2={data.sector_journals[j]}/>
        {sectorJournals}
        <LoadMap sector={sector} history={history}/>
    </ColumnList>);
}


function useQuery() {
    return new URLSearchParams(useLocation().search);
}


export default function Sector(props) {

    const {match, history} = props;
    const {id} = match.params;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const query = useQuery();
    const from = query.get("from");

    function setJson(json) {
        setData(fixJournals(json));
    }

    function fixJournals(json) {
        if (json !== null && json.sector_journals !== undefined) {
            json.sector_journals = json.sector_journals.map(fixDatum);
        }
        return json;
    }

    function fixDatum(row, i) {
        log.debug(`fixing ${row.name} / ${row.db}`);
        row.date = parse(row.date, FMT_DAY_TIME, new Date());
        row.index = i;
        row.zipped_edt = zip(row.edt);
        return row;
    }

    useEffect(() => {
        fetch('/api/sector/' + id)
            .then(handleJson(history, setJson, setError));
    }, [id]);

    const content = data === null ? <Loading/> :
        <SectorContent sector={id} data={data} history={history} from={from}/>;

    return <Layout title='Sector Analysis' content={content} errorState={errorState}/>;
}
