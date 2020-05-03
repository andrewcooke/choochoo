import {Grid, InputLabel} from "@material-ui/core";
import {FormatValueUnits} from "../../../elements";
import React from "react";


function NamedValue(props) {
    const {name, value, units, xs=3} = props;
    return (<Grid item xs={xs}>
        <InputLabel shrink>{name}</InputLabel>
        <FormatValueUnits value={value} units={units}/>
    </Grid>);
}


function Statistic(props) {
    const {statistic} = props;
    return (<>
        {Object.keys(statistic).
        filter(key => ! ['n', 'name', 'units', 'id'].includes(key)).
        map((key, i) =>
            <NamedValue xs={4} name={statistic.name} value={statistic[key]} units={statistic.units} key={i}/>)}
    </>)
}


export default function StatisticsValues(props) {
    const {statistics} = props;
    return statistics.map((statistic, i) => <Statistic statistic={statistic} key={i}/>);
}
