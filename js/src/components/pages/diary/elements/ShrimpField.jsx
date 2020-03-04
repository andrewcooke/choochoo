import React from 'react';
import {Grid} from "@material-ui/core";
import {Text} from '../../../elements';
import {makeStyles} from "@material-ui/core/styles";
import PercentBar from "./PercentBar";


const useStyles = makeStyles(theme => ({
    center: {
        textAlign: 'center',
    },
    left: {
        textAlign: 'left',
    },
}));


export default function ShrimpField(prop) {
    const {json} = prop;
    const [label, from, to, arrow, ...stats] = json;
    const classes = useStyles();

    const bars = stats.map(entry => {
        const [tag, lo, hi, id] = entry;
        const percent = 100 * (to.value - lo.value) / (hi.value - lo.value);
        return (<PercentBar percent={percent} label={tag.tag} key={entry.id}/>);
    });

    return (<>
        <Grid item xs={3}><Text>{label.value}:</Text></Grid>
        <Grid item xs={1}><Text>{from.value}</Text></Grid>
        <Grid item xs={1} className={classes.center}><Text>{arrow.value}</Text></Grid>
        <Grid item xs={1} className={classes.left}><Text>{to.value}</Text></Grid>
        <Grid item xs={6}>
            {bars}
        </Grid>
    </>);
}
