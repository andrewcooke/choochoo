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


export default function Calendar(props) {
    const classes = useStyles();
    return (<ColumnCard header='Calendar'>
        <Grid item xs={12}><Text>
            <p>Various representations of all activities, across all dates, showing distance, time, SHRIMP, etc.</p>
        </Text></Grid>
        <Grid item xs={12} className={classes.right}><LinkButton href='jupyter/calendar'>Display</LinkButton></Grid>
    </ColumnCard>);
}
