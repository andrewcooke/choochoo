import React from 'react';
import {Text} from "../../elements";
import {Grid} from "@material-ui/core";
import ActivityCard from "./ActivityCard";


export default function Calendar(props) {
    return (<ActivityCard header='Calendar' href='jupyter/calendar'>
        <Grid item xs={12}><Text>
            <p>Various representations of all activities, across all dates, showing distance, time, SHRIMP, etc.</p>
        </Text></Grid>
    </ActivityCard>)
}
