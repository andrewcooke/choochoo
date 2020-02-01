import React, {useEffect, useState} from 'react';
import Layout from "../../utils/Layout";
import makeStyles from "@material-ui/core/styles/makeStyles";
import {DatePicker} from "@material-ui/pickers";
import parse from 'date-fns/parse';
import format from 'date-fns/format';
import ListItem from '@material-ui/core/ListItem';
import List from "@material-ui/core/List";
import fmtDay from './fmtDay';
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
        case 0: return {ymd, dateFmt:'yyyy', fmt:fmtYear};
        case 1: return {ymd, dateFmt:'yyyy-MM', fmt:fmtMonth};
        case 2: return {ymd, dateFmt:'yyyy-MM-dd', fmt:fmtDay};
        default: throw('Bad date ' + date);
    }
}


export default function Diary(props) {

    const {match, history} = props;
    const {date} = match.params;
    const {ymd, dateFmt, fmt} = classifyDate(date);
    const datetime = parse(date, dateFmt, new Date());
    const [content, setContent] = useState(<p/>);

    useEffect(() => {
        fetch('api/diary/' + date)
            .then(res => res.json())
            .then(res => setContent(fmt(res)));
    }, [date]);

    const navigation = (
        <DiaryMenu ymd={ymd} datetime={datetime} dateFmt={dateFmt} history={history}/>
    );

    return (
        <Layout navigation={navigation} content={content} match={match} title={'Diary: ' + date}/>
    );
}
