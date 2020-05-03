import React from 'react';
import Thumbnail from "./Thumbnail";
import ColumnCard from "./ColumnCard";
import {Grid, Link, Tooltip} from "@material-ui/core";
import FormatValueUnits from "./FormatValueUnits";
import Text from "./Text";
import {format} from 'date-fns'
import {FMT_DAY} from "../../constants";
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
        <Grid item xs={2}>
            <Tooltip title='Display diary entry' placement='top'>
                <Link onClick={onClick}><Thumbnail activity_id={json.db} className={classes.img}/></Link>
            </Tooltip>
        </Grid>
        <Grid container item xs={10}>
            <Grid item xs={9}>
                <Tooltip title='Sort by name' placement='top'>
                    <Link onClick={() => sort('name')}><Text variant='h3'>{json.name.value}</Text></Link>
                </Tooltip>
            </Grid>
            <Grid item xs={3}>
                <Tooltip title='Sort by group' placement='top'>
                    <Link onClick={() => sort('group')}><Text>{json.group.value}</Text></Link>
                </Tooltip>
            </Grid>
            <Grid item xs={6}>
                <Tooltip title='Sort by date' placement='bottom'>
                    <Link onClick={() => sort('start')}><FormatValueUnits {...json.start}/></Link>
                </Tooltip>
            </Grid>
            <Grid item xs={3}>
                <Tooltip title='Sort by distance' placement='bottom'>
                    <Link onClick={() => sort('distance', true)}><FormatValueUnits {...json.distance}/></Link>
                </Tooltip>
            </Grid>
            <Grid item xs={3}>
                <Tooltip title='Sort by time' placement='bottom'>
                    <Link onClick={() => sort('time', true)}><FormatValueUnits {...json.time}/></Link>
                </Tooltip>
            </Grid>
        </Grid>
    </ColumnCard>);
}
