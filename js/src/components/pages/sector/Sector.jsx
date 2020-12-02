import React, {useEffect, useState} from 'react';
import {FormatValueUnits, Layout, Map, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {Grid, Link, Radio, Tooltip} from "@material-ui/core";
import {handleJson} from "../../functions";
import {FMT_DAY_TIME} from "../../../constants";
import {format, parse} from 'date-fns';


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
            <Map latlon={data['latlon']} routes={<Route latlon={data['latlon']}/>}/>
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
