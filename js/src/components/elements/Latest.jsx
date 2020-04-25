import React from "react";
import {IconButton, Tooltip} from "@material-ui/core";
import {Event} from '@material-ui/icons';


export default function Latest(props) {

    const {history} = props;

    function updateHistory(date) {
        console.log('latest', date)
        if (date !== null) {
            history.push('/' + date)
        }
    }

    function onClick() {
        fetch('/api/diary/latest').
            then(response => response.json()).
            then(updateHistory);
    }

    return (<Tooltip title='Latest activity' placement='left'>
        <IconButton color="inherit" onClick={onClick}>
            <Event/>
        </IconButton>
    </Tooltip>);
}
