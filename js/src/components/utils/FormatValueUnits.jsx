import React from "react";
import {sprintf} from "sprintf-js";
import Text from "./Text";


export default function FormatValueUnits(props) {
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


