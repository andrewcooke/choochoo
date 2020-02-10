import React, {useEffect, useState} from 'react';
import Layout from "../../utils/Layout";
import makeStyles from "@material-ui/core/styles/makeStyles";
import {DatePicker} from "@material-ui/pickers";
import {parse, format} from 'date-fns';
import {ListItem, List} from '@material-ui/core';
import Day from './Day';
import fmtMonth from "./fmtMonth";
import fmtYear from "./fmtYear";


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
    const {ymd, datetime, onChange} = props;
    switch (ymd) {
        case 0: return <DatePicker value={datetime} views={["year"]} onChange={onChange}/>;
        case 1: return <DatePicker value={datetime} views={["year", "month"]} onChange={onChange}/>;
        case 2: return <DatePicker value={datetime} animateYearScrolling onChange={onChange}/>;
    }
}


function DiaryMenu(props) {

    const {ymd, datetime, dateFmt, history} = props;
    const classes = useStyles();

    function onChange(datetime) {
        const date = format(datetime, dateFmt);
        history.push('/' + date);
    }

    return (
        <>
            <List component="nav" className={classes.root}>
                <ListItem>
                    <Picker ymd={ymd} datetime={datetime} onChange={onChange}/>
                </ListItem>
            </List>
        </>
    );
}


function classifyDate(date) {
    const ymd = (date.match(/-/g) || []).length;
    switch (ymd) {
        case 0: return {ymd, dateFmt:'yyyy', component:fmtYear};
        case 1: return {ymd, dateFmt:'yyyy-MM', component:fmtMonth};
        case 2: return {ymd, dateFmt:'yyyy-MM-dd', component:Day};
        default: throw 'Bad date ' + date;
    }
}


export default function Diary(props) {

    const {match, history} = props;
    const {date} = match.params;
    const {ymd, dateFmt, component} = classifyDate(date);
    const datetime = parse(date, dateFmt, new Date());
    const [content, setContent] = useState(<p/>);
    const writer = new Worker('/static/writer.js');

    useEffect(() => {
        fetch('/api/diary/' + date)
            .then(response => response.json())
            .then(json => setContent(component({writer, json})));
    }, [date]);

    const navigation = (
        <DiaryMenu ymd={ymd} datetime={datetime} dateFmt={dateFmt} history={history}/>
    );

    return (
        <Layout navigation={navigation} content={content} match={match} title={date}/>
    );
}
