import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, Layout, Loading, MainMenu, Text, FormatValueUnits} from "../../elements";
import {Grid, InputLabel, Typography} from "@material-ui/core";


function NamedValue(props) {
    const {name, value, units, xs=3} = props;
    console.log(`${name} ${units}`)
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


function ModelStatistics(props) {

    const {model, component} = props;

    return (<>
        <Grid item xs={12}><Typography variant='h3'>{model.name} / {component.name}</Typography></Grid>
        <StatisticsValues statistics={model.statistics}/>
    </>);
}


function ItemStatistics(props) {

    const {item, group} = props;

    console.log(item);
    return (<ColumnCard header={`${item.name} / ${group.name}`}>
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
