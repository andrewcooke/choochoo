import React, {useEffect, useState} from 'react';
import {ActivityButtons, DateButtons, Layout, Picker} from "../elements";
import {makeStyles} from "@material-ui/core/styles";
import {format, parse} from 'date-fns';
import {List, ListItem} from '@material-ui/core';
import {Day, Schedule} from './diary';
import {Calendar, Months} from './diary/elements'
import {FMT_DAY, FMT_MONTH, FMT_YEAR} from "../../constants";
import {handleGet} from "../functions";


const useStyles = makeStyles(theme => ({
    root: {
        width: '100%',
        backgroundColor: theme.palette.background.paper,
    },
}));


function ActiveDays(props) {
    const {date, onChange} = props;
    const [json, setJson] = useState(null);
    useEffect(() => {
        setJson(null);
        fetch('/api/diary/active-days/' + date)
            .then(response => response.json())
            .then(json => setJson(json));
    }, [date]);
    return (<Calendar month={date} active={json} onChange={onChange}/>);
}


function ActiveMonths(props) {
    const {date, onChange} = props;
    const [json, setJson] = useState(null);
    useEffect(() => {
        setJson(null);
        fetch('/api/diary/active-months/' + date)
            .then(response => response.json())
            .then(json => setJson(json));
    }, [date]);
    return (<Months year={date} active={json} onChange={onChange}/>);
}


function SubMenu(props) {

    const {ymd, date, dateFmt, onActivity, onDay, onMonth} = props;

    if (ymd === 0) {
        return <ListItem><ActiveMonths date={date} onChange={onMonth}/></ListItem>;
    } else if (ymd === 1) {
        return <ListItem><ActiveDays date={date} onChange={onDay}/></ListItem>;
    } else {
        return <ActivityButtons date={date} dateFmt={dateFmt} onChange={onActivity}/>;
    }
}


function DiaryMenu(props) {

    const {ymdSelected, datetime, dateFmt, history} = props;
    const classes = useStyles();
    const date = format(datetime, dateFmt);

    function setDate(date) {
        history.push('/' + date);
    }

    function setDatetime(datetime, fmt) {
        setDate(format(datetime, fmt));
    }

    return (<List component="nav" className={classes.root}>
        <ListItem>
            <Picker ymdSelected={ymdSelected} datetime={datetime}
                    onChange={datetime => setDatetime(datetime, dateFmt)}/>
        </ListItem>
        <DateButtons ymd={2} ymdSelected={ymdSelected} datetime={datetime}
                     onChange={datetime => setDatetime(datetime, dateFmt)}
                     onCentre={datetime => setDatetime(datetime, dateFmt)}/>
        <DateButtons ymd={1} ymdSelected={ymdSelected} datetime={datetime}
                     onChange={datetime => setDatetime(datetime, dateFmt)}
                     onCentre={datetime => setDatetime(datetime, FMT_MONTH)}/>
        <DateButtons ymd={0} ymdSelected={ymdSelected} datetime={datetime}
                     onChange={datetime => setDatetime(datetime, dateFmt)}
                     onCentre={datetime => setDatetime(datetime, FMT_YEAR)}/>
        <SubMenu ymd={ymdSelected} date={date} dateFmt={dateFmt}
                 onDay={setDate} onMonth={setDate}
                 onActivity={datetime => setDatetime(datetime, dateFmt)}/>
    </List>);
}


function classifyDate(date) {
    const ymdSelected = (date.match(/-/g) || []).length;
    switch (ymdSelected) {
        case 0:
            return {ymdSelected, dateFmt: FMT_YEAR, component: Schedule};
        case 1:
            return {ymdSelected, dateFmt: FMT_MONTH, component: Schedule};
        case 2:
            return {ymdSelected, dateFmt: FMT_DAY, component: Day};
        default:
            throw 'Bad date ' + date;
    }
}


export default function Diary(props) {

    const {match, history} = props;
    const {date} = match.params;
    const {ymdSelected, dateFmt, component} = classifyDate(date);
    const datetime = parse(date, dateFmt, new Date());
    const [json, setJson] = useState(null);
    const busyState = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const [reads, setReads] = useState(0);
    // this gets loaded multiple times which is less than ideal
    const writer = new Worker('/api/static/writer.js');

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        setJson(null);
        fetch('/api/diary/' + date)
            .then(handleGet(history, setJson, setError, busyState));
    }, [`${date} ${reads}`]);

    const navigation = (
        <DiaryMenu ymdSelected={ymdSelected} datetime={datetime} dateFmt={dateFmt} history={history}/>
    );

    return (
        <Layout navigation={navigation}
                content={component({json, writer, history})}
                match={match} title={`Diary: ${date}`} reload={reload}
                busyState={busyState} errorState={errorState}/>
    );
}
