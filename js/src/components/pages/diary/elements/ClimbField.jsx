import React from 'react';
import {Grid} from "@material-ui/core";
import {sprintf} from "sprintf-js";
import {Text} from '../../../elements';
import FormatValueUnits from "./FormatValueUnits";
import Measures from "./Measures";


export default function ClimbField(prop) {

    const {json} = prop;
    const [, elevation, distance, time] = json;

    return (<>
        <Grid item xs={6}>
            <Text>{sprintf('%d', elevation.value)}m</Text>
            <Text secondary> / </Text>
            <FormatValueUnits value={distance.value} units={distance.units}/>
            <Text secondary> in </Text>
            <FormatValueUnits value={time.value} units={time.units}/>
        </Grid>
        <Grid item xs={6}>
            <Measures measures={elevation.measures}/>
        </Grid>
    </>);
}
