import React, {useEffect, useState} from 'react';
import {FormatValueUnits, Image, Layout, OSMap, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {last, useQuery} from "../../../common/functions";
import {FormControl, Grid, InputLabel, Link, MenuItem, Radio, Select, Tooltip} from "@material-ui/core";
import {handleJson} from "../../functions";
import {FMT_DAY, FMT_DAY_TIME} from "../../../constants";
import {format, parse} from 'date-fns';
import log from "loglevel";
import {useLocation, useHistory} from "react-router-dom";
import {Comparison, Scatter} from "./elements";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    thumbnail: {
        marginRight: '10px',
        padding: '1px',
        '&:hover': {
            border: '1px solid white',
            padding: '0px',
        },
    },
}));


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
    const classes = useStyles();
    const history = useHistory();

    function onClick(date) {
        history.push('/' + format(json.date, FMT_DAY));
    }

    function onAuxClick(date) {
        window.open('/' + format(json.date, FMT_DAY), '_blank');
    }

    return (<ColumnCard><Grid item container xs={10}>
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
    </Grid><Grid item xs={2}>
        <Tooltip title='Display diary for activity' placement='top'>
            <Link onClick={() => onClick(json.date)} onAuxClick={() => onAuxClick(json.date)}>
                <Image url={`/api/thumbnail/${json.activity_id}`} className={classes.thumbnail}/>
            </Link>
        </Tooltip>
    </Grid>
    </ColumnCard>);
}


function Introduction(props) {

    const {display, setDisplay} = props;

    return (<ColumnCard header='Introduction'><Grid item xs={12}>
        <Text>
            <p>A sector is defined from an activity.
                Other activities match if they enter / leave the same area and spend a large portion of time
                close to the original activity's route.</p>
            <p>The plots here show the observed data for each activity.
                GPS errors and small variations in routes mean that matching activities have different total
                distances (as well as different times because of different speeds).</p>
        </Text>
        <FormControl variant="outlined">
            <InputLabel id="display">Display</InputLabel>
            <Select
                labelId="display"
                value={display}
                onChange={(event) => setDisplay(event.target.value)}
                label="Display">
                <MenuItem value='Map'>Map</MenuItem>
                <MenuItem value='Scatter'>Scatter</MenuItem>
                <MenuItem value='Comparison'>Comparison</MenuItem>
            </Select>
        </FormControl>
    </Grid></ColumnCard>);
}


function SectorContent(props) {

    // todo - what if 0 or 1 sectors matched?
    const {sector, data, history, from} = props;
    const [sectors, setSectors] = useState(data.sector_journals);
    const [i, setI] = useState(-1);
    const [j, setJ] = useState(-1);
    const [display, setDisplay] = useState('Map');

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
        <Introduction display={display} setDisplay={setDisplay}/>
        {display === 'Scatter' ?
            <Scatter sectors={data.sector_journals}
                     sector1={data.sector_journals[i]} sector2={data.sector_journals[j]}/> : null}
        {display === 'Comparison' ?
            <Comparison sector1={data.sector_journals[i]} sector2={data.sector_journals[j]}/> : null}
        {display === 'Map' ? <LoadMap sector={sector} history={history}/> : null}
        {sectorJournals}
    </ColumnList>);
}


function zip(input) {
    const [first, ...rest] = Object.keys(input);
    const output = input[first].map(value => ({[first]: value}));
    rest.forEach(key => input[key].forEach((x, i) => output[i][key] = x));
    return output;
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

    const content = data ? <SectorContent sector={id} data={data} history={history} from={from}/> : <Loading/>;

    return <Layout title='Sector Jupyter' content={content} errorState={errorState}/>;
}
