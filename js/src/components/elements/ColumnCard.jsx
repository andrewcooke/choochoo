import React from 'react';
import {makeStyles} from "@material-ui/core/styles";
import {Box, Grid, ListItem, Paper, Typography} from "@material-ui/core";


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

    const {header, children} = props;
    const classes = useStyles();

    return (<ListItem className={classes.listItem}>
        <Paper className={classes.paper}>
            <Box mb={1}><Typography variant='h2'>{header}</Typography></Box>
            <Grid container spacing={1}>{children}</Grid>
        </Paper>
    </ListItem>);
}
