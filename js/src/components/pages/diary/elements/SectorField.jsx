import React from 'react';
import {Grid, InputLabel, Link, Tooltip, Typography} from "@material-ui/core";
import {sprintf} from "sprintf-js";
import {FormatValueUnits, Image} from '../../../elements';
import {Text} from '../../../../common/elements';
import {Measures} from ".";
import {makeStyles} from "@material-ui/core/styles";
import log from "loglevel";


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
        padding: '1px',
        '&:hover': {
            border: '1px solid white',
            padding: '0px',
        },
    },
}));


export default function SectorField(prop) {

    const {json, history} = prop;
    const [title, location, thumbnail, sparkline, distance, time] = json;
    const classes = useStyles();

    function onClick() {
        history.push(`/sector/${title.db[0]}?from=${title.db[1]}`);
    }

    function onAuxClick() {
        window.open(`/sector/${title.db[0]}?from=${title.db[1]}`, '_blank');
    }

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
                <Tooltip title='Display sector analysis' placement='top'>
                    <Link onClick={onClick} onAuxClick={onAuxClick}>
                        <Image url={thumbnail.value} className={classes.thumbnail}/>
                    </Link>
                </Tooltip>
            </Grid>
        </Grid>
    </>);
}
