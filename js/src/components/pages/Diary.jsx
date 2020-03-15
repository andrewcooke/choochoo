import React, {useEffect, useState} from 'react';
import {Layout} from "../elements";
import {makeStyles} from "@material-ui/core/styles";
import {DatePicker} from "@material-ui/pickers";
import {add, format, parse} from 'date-fns';
import {Grid, IconButton, List, ListItem, Typography} from '@material-ui/core';
import {Day, Schedule} from './diary';
import NavigateBeforeIcon from '@material-ui/icons/NavigateBefore';
import NavigateNextIcon from '@material-ui/icons/NavigateNext';
import TodayIcon from '@material-ui/icons/Today';
import DateRangeIcon from '@material-ui/icons/DateRange';
import {Calendar, Months} from './diary/elements'
import {FMT_DAY, FMT_MONTH, FMT_YEAR} from "../../constants";


const useStyles = makeStyles(theme => ({
    root: {
        width: '100%',
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
            <Grid item xs={5}>
                <Typography variant='body1' component='span' align='left'>{label}</Typography>
            </Grid>
            <Grid item xs={2}>
                {before}
            </Grid>
            <Grid item xs={3}>
                {centre}
            </Grid>
            <Grid item xs={2}>
                {next}
            </Grid>
        </Grid>
    </ListItem>);
}


function ActivityButtons(props) {

    const noBefore = <IconButton edge='start' disabled><NavigateBeforeIcon/></IconButton>;
    const noNext = <IconButton disabled><NavigateNextIcon/></IconButton>;
    const {date, dateFmt, onChange} = props;
    const [before, setBefore] = useState(noBefore);
    const [next, setNext] = useState(noNext);

    function setContent(json) {

        const {before, after} = json;

        setBefore(before !== undefined ?
            <IconButton edge='start' onClick={() => onChange(parse(before, dateFmt, new Date()))}>
                <NavigateBeforeIcon/>
            </IconButton> :
            noBefore);

        setNext(after !== undefined ?
            <IconButton onClick={() => onChange(parse(after, dateFmt, new Date()))}>
                <NavigateNextIcon/>
            </IconButton> :
            noNext);
    }

    useEffect(() => {
        fetch('/api/neighbour-activities/' + date)
            .then(response => response.json())
            .then(setContent);
    }, [date]);

    return (<BeforeNextButtonsBase
        label={<Typography variant='body1' component='span' align='left'>Activity</Typography>}
        before={before}
        next={next}
    />);
}


function ImmediateBeforeNextButtons(props) {

    const {top, onBefore, onCentre, onNext, label} = props;

    return (<BeforeNextButtonsBase
        label={<Typography variant='body1' component='span' align='left'>{label}</Typography>}
        before={<IconButton edge='start' onClick={onBefore}><NavigateBeforeIcon/></IconButton>}
        centre={<IconButton onClick={onCentre}>{top ? <TodayIcon/> : <DateRangeIcon/>}</IconButton>}
        next={<IconButton onClick={onNext}><NavigateNextIcon/></IconButton>}
    />);
}


const YMD = ['Year', 'Month', 'Day'];


function DateButtons(props) {

    const {ymd, ymdSelected, datetime, onChange, onCentre} = props;
    const top = ymd === ymdSelected;

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

    function onHere() {
        // if top, revert to today, otherwise switch range at current date
        onCentre(top ? new Date() : datetime);
    }

    if (ymd > ymdSelected) {
        return <></>;
    } else {
        return (<ImmediateBeforeNextButtons top={top} label={YMD[ymd]}
                                            onCentre={onHere} onBefore={onBefore} onNext={onNext}/>);
    }
}


function ActiveDays(props) {
    const {date, onChange} = props;
    const [json, setJson] = useState(null);
    useEffect(() => {
        setJson(null);
        fetch('/api/active-days/' + date)
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
        fetch('/api/active-months/' + date)
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
    const writer = new Worker('/static/writer.js');

    useEffect(() => {
        setJson(null);
        fetch('/api/diary/' + date)
            .then(response => response.json())
            .then(json => setJson(json));
    }, [date]);

    const navigation = (
        <DiaryMenu ymdSelected={ymdSelected} datetime={datetime} dateFmt={dateFmt} history={history}/>
    );

    return (
        <Layout navigation={navigation} content={component({json, writer, history})} match={match} title={date}/>
    );
}
