import {Layout, MainMenu, Loading, ColumnCard, FormatValueUnits, Text, ColumnList} from "../../elements";
import React, {useEffect, useState} from "react";
import {Grid, Typography, InputLabel} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
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

    const {model} = props;
    const classes = useStyles();
    const have_statistics = 'statistics' in model;
    const n = have_statistics ? model['statistics'][0]['n'] : 0;

    return (<>
        <Grid item xs={12} className={classes.h3}>
            <Typography variant='h3'>{model.name} {n ? `/ ${n}` : ''}</Typography>
        </Grid>
        {have_statistics && <StatisticsValues statistics={model.statistics}/>}
    </>);
}


function ComponentStatistics(props) {
    const {component} = props;
    return (<ColumnCard header={component.name}>
        {component.models.map((model, index) => <ModelStatistics model={model} key={index}/>)}
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
