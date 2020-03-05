import React from "react";
import {Grid} from "@material-ui/core";
import {LinkButton, Text} from '../../../elements';
import {fmtHref} from "../../../functions";


export default function JupyterAllActivities(props) {
    const {json} = props;
    const all = fmtHref('jupyter/all_activities?start=%s&finish=%s', json.db[0], json.db[1]);

    return (<>
        <Grid item xs={4}><LinkButton href={all}><Text>All Activities</Text></LinkButton></Grid>
    </>);
}
