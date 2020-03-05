import React from "react";
import {Grid} from "@material-ui/core";
import {LinkButton, Text} from '../../../elements';
import JupyterMenu from './JupyterMenu'
import {sprintf} from "sprintf-js";
import {fmtHref} from "../../../functions";


export default function JupyterActivity(props) {

    const {json} = props;
    const [, head, ...rest] = json[0];

    const details = fmtHref('jupyter/activity_details?local_time=%s&activity_group_name=%s',
                            head.db[0], head.db[1]);
    const similar = fmtHref('jupyter/similar_activities?local_time=%s&activity_group_name=%s',
                            json[1].db[0], json[1].db[1]);

    return (<>
        <Grid item xs={4}><LinkButton href={details}><Text>Details</Text></LinkButton></Grid>
        <JupyterMenu json={rest} label='Compare' template='compare_activities'
                     params={['local_time', 'compare_time', 'activity_group_name']}/>
        <Grid item xs={4}><LinkButton href={similar}><Text>{json[1].value}</Text></LinkButton></Grid>
    </>);
}
