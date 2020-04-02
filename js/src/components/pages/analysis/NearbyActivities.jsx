import React, {useState} from 'react';
import {Text, Empty} from "../../elements";
import {Grid, InputLabel, MenuItem, Select} from "@material-ui/core";
import ActivityCard from "./ActivityCard";
import {fmtHref} from "../../functions";


export default function NearbyActivities(props) {

    const {params} = props;
    if (Object.keys(params.nearby_constraints).length === 0) return <Empty/>;

    const [constraint, setConstraint] = useState(params.nearby_constraints[0]);
    const href = fmtHref('api/jupyter/nearby_activities?constraint=%s', constraint);

    return (<ActivityCard header='Nearby Activities' displayWidth={6} href={href}>
        <Grid item xs={12}><Text>
            <p>A plot of activity routes within the contraint area, grouped by similarity.</p>
        </Text></Grid>
        <Grid item xs={6}>
            <InputLabel shrink>Group</InputLabel>
            <Select onChange={event => setConstraint(event.target.value)} value={constraint}>
                {params.nearby_constraints.map(constraint =>
                    <MenuItem value={constraint} key={constraint}>{constraint}</MenuItem>)}
            </Select>
        </Grid>
    </ActivityCard>);
}
