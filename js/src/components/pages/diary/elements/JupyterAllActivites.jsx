import React from "react";
import {Grid} from "@material-ui/core";
import {LinkButton, Text} from '../../../../common/elements';
import {fmtHref} from "../../../../common/functions";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    center: {
        textAlign: 'center',
    },
}));


export default function JupyterAllActivities(props) {
    const {json} = props;
    const classes = useStyles();
    const all = fmtHref('api/jupyter/all_activities?start=%s&finish=%s', json.db[0], json.db[1]);

    return (<>
        <Grid item xs={4} className={classes.center}><LinkButton href={all}><Text>All Activities</Text></LinkButton></Grid>
    </>);
}
