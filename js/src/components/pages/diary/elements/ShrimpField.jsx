import React from 'react';
import {Grid} from "@material-ui/core";
import {PercentBar, Text} from '../../../utils';


export default function ShrimpField(prop) {
    const {json} = prop;
    const [label, from, to, arrow, ...stats] = json;
    const bars = stats.map(entry => {
        const [tag, lo, hi, id] = entry;
        const percent = 100 * (to.value - lo.value) / (hi.value - lo.value);
        return (<PercentBar percent={percent} label={tag.tag} key={entry.id}/>);
    });
    return (<>
        <Grid item xs={6}>
            <Text>{label.value}: {from.value}</Text>
            <Text secondary>{arrow.value}</Text>
            <Text>{to.value}</Text>
        </Grid>
        <Grid item xs={6} key={json.id + 'bars'}>
            {bars}
        </Grid>
    </>);
}
