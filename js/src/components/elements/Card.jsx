import React from 'react';
import {makeStyles} from "@material-ui/core/styles";
import {Box, Paper} from "@material-ui/core";


const useStyles = makeStyles(theme => ({
    paper: {
        padding: theme.spacing(1),
        // get the widest display possible on a phone, single column
        marginLeft: 0,
        marginRight: 0,
        marginTop: theme.spacing(1),
        marginBottom: theme.spacing(1),
        [theme.breakpoints.up('md')]: {
            margin: theme.spacing(1),
        },
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
