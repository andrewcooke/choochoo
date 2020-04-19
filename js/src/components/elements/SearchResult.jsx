import React, {useEffect, useState} from 'react';
import Thumbnail from "./Thumbnail";
import ColumnCard from "./ColumnCard";
import {Grid, Typography, Link} from "@material-ui/core";
import FormatValueUnits from "./FormatValueUnits";
import Text from "./Text";


export default function SearchResult(props) {
    const {json, sort} = props;
    return (<ColumnCard>
        <Grid item xs={2}><Thumbnail activity_id={json.db}/></Grid>
        <Grid container item xs={10}>
            <Grid item xs={9}><Link onClick={() => sort('name')}><Text variant='h3'>{json.name.value}</Text></Link></Grid>
            <Grid item xs={3}><Link onClick={() => sort('group')}><Text variant='h4'>{json.group.value}</Text></Link></Grid>
            <Grid item xs={6}><Link onClick={() => sort('start')}><FormatValueUnits {...json.start}/></Link></Grid>
            <Grid item xs={3}><Link onClick={() => sort('distance', true)}><FormatValueUnits {...json.distance}/></Link></Grid>
            <Grid item xs={3}><Link onClick={() => sort('time', true)}><FormatValueUnits {...json.time}/></Link></Grid>
        </Grid>
    </ColumnCard>);
}
