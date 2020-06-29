import React, {useState} from 'react';
import {Text} from "../../../common/elements";
import {Grid} from "@material-ui/core";
import {FMT_DAY} from "../../../constants";
import {format, parse} from 'date-fns';
import {DatePicker} from "@material-ui/pickers";
import {ActivityCard} from ".";
import {addDay} from "../../functions";
import {fmtHref, last} from "../../../common/functions";


export default function AllActivities(props) {

    const {params} = props;
    if (Object.keys(params.activity_times_by_group).length === 0) return <Empty/>;

    const all_activity_dates = params.all_activity_times.map(time => time.split(' ')[0]);
    const activities_start = last(all_activity_dates);
    const [start, setStart] = useState(activities_start);
    const [finish, setFinish] = useState(all_activity_dates[0]);
    const href = fmtHref('api/jupyter/all_activities?start=%s&finish=%s', start, finish);

    // the addDay increments below are weird, but work.  bug in picker?  or i just don't understand.
    return (<ActivityCard header='All Activities' pad={2} href={href}>
        <Grid item xs={12}><Text>
            <p>Thumbnail maps for each route between the start and finish dates.</p>
        </Text></Grid>
        <Grid item xs={3}>
            <DatePicker value={parse(start, FMT_DAY, new Date())}
                        onChange={date => setStart(format(date, FMT_DAY))}
                        minDate={addDay(activities_start)} maxDate={finish}
                        animateYearScrolling format={FMT_DAY} label='Start'/>
        </Grid>
        <Grid item xs={3}>
            <DatePicker value={parse(finish, FMT_DAY, new Date())}
                        onChange={date => setFinish(format(date, FMT_DAY))}
                        minDate={addDay(start, 2)} maxDate={addDay(all_activity_dates[0])}
                        animateYearScrolling format={FMT_DAY} label='Finish'/>
        </Grid>
    </ActivityCard>);
}
