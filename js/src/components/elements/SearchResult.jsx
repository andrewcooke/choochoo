import React, {useEffect, useState} from 'react';
import Thumbnail from "./Thumbnail";
import ColumnCard from "./ColumnCard";
import {Grid, Typography} from "@material-ui/core";


export default function SearchResult(props) {
    const {json} = props;
    return (<ColumnCard>
        <Grid item xs={2}><Thumbnail activity_id={json.db}/></Grid>
        <Grid container item xs={10}>
            <Grid item xs={12}><Typography variant='h3'>{json.name}</Typography></Grid>
            <Grid item xs={6}><Typography variant='body1'>{json.start}</Typography></Grid>
            <Grid item xs={3}><Typography variant='body1'>{json.distance}</Typography></Grid>
            <Grid item xs={3}><Typography variant='body1'>{json.time}</Typography></Grid>
        </Grid>
    </ColumnCard>);
}
