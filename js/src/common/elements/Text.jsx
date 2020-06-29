import React from 'react';
import {Typography} from "@material-ui/core";


export default function Text(props) {
    const {children, secondary=false, variant='body1', className} = props;
    const colour = secondary ? 'textSecondary' : 'textPrimary';
    return (<Typography variant={variant} color={colour} component='span' className={className}>
        {children}
    </Typography>)
}
