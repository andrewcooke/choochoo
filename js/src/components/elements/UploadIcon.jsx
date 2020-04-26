import React from "react";
import {IconButton, Tooltip} from "@material-ui/core";
import {Publish} from '@material-ui/icons';
import {useHistory} from 'react-router-dom';


export default function UploadIcon(props) {

    const history = useHistory();

    function onClick() {
        history.push('/upload')
    }

    return (<Tooltip title='Upload' placement='top'>
        <IconButton color="inherit" onClick={onClick}>
            <Publish/>
        </IconButton>
    </Tooltip>);
}
