import React, {useState} from 'react';
import {Text, Empty} from "../../elements";
import {Grid, InputLabel, MenuItem, Select} from "@material-ui/core";
import ActivityCard from "./ActivityCard";
import {fmtHref, last} from '../../functions';


export default function CompareActivities(props) {

    const {params} = props;
    const groups = Object.keys(params.activities_by_group).filter(group => params.activities_by_group[group].length > 1);
    if (groups.length === 0) return <Empty/>;

    const defaultGroup = params.latest_activity_group in groups ? params.latest_activity_group : groups[0];
    const [group, setGroup] = useState(defaultGroup);

    const localTimes = params.activities_by_group[group];
    const defaultLocalTime = params.latest_activity_time in localTimes ? params.latest_activity_time : last(localTimes);
    const [localTime, setLocalTime] = useState(defaultLocalTime);
    if (! localTimes.includes(localTime)) setLocalTime(last(localTimes));

    const compareTimes = localTimes.filter(time => time !== localTime);
    const [compareTime, setCompareTime] = useState(last(compareTimes));
    if (! compareTimes.includes(compareTime)) setCompareTime(last(compareTimes));

    const href = fmtHref('api/jupyter/compare_activities?local_time=%s&compare_time=%s&activity_group=%s',
        localTime, compareTime, group);

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
                {localTimes.map(time => <MenuItem value={time} key={time}>{time}</MenuItem>)}
            </Select>
        </Grid>
        <Grid item xs={5}>
            <InputLabel shrink>Compare Time</InputLabel>
            <Select onChange={event => setCompareTime(event.target.value)} value={compareTime}>
                {compareTimes.map(time => <MenuItem value={time} key={time}>{time}</MenuItem>)}
            </Select>
        </Grid>
    </ActivityCard>);
}
