import React, {useEffect, useState} from 'react';
import {FormatValueUnits, Layout, OSMap, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {Grid, Link, Radio, Tooltip} from "@material-ui/core";
import {handleJson} from "../../functions";
import {FMT_DAY_TIME} from "../../../constants";
import {last} from "../../../common/functions";
import {format, parse} from 'date-fns';
import log from "loglevel";
import {Area, ComposedChart, Line, XAxis, YAxis} from "recharts";


function Plot(props) {

    const {fast, slow, fColour, sColour} = props;
    const data = resample(fast, slow, 1000, 'distance', ['elevation', 'time']);
    log.debug(JSON.stringify(data));
    log.debug(`fColour ${fColour} sColour ${sColour}`);

    return (<ComposedChart width={500} height={300} data={data}>
        <XAxis dataKey='distance'/>
        <YAxis yAxisId='left' units='s'/>
        <YAxis yAxisId='right' units='m' orientation='right' domain={['dataMin', 'dataMax']}/>
        <Area dataKey='fast_elevation' dot={false} fill={fColour} fillOpacity={0.1} yAxisId='right'/>
        <Area dataKey='slow_elevation' dot={false} fill={sColour} fillOpacity={0.1} yAxisId='right'/>
        <Line dataKey='fast_time' dot={false} stroke={fColour} strokeOpacity={1} strokeWidth={2} yAxisId='left'/>
        <Line dataKey='slow_time' dot={false} stroke={sColour} strokeOpacity={1} strokeWidth={2} yAxisId='left'/>
    </ComposedChart>);
}


function resample(fast, slow, n, ref, fields=[]) {
    const data = [];
    const [lo, hi] = [fast[ref][0], last(fast[ref])];
    let [i_fast, i_slow] = [0, 0];
    for (let i = 0; i < n; i++) {
        const datum = {}
        const x = lo + (hi - lo) * (i / (n - 1));
        datum[ref] = x;
        while (i_fast+1 < fast[ref].length && fast[ref][i_fast+1] <= x) i_fast++;
        const c = fast[ref][i_fast+1] - fast[ref][i_fast];
        const [a, b] = [(fast[ref][i_fast+1] - x) / c, (x - fast[ref][i_fast]) / c];
        for (let field of fields) {
            datum[`fast_${field}`] = fast[field][i_fast] * a + fast[field][i_fast+1] * b;
        }
        while (i_slow+1 < slow[ref].length && slow[ref][i_slow+1] <= x) i_slow++;
        if (slow[ref][i_slow] <= x && x <= slow[ref][i_slow+1]) {
            const c = slow[ref][i_slow+1] - slow[ref][i_slow];
            const [a, b] = [(slow[ref][i_slow+1] - x) / c, (x - slow[ref][i_slow]) / c];
            for (let field of fields) {
                datum[`slow_${field}`] = slow[field][i_slow] * a + slow[field][i_slow+1] * b;
            }
        }
        data.push(datum);
    }
    return data;
}


function LoadPlot(props) {

    const {sector1, sector2, history} = props;
    const [data1, setData1] = useState(null);
    const [data2, setData2] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

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
    colours.set(data1, 'orange');
    colours.set(data2, 'cyan');

    return  (<ColumnCard><Grid item xs={12}>
        <Plot fast={fast} slow={slow} fColour={colours.get(fast)} sColour={colours.get(slow)}/>
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
        <Grid item xs={1}><Radio checked={i == json.index} onChange={() => setI(json.index)}/></Grid>
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
        <Grid item xs={1}><Radio checked={j == json.index} onChange={() => setJ(json.index)}/></Grid>
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
