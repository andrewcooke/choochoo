import {Layout, MainMenu, Loading, ColumnCard, FormatValueUnits, Text, ColumnList} from "../../elements";
import React, {useEffect, useState} from "react";
import {Grid, Typography, InputLabel} from "@material-ui/core";
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
            filter(key => ! ['n', 'name', 'units', 'id'].includes(key)).
            map((key, id) =>
                <NamedValue xs={2} name={key} value={statistic[key]} units={statistic.units} key={id}/>)}
    </>)
}


function StatisticsValues(props) {
    const {statistics} = props;
    return statistics.map(statistic => <Statistic statistic={statistic} key={statistic.id}/>);
}


function ModelStatistics(props) {

    const {model} = props;
    const classes = useStyles();

    return (<>
        <Grid item xs={12} className={classes.h3}>
            <Typography variant='h3'>{model.name}</Typography>
        </Grid>
        {'statistics' in model && <StatisticsValues statistics={model.statistics}/>}
    </>);
}


function ComponentStatistics(props) {
    const {component} = props;
    return (<ColumnCard header={component.name}>
        {component.models.map(model => <ModelStatistics model={model}/>)}
    </ColumnCard>);
}


function Columns(props) {

    const {components, update} = props;

    if (components === null) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<ColumnList>
            {components.map(component => <ComponentStatistics component={component} key={component.db}/>)}
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
        <Layout navigation={<MainMenu kit/>}
                content={<Columns components={json}/>} match={match} title='Kit Statistics'/>
    );
}
