import React from 'react';
import {Grid, InputLabel} from "@material-ui/core";
import {Text, PercentBar} from '../../../../common/elements';
import {makeStyles} from "@material-ui/core/styles";
import {barWidth} from "../../../../common/functions";


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
}));


export default function ShrimpField(prop) {
    const {json} = prop;
    const [label, from, to, arrow, ...stats] = json;
    const classes = useStyles();

    const bars = stats.map((entry, i) => {
        const [tag, lo, hi] = entry;
        const percent = 100 * (to.value - lo.value) / (hi.value - lo.value);
        return (<PercentBar percent={percent} label={tag.tag} key={i} fraction={barWidth(stats)}/>);
    });

    return (<>
        <Grid item xs={4} className={classes.left}>
            <InputLabel shrink>{label.value}</InputLabel>
            <Text>{from.value} {arrow.value} {to.value}</Text>
        </Grid>
        <Grid item xs={8} className={classes.right}>
            {bars}
        </Grid>
    </>);
}
