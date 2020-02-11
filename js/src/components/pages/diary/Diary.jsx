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
import { add } from 'date-fns'


const useStyles = makeStyles(theme => ({
    root: {
        width: '100%',
        maxWidth: 360,
        backgroundColor: theme.palette.background.paper,
    },
    nested: {
        paddingLeft: theme.spacing(4),
    },
}));


function Picker(props) {
    const {ymdSelected, datetime, onChange} = props;
    switch (ymdSelected) {
        case 0: return <DatePicker value={datetime} views={["year"]} onChange={onChange}/>;
        case 1: return <DatePicker value={datetime} views={["year", "month"]} onChange={onChange}/>;
        case 2: return <DatePicker value={datetime} animateYearScrolling onChange={onChange}/>;
    }
}


const YMD = ['Year', 'Month', 'Day'];


function DateButtons(props) {

    const {ymd, ymdSelected, datetime, onChange} = props;

    function delta(n) {
        switch (ymd) {
            case 0: return {years: n};
            case 1: return {months: n};
            case 2: return {days: n};
        }
    }

    function before() {onChange(add(datetime, delta(-1)));}
    function next() {onChange(add(datetime, delta(1)));}
    function today() {onChange(new Date());}

    if (ymd > ymdSelected) {
        return <></>;
    } else {
        const centre = (ymd === ymdSelected ?
            <Grid item xs={3} justify='center'>
                <IconButton onClick={today}><CalendarTodayIcon/></IconButton>
            </Grid> :
            <Grid item xs={3} justify='center'/>);
        return (<ListItem>
                    <Grid container alignItems='center'>
                        <Grid item xs={5} justify='center'>
                            <Typography variant='body1' align='left'>{YMD[ymd]}</Typography>
                        </Grid>
                        <Grid item xs={2} justify='center'>
                            <IconButton edge='start' onClick={before}><NavigateBeforeIcon/></IconButton>
                        </Grid>
                        {centre}
                        <Grid item xs={2} justify='center'>
                            <IconButton onClick={next}><NavigateNextIcon/></IconButton>
                        </Grid>
                    </Grid>
                </ListItem>);
    }
}


function DiaryMenu(props) {

    const {ymdSelected, datetime, dateFmt, history} = props;
    const classes = useStyles();

    function onChange(datetime) {
        const date = format(datetime, dateFmt);
        history.push('/' + date);
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
                <ListItem>
                    <Grid container alignItems='center'>
                        <Grid item xs={5} justify='center'>
                            <Typography variant='body1' align='left'>Activity</Typography>
                        </Grid>
                        <Grid item xs={2} justify='center'>
                            <IconButton edge='start'><NavigateBeforeIcon/></IconButton>
                        </Grid>
                        <Grid item xs={3} justify='center'>
                        </Grid>
                        <Grid item xs={2} justify='center'>
                            <IconButton><NavigateNextIcon/></IconButton>
                        </Grid>
                    </Grid>
                </ListItem>
            </List>
        </>
    );
}


function classifyDate(date) {
    const ymdSelected = (date.match(/-/g) || []).length;
    switch (ymdSelected) {
        case 0: return {ymdSelected, dateFmt:'yyyy', component:fmtYear};
        case 1: return {ymdSelected, dateFmt:'yyyy-MM', component:fmtMonth};
        case 2: return {ymdSelected, dateFmt:'yyyy-MM-dd', component:Day};
        default: throw 'Bad date ' + date;
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
