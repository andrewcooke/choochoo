import React, {useEffect, useState} from "react";
import {format, parse} from "date-fns";
import {List, ListItem} from "@material-ui/core";
import {ActivityButtons, DateButtons, Picker} from "../elements";
import {ListItemLink} from "../../common/elements";
import {FMT_DAY, FMT_MONTH, FMT_YEAR} from "../../constants";
import {makeStyles} from "@material-ui/styles";
import {Calendar, Months} from ".";
import ListItemText from "@material-ui/core/ListItemText";
import {KeyboardArrowLeft} from "@material-ui/icons";
import {useHistory, useLocation} from 'react-router-dom';
import {csrfFetch} from "../functions";


const useStyles = makeStyles(theme => ({
    root: {
        width: '100%',
        maxWidth: 360,
        backgroundColor: theme.palette.background.paper,
    },
    right: {
        textAlign: 'right',
    },
}));


function ActiveDays(props) {
    const {date, onChange} = props;
    const [json, setJson] = useState(null);
    useEffect(() => {
        setJson(null);
        csrfFetch('/api/diary/active-days/' + date)
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
        csrfFetch('/api/diary/active-months/' + date)
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


export default function DiaryMenu(props) {

    const {setDiaryOpen} = props;
    const history = useHistory();
    const location = useLocation().pathname;
    const classes = useStyles();
    // the number of - in the url (so year alone is 0, month is 1 and day is 2)
    const ymdSelected = (location.match(/-/g) || []).length;
    const dateFmt = {0: FMT_YEAR, 1: FMT_MONTH, 2: FMT_DAY}[ymdSelected];
    const datetime = parse(location.substring(1), dateFmt, new Date());
    const date = format(datetime, dateFmt);

    function setDate(date) {
        history.push('/' + date);
    }

    function setDatetime(datetime, fmt) {
        setDate(format(datetime, fmt));
    }

    return (<List component="nav" className={classes.root}>
        <ListItemLink primary='Choochoo' to='/'/>
        <ListItem button onClick={() => setDiaryOpen(1)}>
            <ListItemText>Diary</ListItemText>
            <KeyboardArrowLeft/>
        </ListItem>
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
