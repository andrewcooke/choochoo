import {Grid, IconButton, ListItem, Typography} from "@material-ui/core";
import NavigateBeforeIcon from "@material-ui/icons/NavigateBefore";
import NavigateNextIcon from "@material-ui/icons/NavigateNext";
import React, {useEffect, useState} from "react";
import {add, parse} from "date-fns";
import TodayIcon from "@material-ui/icons/Today";
import DateRangeIcon from "@material-ui/icons/DateRange";


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


export function ActivityButtons(props) {

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
        fetch('/api/diary/neighbour-activities/' + date)
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
        centre={onCentre === null ? null :
                <IconButton onClick={onCentre}>{top ? <TodayIcon/> : <DateRangeIcon/>}</IconButton>}
        next={<IconButton onClick={onNext}><NavigateNextIcon/></IconButton>}
    />);
}


const YMD = ['Year', 'Month', 'Day'];


export default function DateButtons(props) {

    const {ymd, ymdSelected, datetime, onChange, onCentre=null} = props;
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
                                            onCentre={onCentre === null ? null : onHere}
                                            onBefore={onBefore} onNext={onNext}/>);
    }
}
