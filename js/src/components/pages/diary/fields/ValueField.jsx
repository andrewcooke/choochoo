import React from 'react';
import {Grid} from "@material-ui/core";
import {PercentBar, Text} from '../../../utils';


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
        <Text>{json.value}</Text>
        {json.units && <Text secondary> {json.units}</Text>}
    </>);
}


function SimpleValueField(props) {
    return (<Grid item xs={4}>
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
            <Schedules schedules={json.measures.schedules}/>
        </Grid>
    </>);
}


function Schedules(props) {

    const {schedules} = props;

    return (Object.entries(schedules).map(entry => {
        const [period, [percent, rank]] = entry;
        const label = rank + '/' + period;
        return (<PercentBar percent={percent} label={label}/>);
    }));
}

