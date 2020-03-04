import React from 'react';
import {Typography} from "@material-ui/core";


export default function Text(props) {
    const {children, secondary=false} = props;
    const colour = secondary ? 'textSecondary' : 'textPrimary';
    return (<Typography variant='body1' color={colour} component='span'>
        {children}
    </Typography>)
}
