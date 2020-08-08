import React, {useEffect, useState} from 'react';
import {DateButtons, Picker, Layout} from "../../elements";
import {ColumnCard, ColumnList, Loading} from "../../../common/elements";
import {Grid, List, ListItem, Typography} from "@material-ui/core";
import {FMT_DAY} from "../../../constants";
import {format} from 'date-fns';
import {makeStyles} from "@material-ui/core/styles";
import {handleJson} from "../../functions";
import {StatisticsValues} from "./elements";


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
        {have_statistics && <StatisticsValues statistics={item.statistics} key='x'/>}
        {item.components.map(
            (component, i) => component.models.map(
                (model, j) => <ModelStatistics model={model} component={component} key={[i,j]}/>)).flat()}
    </ColumnCard>);
}


function Columns(props) {

    const {groups} = props;

    if (groups === null) {
        return <Loading/>;
    } else {
        return (<ColumnList>
            {groups.map(
                (group, i) => group.items.map(
                    (item, j) => <ItemStatistics item={item} group={group} key={[i,j]}/>)).flat()}
        </ColumnList>);
    }
}


// TODO - this isn't used?!
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
    const [groups, setGroups] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        setGroups(null);
        fetch('/api/kit/' + date)
            .then(handleJson(history, setGroups, setError));
    }, [date]);

    return (
        <Layout title={`Kit: ${date}`}
                content={<Columns groups={groups}/>} errorState={errorState}/>
    );
}
