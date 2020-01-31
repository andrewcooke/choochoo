import React from 'react';
import Layout from "./Layout";
import makeStyles from "@material-ui/core/styles/makeStyles";
import {DatePicker} from "@material-ui/pickers";
import {useParams} from 'react-router-dom';
import parse from 'date-fns/parse';


const useStyles = makeStyles(theme => ({
    root: {
        display: 'flex',
    },
    toolbar: theme.mixins.toolbar,
    content: {
        flexGrow: 1,
        padding: theme.spacing(3),
    },
}));


function Picker(props) {
    const {ymd, datetime} = props;
    switch (ymd) {
        case 0: return <DatePicker value={datetime} views={["year"]}/>;
        case 1: return <DatePicker value={datetime} views={["year", "month"]}/>;
        case 2: return <DatePicker value={datetime} animateYearScrolling/>;
    }
}


function DiaryMenu(props) {

    const {ymd, datetime} = props;
    const classes = useStyles();

    return (
        <>
           <Picker ymd={ymd} datetime={datetime}/>
        </>
    );
}


function parseDate(date) {
    const ymd = (date.match(/-/g) || []).length;
    switch (ymd) {
        case 0:
            return {ymd, datetime:parse(date, 'yyyy', new Date()), title:'Year'};
        case 1:
            return {ymd, datetime:parse(date, 'yyyy-MM', new Date()), title:'Month'};
        case 2:
            return {ymd, datetime:parse(date, 'yyyy-MM-dd', new Date()), title:'Day'};
        default:
            throw('Bad date ' + date);
    }
}


export default function Diary(props) {

    const {match} = props;
    const {date} = useParams();
    const classes = useStyles();

    const {ymd, datetime, title} = parseDate(date);

    console.log(ymd);
    console.log(date);
    console.log(datetime);

    const content = (
        <p>
            Diary here.
        </p>);

    const navigation = (
        <DiaryMenu ymd={ymd} datetime={datetime}/>
    );

    return (
        <Layout navigation={navigation} content={content} match={match} title={title}/>
    );
}
