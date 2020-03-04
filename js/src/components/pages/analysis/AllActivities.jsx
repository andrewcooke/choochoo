import React from 'react';
import {ColumnCard, LinkButton, Text} from "../../elements";
import {Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    center: {
        textAlign: 'center',
    },
    left: {
        textAlign: 'left',
    },
    right: {
        textAlign: 'right',
    },
}));


export default function AllActivities(props) {

    const {params} = props;
    const classes = useStyles();

    const href = sprintf('jupyter/all_activities?start=%s&finish=%s',
        params.activities_start, params.activities_finish);

    return (<ColumnCard header='All Activities'>
        <Grid item xs={12}><Text>
            <p>Foo.</p>
        </Text></Grid>
        <Grid item xs={12} className={classes.right}><LinkButton href={href}>Display</LinkButton></Grid>
    </ColumnCard>);
}
