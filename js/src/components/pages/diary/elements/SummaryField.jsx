import React from 'react';
import {Grid} from "@material-ui/core";
import FormatValueUnits from "./FormatValueUnits";
import {Text} from '../../../elements';


export default function SummaryField(props) {
    const {json} = props;
    return (<>
        <Grid item xs={1}><Text secondary>{json.label}:</Text></Grid>
        <Grid item xs={2}><FormatValueUnits value={json.value} units={json.units} tag={json.tag}/></Grid>
    </>);
}
