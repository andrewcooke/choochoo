import React from 'react';
import {Grid} from "@material-ui/core";
import {sprintf} from "sprintf-js";
import {Text, FormatValueUnits} from '../../../elements';
import Measures from "./Measures";
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
}));


export default function ClimbField(prop) {

    const {json} = prop;
    const [, elevation, distance, time] = json;
    const classes = useStyles();

    return (<>
        <Grid item xs={5} className={classes.left}>
            <Text>{sprintf('%d', elevation.value)}m</Text>
            <Text secondary> / </Text>
            <FormatValueUnits value={distance.value} units={distance.units}/>
            <Text secondary> / </Text>
            <FormatValueUnits value={time.value} units={time.units}/>
        </Grid>
        <Grid item xs={7} className={classes.right}>
            <Measures measures={elevation.measures}/>
        </Grid>
    </>);
}
