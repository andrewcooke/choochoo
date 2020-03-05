import React from 'react';
import {makeStyles} from "@material-ui/core/styles";
import {Box, Grid, ListItem, Typography} from "@material-ui/core";
import Card from "./Card";


const useStyles = makeStyles(theme => ({
    listItem: {
        padding: theme.spacing(1),
    },
    paper: {
        padding: theme.spacing(1),
        margin: theme.spacing(1),
        width: '100%',
    },
}));


export default function ColumnCard(props) {

    const {header=null, children} = props;
    const classes = useStyles();

    return (<ListItem className={classes.listItem}><Card>
        {header !== null ? <Typography variant='h2'>{header}</Typography> : <></>}
        <Grid container spacing={1}>{children}</Grid>
    </Card></ListItem>);
}
