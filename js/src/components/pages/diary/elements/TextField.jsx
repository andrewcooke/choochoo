import React from 'react';
import {Typography, Grid} from "@material-ui/core";


export default function TextField(props) {

    const {json} = props;

    return (<Grid item xs={12}>
        <Typography variant='body1'>{json.value}</Typography>
    </Grid>)
}