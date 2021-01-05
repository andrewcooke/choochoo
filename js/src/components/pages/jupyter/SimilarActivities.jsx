import React, {useState} from 'react';
import {Text, Empty} from "../../../common/elements";
import {Grid, InputLabel, MenuItem, Select} from "@material-ui/core";
import {ActivityCard} from ".";
import {fmtHref} from "../../../common/functions";


export default function SimilarActivities(props) {

    const {params} = props;
    if (params.all_activity_times.length === 0) return <Empty/>;

    const [datetime, setDatetime] = useState(params.all_activity_times[0]);
    const href = fmtHref('api/jupyter/similar_activities?local_time=%s', datetime);

    return (<ActivityCard header='Similar Activities' pad={3} href={href}>
        <Grid item xs={12}><Text>
            <p>Thumbnail maps of nearby activities.</p>
        </Text></Grid>
        <Grid item xs={5}>
            <InputLabel shrink>Time</InputLabel>
            <Select onChange={event => setDatetime(event.target.value)} value={datetime}>
                {params.all_activity_times.map((datetime, i) =>
                    <MenuItem value={datetime} key={i}>{datetime}</MenuItem>)}
            </Select>
        </Grid>
    </ActivityCard>);
}
