import React from 'react';
import {Text} from "../../../common/elements";
import {Grid} from "@material-ui/core";
import {ActivityCard} from ".";


export default function Calendar(props) {
    return (<ActivityCard header='Calendar' pad={8} href='api/jupyter/calendar'>
        <Grid item xs={12}><Text>
            <p>Various representations of all activities, across all dates, showing distance, time, SHRIMP, etc.</p>
        </Text></Grid>
    </ActivityCard>)
}
