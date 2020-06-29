import React from "react";
import {sprintf} from "sprintf-js";
import {Text} from "../../common/elements";
import {FMT_DAY_TIME} from "../../constants";
import {format} from 'date-fns';


export default function FormatValueUnits(props) {
    const {value, units=''} = props;
    if (units === 's') {
        return <FormatSeconds value={value}/>
    } else if (['kmh⁻¹', 'km', '%'].includes(units)) {
        if (value >= 100) {
            return (<Text>{sprintf('%d', value)}{units}</Text>);
        } else {
            return (<Text>{sprintf('%.1f', value)}{units}</Text>);
        }
    } else if (['W', 'bpm', 'm', 'kJ', 'kCal'].includes(units)) {
        return (<Text>{sprintf('%d', value)}{units}</Text>);
    } else if (['FF', 'stp'].includes(units)) {
        return (<Text>{sprintf('%d', value)}</Text>);
    } else if (units === 'date') {
        return (<Text>{format(value, FMT_DAY_TIME)}</Text>);
    } else {
        return (<Text>{value}{units}</Text>);
    }
}


function FormatSeconds(props) {
    const {value} = props;
    const units = [[60, 's'], [60, 'm'], [24, 'h'], [999, 'd']];

    function helper(value, cumulative, units, depth=0) {
        let [[factor, label], ...rest] = units;
        let time = '';
        let maxDepth = depth;
        if (value > factor * cumulative) {
            [value, time, maxDepth] = helper(value, cumulative * factor, rest, depth+1);
        }
        if (maxDepth - depth < 2) {  // restrict to two most significant units for compact display
            const n = Math.trunc(value / cumulative);
            time = time + sprintf('%d', n) + label;
            value = value - n * cumulative;
        }
        return [value, time, maxDepth];
    }

    var text = helper(value, 1, units)[1];
    const match = /(\d+d.*?)\d+s/.exec(text);
    if (match) text = match[1];

    return (<Text>{text}</Text>);
}
