import React from 'react';
import {Text} from "../../elements";
import {Grid} from "@material-ui/core";
import ActivityCard from "./ActivityCard";


export default function Health(props) {
    return (<ActivityCard header='Health' pad={8} href='api/jupyter/health'>
        <Grid item xs={12}><Text>
            <p>Plots of SHRIMP parameters, rest heart rate, steps, and activity distances and times.</p>
        </Text></Grid>
    </ActivityCard>)
}
