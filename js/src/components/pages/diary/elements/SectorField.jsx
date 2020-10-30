import React from 'react';
import {Grid, InputLabel, Typography} from "@material-ui/core";
import {sprintf} from "sprintf-js";
import {FormatValueUnits, Image} from '../../../elements';
import {Text} from '../../../../common/elements';
import {Measures} from ".";
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
    sparkline: {
        marginTop: '10px',
    },
    thumbnail: {
        marginRight: '10px',
    },
}));


export default function SectorField(prop) {

    const {json} = prop;
    const [, location, thumbnail, sparkline, distance, time] = json;
    const classes = useStyles();

    return (<>
        <Grid container item xs={4} className={classes.left}>
            <Grid item xs={12}>
                <InputLabel shrink>Sector at {sprintf('%2.1f', location.value)}{location.units}</InputLabel>
                <FormatValueUnits value={distance.value} units={distance.units}/>
                <Text secondary> </Text>
                <FormatValueUnits value={time.value} units={time.units}/>
            </Grid>
        </Grid>
        <Grid container item xs={8} className={classes.right}>
            <Grid item xs={9}>
                <Image url={sparkline.value} className={classes.sparkline}/>
            </Grid>
            <Grid item xs={3}>
                <Image url={thumbnail.value} className={classes.thumbnail}/>
            </Grid>
        </Grid>
    </>);
}
