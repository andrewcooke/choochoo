import React from 'react';
import {CircularProgress, Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    center: {
        minHeight: '100vh',
    },
}));


export default function Loading(props) {
    const classes = useStyles();
    return (<Grid container alignItems='center' justify='center' className={classes.center}>
        <CircularProgress/>
    </Grid>);
}
