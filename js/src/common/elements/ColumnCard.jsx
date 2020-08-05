import React from 'react';
import {makeStyles} from "@material-ui/core/styles";
import {Grid, ListItem, Typography} from "@material-ui/core";
import {Card} from ".";


const useStyles = makeStyles(theme => ({
    listItem: {
        padding: 0,
        [theme.breakpoints.up('md')]: {
            // get the widest display possible on a phone, single column
            padding: theme.spacing(1),
        },
        // 
        display: 'inline-block',
    },
    align: {
        alignItems: 'flex-end',
    },
}));


export function ColumnCardBase(props) {

    const {header=null, variant, className, children} = props;
    const classes = useStyles();

    return (<ListItem className={classes.listItem}><Card variant={variant} className={className}>
        {header !== null ? header : <></>}
        <Grid container spacing={1} className={classes.align}>{children}</Grid>
    </Card></ListItem>);
}


export default function ColumnCard(props) {
    const {header = null, variant, children, className} = props;
    return (<ColumnCardBase variant={variant} className={className}
        header={header !== null ? <Typography variant='h2'>{header}</Typography> : header}>
        {children}
    </ColumnCardBase>);
}
