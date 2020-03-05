import React, {useState} from 'react';
import {Text} from "../../elements";
import {Grid, InputLabel, MenuItem, Select} from "@material-ui/core";
import ActivityCard from "./ActivityCard";


export default function CompareActivities(props) {

    const {params} = props;
    const [group, setGroup] = useState(params.latest_activity_group);
    const [localTime, setLocalTime] = useState(params.latest_activity_time);
    const [compareTime, setCompareTime] = useState(params.latest_activity_time);
    const href = sprintf('jupyter/compare_activitties?local_time=%s&compare_time=%s&activity_group_name=%s',
        localTime, compareTime, group);

    // force consistent dates (will re-render)
    const datetimes = params.activities_by_group[group];
    [localTime, compareTime].forEach(time => {
        if (time !== null && ! datetimes.includes(time)) {
            setLocalTime(datetimes[datetimes.length - 1])
        }
    });

    return (<ActivityCard header='Compare Activities' href={href}>
        <Grid item xs={12}><Text>
            <p>Graphical details for two activities, superimposed.</p>
        </Text></Grid>
        <Grid item xs={2}>
            <InputLabel shrink>Group</InputLabel>
            <Select onChange={event => setGroup(event.target.value)} value={group}>
                {Object.keys(params.activities_by_group).map(group =>
                    <MenuItem value={group} key={group}>{group}</MenuItem>)}
            </Select>
        </Grid>
        <Grid item xs={5}>
            <InputLabel shrink>Reference Time</InputLabel>
            <Select onChange={event => setLocalTime(event.target.value)} value={localTime}>
                {params.activities_by_group[group].map(datetime =>
                    <MenuItem value={datetime} key={datetime}>{datetime}</MenuItem>)}
            </Select>
        </Grid>
        <Grid item xs={5}>
            <InputLabel shrink>Compare Time</InputLabel>
            <Select onChange={event => setCompareTime(event.target.value)} value={compareTime}>
                {params.activities_by_group[group].map(datetime =>
                    <MenuItem value={datetime} key={datetime}>{datetime}</MenuItem>)}
            </Select>
        </Grid>
    </ActivityCard>);
}
