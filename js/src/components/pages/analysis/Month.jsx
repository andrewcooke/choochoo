import React, {useState} from 'react';
import {Text} from "../../elements";
import {Grid} from "@material-ui/core";
import ActivityCard from "./ActivityCard";
import {FMT_MONTH} from "../../../constants";
import {DatePicker} from "@material-ui/pickers";
import {format} from 'date-fns';


export default function Month(props) {

    const [month, setMonth] = useState(format(new Date(), FMT_MONTH));
    const href = sprintf('jupyter/month?month=%s', month);

    return (<ActivityCard header='Month' displayWidth={9} href={href}>
        <Grid item xs={12}><Text>
            <p>Thumbnail maps for each route in the given month.</p>
        </Text></Grid>
        <Grid item xs={3}>
            <DatePicker value={month} views={["year", "month"]} label='Month'
                        onChange={date => setMonth(format(date, FMT_MONTH))}/>
        </Grid>
    </ActivityCard>);
}
