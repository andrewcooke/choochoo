import React from 'react';
import {Grid} from "@material-ui/core";
import {Text, PercentBar} from '../../../../common/elements';


export default function HRZoneField(prop) {
    const {json} = prop;
    const [zone, percent] = json;
    return (<>
        <Grid item xs={3}>
            <Text>Zone {zone.value}</Text>
        </Grid>
        <Grid item xs={9}>
            <PercentBar percent={percent.value} width={200} fraction={0.99}/>
        </Grid>
    </>);
}
