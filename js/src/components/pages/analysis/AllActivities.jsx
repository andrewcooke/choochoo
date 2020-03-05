import React, {useState} from 'react';
import {Text} from "../../elements";
import {Grid} from "@material-ui/core";
import {FMT_DAY} from "../../../constants";
import {format, parse} from 'date-fns';
import {DatePicker} from "@material-ui/pickers";
import ActivityCard from "./ActivityCard";
import {addDay, fmtHref} from "../../functions";


export default function AllActivities(props) {

    const {params} = props;
    const [start, setStart] = useState(params.activities_start);
    const [finish, setFinish] = useState(params.activities_finish);
    const href = fmtHref('jupyter/all_activities?start=%s&finish=%s', start, finish);

    // the addDay increments below are weird, but work.  bug in picker?  or i just don't understand.
    return (<ActivityCard header='All Activities' displayWidth={6} href={href}>
        <Grid item xs={12}><Text>
            <p>Thumbnail maps for each route between the start and finish dates.</p>
        </Text></Grid>
        <Grid item xs={3}>
            <DatePicker value={parse(start, FMT_DAY, new Date())}
                        onChange={date => setStart(format(date, FMT_DAY))}
                        minDate={addDay(params.activities_start)} maxDate={finish}
                        animateYearScrolling format={FMT_DAY} label='Start'/>
        </Grid>
        <Grid item xs={3}>
            <DatePicker value={parse(finish, FMT_DAY, new Date())}
                        onChange={date => setFinish(format(date, FMT_DAY))}
                        minDate={addDay(start, 2)} maxDate={addDay(params.activities_finish)}
                        animateYearScrolling format={FMT_DAY} label='Finish'/>
        </Grid>
    </ActivityCard>);
}
