import React from 'react';
import {Grid} from "@material-ui/core";
import {Text} from '../../../elements';
import FormatValueUnits from "./FormatValueUnits";


export default function ValueField(props) {
    const {json} = props;
    if (json.measures) {
        return <MeasuredValueField {...props}/>
    } else {
        return <SimpleValueField {...props}/>
    }
}


function CommonValueField(props) {
    const {json} = props;
    return (<>
        <Text>{json.label}: </Text>
        <FormatValueUnits value={json.value} units={json.units} tag={json.tag}/>
    </>);
}


function SimpleValueField(props) {
    return (<Grid item xs={6}>
        <CommonValueField {...props}/>
    </Grid>);
}


function MeasuredValueField(props) {
    const {json} = props;
    return (<>
        <Grid item xs={6}>
            <CommonValueField {...props}/>
        </Grid>
        <Grid item xs={6}>
            <Measures measures={json.measures}/>
        </Grid>
    </>);
}
