import React from "react";
import {sprintf} from "sprintf-js";
import Text from "./Text";


export default function FormatValueUnits(props) {
    const {value, units, tag} = props;
    if (units === 's') {
        return <FormatSeconds value={value}/>
    } else if (['kmh⁻¹', 'km'].includes(units)) {
        return (<Text>{sprintf('%.1f', value)}{units}</Text>);
    } else if (['W', 'bpm', 'm'].includes(units)) {
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
        let [[factor, format, label], ...rest] = units;
        let time = '';
        if (value > factor * cumulative) {
            [value, time] = helper(value, cumulative * factor, rest);
        } else {
            format = '%d';  /* outermost value is not padded */
        }
        const n = Math.trunc(value / cumulative);
        time = time + sprintf(format, n) + label;
        value = value - n * cumulative;
        return [value, time];
    }

    return (<Text>{helper(value, 1, units)[1]}</Text>);
}
