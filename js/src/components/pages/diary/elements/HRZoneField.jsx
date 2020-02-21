import React from 'react';
import {Grid} from "@material-ui/core";
import {PercentBar, Text} from '../../../utils';


export default function HRZoneField(prop) {
    const {json} = prop;
    const [zone, percent] = json;
    const label = percent.value.toFixed(1) + '%/' + zone.value;
    return (<>
        <Grid item xs={3}>
            <Text>Zone {zone.value}</Text>
        </Grid>
        <Grid item xs={9}>
            <PercentBar percent={percent.value} width={200}/>
        </Grid>
    </>);
}
