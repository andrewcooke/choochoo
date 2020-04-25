import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, DateButtons, FormatValueUnits, Layout, Loading, Picker, Text} from "../../elements";
import {Grid, InputLabel, List, ListItem, Typography} from "@material-ui/core";
import {FMT_DAY} from "../../../constants";
import {differenceInCalendarDays, format, formatDistance, parse} from 'date-fns';
import {makeStyles} from "@material-ui/core/styles";
import {handleJson, setIds} from "../../functions";
import StatisticsValues from "./elements/StatisticsValues";


const useStyles = makeStyles(theme => ({
    right: {
        textAlign: 'right',
    },
    center: {
        textAlign: 'center',
    },
    left: {
        textAlign: 'left',
    },
    h3: {
        marginTop: theme.spacing(2),
    },
}));


function ModelStatistics(props) {

    const {model, component} = props;
    const classes = useStyles();
    const have_statistics = 'statistics' in model;
    const n = have_statistics ? Math.max(...model['statistics'].map(statistic => statistic['n'])) : 0;

    return (<>
        <Grid item xs={12} className={classes.h3}>
            <Typography variant='h3'>{model.name} / {component.name} {n ? `/ ${n} uses` : ''}</Typography>
        </Grid>
        {have_statistics && <StatisticsValues statistics={model.statistics}/>}
    </>);
}


function ItemStatistics(props) {

    const {item, group} = props;
    const have_statistics = 'statistics' in item;
    const n = have_statistics ? Math.max(...item['statistics'].map(statistic => statistic['n'])) : 0;

    return (<ColumnCard header={`${item.name} / ${group.name} ${n ? `/ ${n} uses` : ''}`}>
        {have_statistics && <StatisticsValues statistics={item.statistics}/>}
        {item.components.map(
            component => component.models.map(
                model => <ModelStatistics model={model} component={component} key={model.id}/>)).flat()}
    </ColumnCard>);
}


function Columns(props) {

    const {groups} = props;

    if (groups === null) {
        return <Loading/>;
    } else {
        let id = 0;
        groups.forEach(group => id = setIds(group, id, ['items', 'components', 'models', 'statistics']));
        return (<ColumnList>
            {groups.map(
                group => group.items.map(
                    item => <ItemStatistics item={item} group={group} key={item.id}/>)).flat()}
        </ColumnList>);
    }
}


function SnapshotMenu(props) {

    const {datetime, history} = props;
    const classes = useStyles();

    function setDate(datetime) {
        history.push('/kit/' + format(datetime, FMT_DAY));
    }

    return (<List component="nav" className={classes.root}>
        <ListItem>
            <Picker ymdSelected={2} datetime={datetime} onChange={setDate}/>
        </ListItem>
        <DateButtons ymd={2} ymdSelected={2} datetime={datetime} onChange={setDate} onCentre={setDate}/>
        <DateButtons ymd={1} ymdSelected={2} datetime={datetime} onChange={setDate}/>
        <DateButtons ymd={0} ymdSelected={2} datetime={datetime} onChange={setDate}/>
    </List>);
}


export default function Snapshot(props) {


    const {match, history} = props;
    const {date} = match.params;
    const datetime = parse(date, FMT_DAY, new Date());
    const [groups, setGroups] = useState(null);
    const busyState = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const [reads, setReads] = useState(0);

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        setGroups(null);
        fetch('/api/kit/' + date)
            .then(handleJson(history, setGroups, setError, busyState));
    }, [`${date} ${reads}`]);

    return (
        <Layout navigation={<SnapshotMenu datetime={datetime} history={history}/>}
                content={<Columns groups={groups}/>}
                match={match} title={`Kit: ${date}`} reload={reload} history={history}
                busyState={busyState} errorState={errorState}/>
    );
}
