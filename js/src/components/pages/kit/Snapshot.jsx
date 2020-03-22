import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, DateButtons, FormatValueUnits, Layout, Loading, Picker, Text} from "../../elements";
import {Grid, InputLabel, List, ListItem, Typography} from "@material-ui/core";
import {FMT_DAY} from "../../../constants";
import {differenceInCalendarDays, format, formatDistance, parse} from 'date-fns';
import {makeStyles} from "@material-ui/core/styles";
import {setIds} from "../../functions";


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
            map((key, id) =>
                <NamedValue xs={2} name={key} value={statistic[key]} units={statistic.units} key={id}/>)}
    </>)
}


function StatisticsValues(props) {
    const {statistics} = props;
    return statistics.map(statistic => <Statistic statistic={statistic} key={statistic.id}/>);
}


function Added(props) {

    const {added, datetime} = props;
    const classes = useStyles();

    const date = parse(added, FMT_DAY, new Date());
    const age = differenceInCalendarDays(datetime, date);
    const readable = age > 7 ? ` (${formatDistance(date, datetime)})` : '';

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

    const {model, component, datetime} = props;
    const classes = useStyles();

    return (<>
        <Grid item xs={12} className={classes.h3}>
            <Typography variant='h3'>{model.name} / {component.name}</Typography>
        </Grid>
        <Added added={model.added} datetime={datetime}/>
        {'statistics' in model && <StatisticsValues statistics={model.statistics}/>}
    </>);
}


function ItemStatistics(props) {
    const {item, group, datetime} = props;
    return (<ColumnCard header={`${item.name} / ${group.name}`}>
        <Added added={item.added} datetime={datetime}/>
        {'statistics' in item && <StatisticsValues statistics={item.statistics}/>}
        {item.components.map(
            component => component.models.map(
                model => <ModelStatistics model={model} component={component} key={model.id}
                                          datetime={datetime}/>)).flat()}
    </ColumnCard>);
}


function Columns(props) {

    const {groups, datetime} = props;

    if (groups === null) {
        return <Loading/>;  // undefined initial data
    } else {
        let id = 0;
        groups.forEach(group => id = setIds(group, id, ['items', 'components', 'models', 'statistics']));
        return (<ColumnList>
            {groups.map(
                group => group.items.map(
                    item => <ItemStatistics item={item} group={group} key={item.id} datetime={datetime}/>)).flat()}
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
    const [json, setJson] = useState(null);

    useEffect(() => {
        setJson(null);
        fetch('/api/kit/' + date)
            .then(response => response.json())
            .then(json => setJson(json));
    }, [date]);

    return (
        <Layout navigation={<SnapshotMenu datetime={datetime} history={history}/>}
                content={<Columns groups={json} datetime={datetime}/>} match={match} title={`Kit: ${date}`}/>
    );
}
