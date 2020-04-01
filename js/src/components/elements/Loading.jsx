import React from 'react';
import {CircularProgress, Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import BusyDialog from "./BusyDialog";


const useStyles = makeStyles(theme => ({
    center: {
        minHeight: '100vh',
    },
}));


export default function Loading(props) {
    const {busyState, reload} = props;
    const classes = useStyles();
    return (<>
        <BusyDialog busyState={busyState} reload={reload}/>
        <Grid container alignItems='center' justify='center' className={classes.center}>
            <CircularProgress/>
        </Grid>
    </>);
}
