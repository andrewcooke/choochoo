import React from 'react';
import {Button} from "@material-ui/core";


export default function LinkButton(props) {
    const {href, children} = props;
    function onClick() {
        window.open(href, '_blank')
    }
    return <Button onClick={onClick}>{children}</Button>
}
