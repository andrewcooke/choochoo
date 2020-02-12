import React, {useEffect, useState} from 'react';
import Layout from "../../utils/Layout";
import makeStyles from "@material-ui/core/styles/makeStyles";
import {DatePicker} from "@material-ui/pickers";
import {parse, format} from 'date-fns';
import {ListItem, List, Grid, IconButton, Typography} from '@material-ui/core';
import Day from './Day';
import fmtMonth from "./fmtMonth";
import fmtYear from "./fmtYear";
import NavigateBeforeIcon from '@material-ui/icons/NavigateBefore';
import NavigateNextIcon from '@material-ui/icons/NavigateNext';
import CalendarTodayIcon from '@material-ui/icons/CalendarToday';
import {add} from 'date-fns';


const useStyles = makeStyles(theme => ({
    root: {
        width: '100%',
        maxWidth: 360,  // what is this for?  is it the same as constants.drawerWidth?
        backgroundColor: theme.palette.background.paper,
    },
}));


function Picker(props) {
    const {ymdSelected, datetime, onChange} = props;
    switch (ymdSelected) {
        case 0:
            return <DatePicker value={datetime} views={["year"]} onChange={onChange}/>;
        case 1:
            return <DatePicker value={datetime} views={["year", "month"]} onChange={onChange}/>;
        case 2:
            return <DatePicker value={datetime} animateYearScrolling onChange={onChange}/>;
    }
}


function BeforeNextButtonsBase(props) {

    const {label, before, centre, next} = props;

    return (<ListItem>
        <Grid container alignItems='center'>
            <Grid item xs={5} justify='center'>
                <Typography variant='body1' align='left'>{label}</Typography>
            </Grid>
            <Grid item xs={2} justify='center'>
                {before}
            </Grid>
            <Grid item xs={3} justify='center'>
                {centre}
            </Grid>
            <Grid item xs={2} justify='center'>
                {next}
            </Grid>
        </Grid>
    </ListItem>);
}


function ActivityButtons(props) {

    const {date, dateFmt, onChange} = props;
    const [before, setBefore] = useState(<IconButton edge='start' disabled><NavigateBeforeIcon/></IconButton>);
    const [next, setNext] = useState(<IconButton disabled><NavigateNextIcon/></IconButton>);

    function setContent(json) {

        const {before, after} = json;
        
        if (before !== undefined) {
            setBefore(<IconButton edge='start' onClick={() => onChange(parse(before, dateFmt, new Date()))}>
                <NavigateBeforeIcon/>
            </IconButton>);
        }
        if (after !== undefined) {
            setNext(<IconButton onClick={() => onChange(parse(after, dateFmt, new Date()))}>
                <NavigateNextIcon/>
            </IconButton>)
        }
    }

    useEffect(() => {
        fetch('/api/neighbour-activities/' + date)
            .then(response => response.json())
            .then(setContent);
    }, [date]);

    return (<BeforeNextButtonsBase
        label={<Typography variant='body1' align='left'>Activity</Typography>}
        before={before}
        next={next}
    />);
}


function ImmediateBeforeNextButtons(props) {

    const {centre, onBefore, onCentre, onNext, label} = props;

    return (<BeforeNextButtonsBase
        label={<Typography variant='body1' align='left'>{label}</Typography>}
        before={<IconButton edge='start' onClick={onBefore}><NavigateBeforeIcon/></IconButton>}
        centre={centre ? <IconButton onClick={onCentre}><CalendarTodayIcon/></IconButton> : null}
        next={<IconButton onClick={onNext}><NavigateNextIcon/></IconButton>}
    />);
}


const YMD = ['Year', 'Month', 'Day'];


function DateButtons(props) {

    const {ymd, ymdSelected, datetime, onChange} = props;

    function delta(n) {
        switch (ymd) {
            case 0:
                return {years: n};
            case 1:
                return {months: n};
            case 2:
                return {days: n};
        }
    }

    function onBefore() {
        onChange(add(datetime, delta(-1)));
    }

    function onNext() {
        onChange(add(datetime, delta(1)));
    }

    function onCentre() {
        onChange(new Date());
    }

    if (ymd > ymdSelected) {
        return <></>;
    } else {
        return (<ImmediateBeforeNextButtons centre={ymd === ymdSelected} onCentre={onCentre}
                                            onBefore={onBefore} onNext={onNext} label={YMD[ymd]}/>);
    }
}


function DiaryMenu(props) {

    const {ymdSelected, datetime, dateFmt, history} = props;
    const classes = useStyles();
    const date = format(datetime, dateFmt);

    function onChange(datetime) {
        const date = format(datetime, dateFmt);
        history.push('/' + date);
    }

    function activityBefore() {
        window.location = '/redirect/before/' + date;
    }

    function activityNext() {
        window.location = '/redirect/after/' + date;
    }

    return (
        <>
            <List component="nav" className={classes.root}>
                <ListItem>
                    <Picker ymdSelected={ymdSelected} datetime={datetime} onChange={onChange}/>
                </ListItem>
                <DateButtons ymd={2} ymdSelected={ymdSelected} datetime={datetime} onChange={onChange}/>
                <DateButtons ymd={1} ymdSelected={ymdSelected} datetime={datetime} onChange={onChange}/>
                <DateButtons ymd={0} ymdSelected={ymdSelected} datetime={datetime} onChange={onChange}/>
                <ActivityButtons date={date} dateFmt={dateFmt} onChange={onChange}/>
            </List>
        </>
    );
}


function classifyDate(date) {
    const ymdSelected = (date.match(/-/g) || []).length;
    switch (ymdSelected) {
        case 0:
            return {ymdSelected, dateFmt: 'yyyy', component: fmtYear};
        case 1:
            return {ymdSelected, dateFmt: 'yyyy-MM', component: fmtMonth};
        case 2:
            return {ymdSelected, dateFmt: 'yyyy-MM-dd', component: Day};
        default:
            throw 'Bad date ' + date;
    }
}


export default function Diary(props) {

    const {match, history} = props;
    const {date} = match.params;
    const {ymdSelected, dateFmt, component} = classifyDate(date);
    const datetime = parse(date, dateFmt, new Date());
    const [content, setContent] = useState(<p/>);
    const writer = new Worker('/static/writer.js');

    useEffect(() => {
        fetch('/api/diary/' + date)
            .then(response => response.json())
            .then(json => setContent(component({writer, json})));
    }, [date]);

    const navigation = (
        <DiaryMenu ymdSelected={ymdSelected} datetime={datetime} dateFmt={dateFmt} history={history}/>
    );

    return (
        <Layout navigation={navigation} content={content} match={match} title={date}/>
    );
}
