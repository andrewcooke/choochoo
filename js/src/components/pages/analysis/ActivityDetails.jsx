import React, {useState} from 'react';
import {Text} from "../../elements";
import {Grid, MenuItem, Select, InputLabel} from "@material-ui/core";
import {FMT_DAY_TIME} from "../../../constants";
import {format, parse} from 'date-fns';
import {DateTimePicker} from "@material-ui/pickers";
import ActivityCard from "./ActivityCard";
import {addDay} from "../../functions";


export default function ActivityDetails(props) {

    const {params} = props;
    const [datetime, setDatetime] = useState(params.latest_activity_time);
    const [group, setGroup] = useState(params.latest_activity_group);
    const href = sprintf('jupyter/activity_details?local_time=%s&activity_group_name=%s', datetime, group);

    return (<ActivityCard header='Activity Details' displayWidth={4} href={href}>
        <Grid item xs={12}><Text>
            <p>Graphical details for the given activity.</p>
        </Text></Grid>
        <Grid item xs={5}>
            <DateTimePicker value={parse(datetime, FMT_DAY_TIME, new Date())}
                            onChange={datetime => setDatetime(format(datetime, FMT_DAY_TIME))}
                            minDate={addDay(params.activities_start)}
                            maxDate={addDay(params.activities_finish)}
                            animateYearScrolling label='Time'/>
        </Grid>
        <Grid item xs={3}>
            <InputLabel shrink>Group</InputLabel>
            <Select onChange={setGroup} value={params.latest_activity_group}>
                {params.activity_groups.map(group => <MenuItem value={group}>{group}</MenuItem>)}
            </Select>
        </Grid>
    </ActivityCard>);
}
