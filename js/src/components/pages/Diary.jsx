import React, {useEffect} from 'react';
import Layout from "../utils/Layout";
import makeStyles from "@material-ui/core/styles/makeStyles";
import {DatePicker} from "@material-ui/pickers";
import parse from 'date-fns/parse';
import format from 'date-fns/format';
import ListItem from "@material-ui/core/ListItem";
import List from "@material-ui/core/List";


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

    const {ymd, datetime, fmt, history} = props;
    const classes = useStyles();

    function onChange(datetime) {
        const date = format(datetime, fmt);
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


function parseDate(date) {
    const ymd = (date.match(/-/g) || []).length;
    switch (ymd) {
        case 0: return {ymd, fmt:'yyyy', title:'Year'};
        case 1: return {ymd, fmt:'yyyy-MM', title:'Month'};
        case 2: return {ymd, fmt:'yyyy-MM-dd', title:'Day'};
        default: throw('Bad date ' + date);
    }
}


export default function Diary(props) {

    const {match, history} = props;
    const {date} = match.params;
    const {ymd, fmt, title} = parseDate(date);
    const datetime = parse(date, fmt, new Date());

    useEffect(() => {
        fetch('api/diary/' + date)
            .then(res => res.json())
            .then(res => console.log(res));
    });

    const content = (
        <p>
            Diary here.
        </p>);

    const navigation = (
        <DiaryMenu ymd={ymd} datetime={datetime} fmt={fmt} history={history}/>
    );

    return (
        <Layout navigation={navigation} content={content} match={match} title={'Diary: ' + date}/>
    );
}
