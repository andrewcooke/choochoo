import React from 'react';
import {Typography, Box} from "@material-ui/core";


export default function P(props) {
    const {children} = props;
    return (<Box mb={1}><Typography variant='body1'>{children}</Typography></Box>);
}
