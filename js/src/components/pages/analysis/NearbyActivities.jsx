import React from 'react';
import {Text} from "../../../common/elements";
import {Grid} from "@material-ui/core";
import {ActivityCard} from ".";


export default function NearbyActivities(props) {
    return (<ActivityCard header='Nearby Activities' pad={8} href='api/jupyter/nearby_activities'>
        <Grid item xs={12}><Text>
            <p>A plot of activity routes grouped by similarity.</p>
        </Text></Grid>
    </ActivityCard>)
}
