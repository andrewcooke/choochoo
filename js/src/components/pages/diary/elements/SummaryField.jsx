import React from 'react';
import {Grid} from "@material-ui/core";
import {FormatValueUnits, Text} from '../../../utils';


export default function SummaryField(props) {
    const {json} = props;
    return (<Grid item xs={4}>
        <Text>{json.label}: </Text>
        <FormatValueUnits value={json.value} units={json.units} tag={json.tag}/>
    </Grid>);
}
