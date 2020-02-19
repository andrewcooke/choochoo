import React from 'react';
import {Grid} from "@material-ui/core";
import {PercentBar, Text} from '../../../utils';
import {sprintf} from 'sprintf-js';


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
        <FormatValueUnits value={json.value} units={json.units}/>
    </>);
}


function FormatValueUnits(props) {
    const {value, units} = props;
    if (units === 's') {
        return <FormatSeconds value={value}/>
    } else if (units === 'm') {
        return (<Text>{sprintf('%.1fkm', value / 1000)}</Text>);
    } else if (units === 'kmh⁻¹') {
        return (<Text>{sprintf('%.1f', value)}{units}</Text>);
    } else if (['W', 'bpm'].includes(units)) {
        return (<Text>{sprintf('%d', value)}{units}</Text>);
    } else if (units === 'FF') {
        return (<Text>{sprintf('%d', value)}</Text>);
    } else if (units) {
        return (<Text>{value}{units}</Text>);
    } else {
        return (<Text>{value}</Text>);
    }
}


function FormatSeconds(props) {
    const {value} = props;
    const units = [[60, '%02d', 's'], [60, '%02d', 'm'], [24, '%d', 'h'], [999, '%d', 'd']];

    function helper(value, cumulative, units) {
        const [[factor, format, label], ...rest] = units;
        let time = '';
        if (value > factor * cumulative) {
            [value, time] = helper(value, cumulative * factor, rest);
        }
        const n = Math.trunc(value / cumulative);
        time = time + sprintf(format, n) + label;
        value = value - n * cumulative;
        return [value, time];
    }

    return (<Text>{helper(value, 1, units)[1]}</Text>);
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
