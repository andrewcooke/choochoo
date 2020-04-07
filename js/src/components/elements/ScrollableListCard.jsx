import React from 'react';
import {Grid, List, ListItem, ListItemText} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import ColumnCard from "./ColumnCard";


const useStyles = makeStyles(theme => ({
    list: {
        maxHeight: '400px',
        overflow: 'auto',
    },
}));


export default function ScrollableListCard(props) {

    const {header, list} = props;
    const classes = useStyles();

    return (<ColumnCard header={header}>
        <Grid item xs={12}><List dense className={classes.list}>
            {list.map(entry => (<ListItem><ListItemText primary={entry}/></ListItem>))}
        </List></Grid>
    </ColumnCard>);
}
