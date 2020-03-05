import React from 'react';
import {makeStyles} from "@material-ui/core/styles";
import {Box, Paper} from "@material-ui/core";


const useStyles = makeStyles(theme => ({
    paper: {
        padding: theme.spacing(1),
        margin: theme.spacing(1),
        width: '100%',
    },
}));


export default function Card(props) {

    const {children} = props;
    const classes = useStyles();

    return (<Paper className={classes.paper}><Box mb={1}>
        {children}
    </Box></Paper>);
}
