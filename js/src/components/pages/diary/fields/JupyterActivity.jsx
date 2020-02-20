import {Grid, Link} from "@material-ui/core";
import JupyterMenu from './JupyterMenu'
import React from "react";


export default function JupyterActivity(props) {
    const {json} = props;
    console.log(json);
    return (<>
        <Grid item xs={4}><Link>Details</Link></Grid>
        <Grid item xs={4}><JupyterMenu json={json[0].slice(1)} label='Compare' template='compare_activities'
                                       params={['local_time', 'compare_time', 'activity_group_name']}/></Grid>
        <Grid item xs={4}><Link>{json[1].value}</Link></Grid>
    </>);
}
