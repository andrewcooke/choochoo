import React from 'react';
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    break: {
        flexBasis: '100%',
        height: 0,
    },
}));


export default function Break(props) {

    const classes = useStyles();

    return (<div className={classes.break}/>);
}
