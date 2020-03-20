import React from 'react';
import {Grid, InputLabel} from "@material-ui/core";
import {FormatValueUnits} from "../../../elements";


export default function SummaryField(props) {
    const {json} = props;
    return (<Grid item xs={2}>
        <InputLabel shrink>{json.label}</InputLabel>
        <FormatValueUnits value={json.value} units={json.units} tag={json.tag}/>
    </Grid>);
}
