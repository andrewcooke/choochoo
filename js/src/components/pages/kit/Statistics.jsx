import React, {useEffect, useState} from "react";
import {ColumnCard, ColumnList, Loading} from "../../../common/elements";
import {Grid, Typography} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {StatisticsValues} from "./elements";
import {handleJson} from "../../functions";
import {Layout} from "../../elements";


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
        {component.models.map((model, i) => <ModelStatistics model={model} key={i}/>)}
    </ColumnCard>);
}


function Columns(props) {

    const {components} = props;

    if (components === null) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<ColumnList>
            {components.map((component, i) => <ComponentStatistics component={component} key={i}/>)}
        </ColumnList>);
    }
}


export default function Statistics(props) {

    const {history} = props;
    const [components, setComponents] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        setComponents(null);
        fetch('/api/kit/statistics')
            .then(handleJson(history, setComponents, setError));
    });

    return (
        <Layout title='Kit Statistics'
                content={<Columns components={components}/>} errorState={errorState}/>
    );
}
