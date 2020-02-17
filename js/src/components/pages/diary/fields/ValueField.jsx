import React from 'react';
import {Grid} from "@material-ui/core";
import {Text} from '../../../utils';


export default function ValueField(props) {
    const {json} = props;
    if (json.measures) {
        return <MeasuredValueField {...props}/>
    } else {
        return <SimpleValueField {...props}/>
    }
}


function SimpleValueField(props) {
    const {json} = props;
    return (<Grid item xs={4}>
        <p>
            <Text secondary>{json.label}:</Text>
            <Text>{json.value}</Text>
        </p>
    </Grid>);
}


function MeasuredValueField(props) {
    const {json} = props;
    return (<Grid item xs={12}>
        <p>
            <Text secondary>{json.label}:</Text>
            <Text>{json.value}</Text>
            {json.units && <Text secondary>{json.units}</Text>}
            <Schedules schedules={json.measures.schedules}/>
        </p>
    </Grid>);
}


function Schedules(props) {
    const {schedules} = props;
    return (Object.entries(schedules).map(entry => {
        const [period, [percent, rank]] = entry;
        return (<Text>{period}={percent}/{rank}</Text>);
    }));
}
