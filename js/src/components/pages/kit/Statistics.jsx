import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, FormatValueUnits, Layout, Loading, MainMenu, Text} from "../../elements";
import {Grid, InputLabel, Typography} from "@material-ui/core";
import {FMT_DAY} from "../../../constants";
import {differenceInCalendarDays, formatDistanceToNow, parse} from 'date-fns';
import {makeStyles} from "@material-ui/core/styles";


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


function NamedValue(props) {
    const {name, value, units, xs=3} = props;
    return (<Grid item xs={xs}>
        <InputLabel shrink>{name}</InputLabel>
        <FormatValueUnits value={value} units={units}/>
    </Grid>);
}


function Statistic(props) {
    const {statistic} = props;
    return (<>
        <Grid item xs={3}><Text>{statistic.name}</Text></Grid>
        <NamedValue xs={1} name='n' value={statistic.n}/>
        {Object.keys(statistic).
            filter(key => ! ['n', 'name', 'units'].includes(key)).
            map(key => <NamedValue xs={2} name={key} value={statistic[key]} units={statistic.units}/>)}
    </>)
}


function StatisticsValues(props) {
    const {statistics} = props;
    return statistics.map(statistic => <Statistic statistic={statistic}/>);
}


function Added(props) {

    const {added} = props;
    const classes = useStyles();

    const date = parse(added, FMT_DAY, new Date());
    const age = differenceInCalendarDays(Date.now(), date);
    const readable = age > 7 ? ` (${formatDistanceToNow(date)})` : '';

    return (<>
        <Grid item xs={3}><Text>Added</Text></Grid>
        <Grid item xs={3}><Text>{added}</Text></Grid>
        <Grid item xs={6} className={classes.left}>
            <InputLabel shrink>age</InputLabel>
            <Text>{age}d {readable}</Text>
        </Grid>
    </>);
}


function ModelStatistics(props) {

    const {model, component} = props;
    const classes = useStyles();

    return (<>
        <Grid item xs={12} className={classes.h3}><Typography variant='h3'>{model.name} / {component.name}</Typography></Grid>
        <Added added={model.added}/>
        <StatisticsValues statistics={model.statistics}/>
    </>);
}


function ItemStatistics(props) {
    const {item, group} = props;
    return (<ColumnCard header={`${item.name} / ${group.name}`}>
        <Added added={item.added}/>
        <StatisticsValues statistics={item.statistics}/>
        {item.components.map(
            component => component.models.map(
                model => <ModelStatistics model={model} component={component} key={model.db}/>)).flat()}
    </ColumnCard>);
}


function Columns(props) {

    const {groups} = props;

    if (groups === null) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<ColumnList>
            {groups.map(
                group => group.items.map(
                    item => <ItemStatistics item={item} group={group} key={item.db}/>)).flat()}
        </ColumnList>);
    }
}


export default function Statistics(props) {

    const {match} = props;
    const [json, setJson] = useState(null);

    useEffect(() => {
        setJson(null);
        fetch('/api/kit/statistics')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [1]);

    return (
        <Layout navigation={<MainMenu/>} content={<Columns groups={json}/>} match={match} title='Kit Statistics'/>
    );
}
