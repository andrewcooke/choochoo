import React from 'react';
import {PercentBar} from '../../../../common/elements';
import {barWidth} from "../../../../common/functions";


export default function Measures(props) {
    const {measures} = props;
    const schedules = Object.entries(measures.schedules);
    return schedules.map((entry, i) => {
        const [period, [percent, rank]] = entry;
        const label = rank + '/' + period;
        return (<PercentBar percent={percent} label={label} key={i} fraction={barWidth(schedules)}/>);
    });
}