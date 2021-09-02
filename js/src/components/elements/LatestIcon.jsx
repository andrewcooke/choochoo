import React from "react";
import {IconButton, Tooltip} from "@material-ui/core";
import {Event} from '@material-ui/icons';
import {useHistory} from 'react-router-dom';
import {csrfFetch} from "../functions";


export default function LatestIcon(props) {

    const history = useHistory();

    function updateHistory(date) {
        if (date !== null) {
            history.push('/' + date)
        }
    }

    function onClick() {
        csrfFetch('/api/diary/latest')
            .then(response => response.json())
            .then(updateHistory);
    }

    return (<Tooltip title='Latest activity' placement='bottom'>
        <IconButton color="inherit" onClick={onClick}>
            <Event/>
        </IconButton>
    </Tooltip>);
}
