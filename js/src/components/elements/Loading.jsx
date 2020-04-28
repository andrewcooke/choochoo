import React from 'react';
import {CircularProgress, Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    big: {
        minHeight: '100vh',
    },
    small: {
        minHeight: '10vh',
    },
}));


export default function Loading(props) {
    const {small=false} = props;
    const classes = useStyles();
    return (<Grid container alignItems='center' justify='center'
                  className={small ? classes.small : classes.big}>
            <CircularProgress/>
        </Grid>);
}
