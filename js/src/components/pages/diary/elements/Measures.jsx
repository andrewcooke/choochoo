import React from 'react';
import PercentBar from './PercentBar';


export default function Measures(props) {
    const {measures} = props;
    return Object.entries(measures.schedules).map((entry, i) => {
        const [period, [percent, rank]] = entry;
        const label = rank + '/' + period;
        return (<PercentBar percent={percent} label={label} key={i}/>);
    });
}