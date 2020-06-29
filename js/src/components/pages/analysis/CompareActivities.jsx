import React, {useState} from 'react';
import {Text, Empty} from "../../../common/elements";
import {Grid, InputLabel, MenuItem, Select} from "@material-ui/core";
import {ActivityCard} from ".";
import {fmtHref, last} from '../../../common/functions';


export default function CompareActivities(props) {

    const {params} = props;
    const groups = Object.keys(params.activity_times_by_group).filter(group => params.activity_times_by_group[group].length > 1);
    if (groups.length === 0) return <Empty/>;

    const defaultGroup = params.latest_activity_group in groups ? params.latest_activity_group : groups[0];
    const [group, setGroup] = useState(defaultGroup);

    const latest_activity_time = params.all_activity_times[0];
    const localTimes = params.activity_times_by_group[group];
    const defaultLocalTime = latest_activity_time in localTimes ? latest_activity_time : localTimes[0];
    const [localTime, setLocalTime] = useState(defaultLocalTime);
    if (! localTimes.includes(localTime)) setLocalTime(last(localTimes));

    const compareTimes = localTimes.filter(time => time !== localTime);
    const [compareTime, setCompareTime] = useState(last(compareTimes));
    if (! compareTimes.includes(compareTime)) setCompareTime(last(compareTimes));

    const href = fmtHref('api/jupyter/compare_activities?local_time=%s&compare_time=%s&activity_group=%s',
        localTime, compareTime, group);

    return (<ActivityCard header='Compare Activities' pad={8} href={href}>
        <Grid item xs={12}><Text>
            <p>Graphical details for two activities, superimposed.</p>
        </Text></Grid>
        <Grid item xs={2}>
            <InputLabel shrink>Group</InputLabel>
            <Select onChange={event => setGroup(event.target.value)} value={group}>
                {Object.keys(params.activity_times_by_group).map((group, i) =>
                    <MenuItem value={group} key={i}>{group}</MenuItem>)}
            </Select>
        </Grid>
        <Grid item xs={5}>
            <InputLabel shrink>Reference Time</InputLabel>
            <Select onChange={event => setLocalTime(event.target.value)} value={localTime}>
                {localTimes.map((time, i) => <MenuItem value={time} key={i}>{time}</MenuItem>)}
            </Select>
        </Grid>
        <Grid item xs={5}>
            <InputLabel shrink>Compare Time</InputLabel>
            <Select onChange={event => setCompareTime(event.target.value)} value={compareTime}>
                {compareTimes.map((time, i) => <MenuItem value={time} key={i}>{time}</MenuItem>)}
            </Select>
        </Grid>
    </ActivityCard>);
}
