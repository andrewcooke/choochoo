import React, {useState} from 'react';
import {Text, Empty} from "../../../common/elements";
import {Grid, InputLabel, MenuItem, Select} from "@material-ui/core";
import {ActivityCard} from ".";
import {fmtHref} from "../../../common/functions";


export default function ActivityDetails(props) {

    const {params} = props;
    const [group, setGroup] = useState(params.latest_activity_group);
    const [datetime, setDatetime] = useState(params.all_activity_times[0]);
    const href = fmtHref('api/jupyter/activity_details?local_time=%s&activity_group=%s', datetime, group);

    if (Object.keys(params.activity_times_by_group).length === 0) return <Empty/>;

    // force consistent date (will re-render)
    const datetimes = params.activity_times_by_group[group];
    if (datetime !== null && ! datetimes.includes(datetime)) {
        setDatetime(datetimes[0])
    }

    return (<ActivityCard header='Activity Details' pad={1} href={href}>
        <Grid item xs={12}><Text>
            <p>Graphical details for the given activity.</p>
        </Text></Grid>
        <Grid item xs={2}>
            <InputLabel shrink>Group</InputLabel>
            <Select onChange={event => setGroup(event.target.value)} value={group}>
                {Object.keys(params.activity_times_by_group).map((group, i) =>
                    <MenuItem value={group} key={i}>{group}</MenuItem>)}
            </Select>
        </Grid>
        <Grid item xs={5}>
            <InputLabel shrink>Time</InputLabel>
            <Select onChange={event => setDatetime(event.target.value)} value={datetime}>
                {params.activity_times_by_group[group].map((datetime, i) =>
                    <MenuItem value={datetime} key={i}>{datetime}</MenuItem>)}
            </Select>
        </Grid>
    </ActivityCard>);
}
