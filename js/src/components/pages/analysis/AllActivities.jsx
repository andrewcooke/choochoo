import React, {useState} from 'react';
import {ColumnCard, LinkButton, Text} from "../../elements";
import {Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {FMT_DAY} from "../../../constants";
import {parse, format} from 'date-fns';
import {DatePicker} from "@material-ui/pickers";


const useStyles = makeStyles(theme => ({
    center: {
        textAlign: 'center',
    },
    left: {
        textAlign: 'left',
    },
    right: {
        textAlign: 'right',
    },
}));


export default function AllActivities(props) {

    const {params} = props;
    const classes = useStyles();
    const [start, setStart] = useState(params.activities_start);
    const [finish, setFinish] = useState(params.activities_finish);
    const href = sprintf('jupyter/all_activities?start=%s&finish=%s', start, finish);

    return (<ColumnCard header='All Activities'>
        <Grid item xs={12}><Text>
            <p>Thumbnail maps for each route between the start and finish dates.</p>
        </Text></Grid>
        <Grid item xs={4}>
            <DatePicker value={parse(start, FMT_DAY, new Date())}
                        onChange={date => setStart(format(date, FMT_DAY))}
                        animateYearScrolling format={FMT_DAY} label='Start'/>
        </Grid>
        <Grid item xs={4}>
            <DatePicker value={parse(finish, FMT_DAY, new Date())}
                        onChange={date => setFinish(format(date, FMT_DAY))}
                        animateYearScrolling format={FMT_DAY} label='Finish'/>
        </Grid>
        <Grid item xs={4} className={classes.right}>
            <LinkButton href={href}>Display</LinkButton>
        </Grid>
    </ColumnCard>);
}
