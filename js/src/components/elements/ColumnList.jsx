import React from 'react';
import {makeStyles} from "@material-ui/core/styles";
import {List} from "@material-ui/core";


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
    const {children, reload, ...rest} = props;
    const classes = useStyles();
    return (<List className={classes.list} {...rest}>
        {children}
    </List>)
}
