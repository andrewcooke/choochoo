import React, {useState} from 'react';
import {Text} from "../../elements";
import {Grid, TextField} from "@material-ui/core";
import ActivityCard from "./ActivityCard";
import {fmtHref} from "../../functions";


export default function SomeActivities(props) {

    const [constraint, setConstraint] = useState('');
    const href = fmtHref('jupyter/some_activities?constraint=%s', constraint);

    return (<ActivityCard header='Some Activities' href={href}>
        <Grid item xs={12}><Text>
            <p>Thumbnail maps of activities that match the query.</p>
            <p>Example queries:</p>
            <p>Active Distance &gt; 50 & Active Distance &lt; 100</p>
            <p>(more here)</p>
        </Text></Grid>
        <Grid item xs={12}>
            <TextField label='Constraint' value={constraint}
                       onChange={event => setConstraint(event.target.value)}
                       fullWidth multiline/>
        </Grid>
    </ActivityCard>)
}
