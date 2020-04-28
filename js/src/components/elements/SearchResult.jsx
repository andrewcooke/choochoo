import React, {useEffect, useState} from 'react';
import Thumbnail from "./Thumbnail";
import ColumnCard from "./ColumnCard";
import {Grid, Typography, Link} from "@material-ui/core";
import FormatValueUnits from "./FormatValueUnits";
import Text from "./Text";
import {format} from 'date-fns'
import {FMT_DAY, FMT_DAY_TIME} from "../../constants";
import {makeStyles} from "@material-ui/styles";
import {useHistory} from 'react-router-dom';


const useStyles = makeStyles(theme => ({
    img: {
        marginBottom: '-10px',
        marginLeft: '2px',
        padding: '1px',
        '&:hover': {
            border: '1px solid white',
            padding: '0px',
        },
    },
}));


export default function SearchResult(props) {

    const {json, sort} = props;
    const history = useHistory();
    const classes = useStyles();

    function onClick() {
        const date = format(json.start.value, FMT_DAY);
        history.push('/' + date);
    }

    return (<ColumnCard>
        <Grid item xs={2}><Link onClick={onClick}><Thumbnail activity_id={json.db} className={classes.img}/></Link></Grid>
        <Grid container item xs={10}>
            <Grid item xs={9}><Link onClick={() => sort('name')}><Text variant='h3'>{json.name.value}</Text></Link></Grid>
            <Grid item xs={3}><Link onClick={() => sort('group')}><Text>{json.group.value}</Text></Link></Grid>
            <Grid item xs={6}><Link onClick={() => sort('start')}><FormatValueUnits {...json.start}/></Link></Grid>
            <Grid item xs={3}><Link onClick={() => sort('distance', true)}><FormatValueUnits {...json.distance}/></Link></Grid>
            <Grid item xs={3}><Link onClick={() => sort('time', true)}><FormatValueUnits {...json.time}/></Link></Grid>
        </Grid>
    </ColumnCard>);
}
