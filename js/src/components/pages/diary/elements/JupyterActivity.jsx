import React from "react";
import {Grid} from "@material-ui/core";
import {LinkButton, Text} from '../../../elements';
import JupyterMenu from './JupyterMenu'
import {sprintf} from "sprintf-js";
import {fmtHref} from "../../../functions";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    center: {
        textAlign: 'center',
    },
    inverse: {
        color: theme.palette.background.paper,
    },
}));


export default function JupyterActivity(props) {

    console.log('JA', props);

    const {json} = props;
    const [, head, ...rest] = json[0];
    const classes = useStyles();

    console.log('head', head);
    console.log('rest', rest);

    const details = fmtHref('api/jupyter/activity_details?local_time=%s&activity_group=%s',
                            head.db[0], head.db[2]);
    const similar = fmtHref('api/jupyter/similar_activities?local_time=%s&activity_group=%s',
                            json[1].db[0], json[1].db[1]);

    return (<>
        <Grid item xs={4} className={classes.center}>
            <LinkButton href={details} variant='contained'>
                <Text className={classes.inverse}>Details</Text>
            </LinkButton>
        </Grid>
        <JupyterMenu json={rest} label='Compare' template='compare_activities'
                     params={['local_time', 'compare_time', 'activity_group']}/>
        <Grid item xs={4} className={classes.center}>
            <LinkButton href={similar}><Text>{json[1].value}</Text></LinkButton>
        </Grid>
    </>);
}
