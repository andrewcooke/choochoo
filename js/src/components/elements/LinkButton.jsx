import React from 'react';
import {Button} from "@material-ui/core";


export default function LinkButton(props) {
    const {href, children, disabled=false} = props;
    function onClick() {
        window.open(href, '_blank')
    }
    return <Button variant='outlined' onClick={onClick} disabled={disabled}>{children}</Button>
}
