import React from 'react';
import {makeStyles} from "@material-ui/core/styles";
import {List} from "@material-ui/core";
import BusyDialog from "./BusyDialog";


const useStyles = makeStyles(theme => ({
    list: {
        [theme.breakpoints.up('md')]: {
            columnCount: 2,
        },
        [theme.breakpoints.up('xl')]: {
            columnCount: 3,
        },
        padding: 0,
        columnGap: 0,
    },
}));


export default function ColumnList(props) {
    const {children, busyState, reload, ...rest} = props;
    const classes = useStyles();
    return (<List className={classes.list} {...rest}>
        {busyState !== undefined && reload !== undefined ? <BusyDialog busyState={busyState} reload={reload}/> : null}
        {children}
    </List>)
}
