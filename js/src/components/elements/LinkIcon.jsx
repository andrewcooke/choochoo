import React from "react";
import {IconButton, Tooltip} from "@material-ui/core";
import {useHistory} from 'react-router-dom';


export default function LinkIcon(props) {

    const {icon, url, tooltip=null} = props;
    const history = useHistory();

    function onClick() {
        history.push(url)
    }

    const button = (<IconButton color="inherit" onClick={onClick}>{icon}</IconButton>);
    if (tooltip !== null) {
        return (<Tooltip title={tooltip} placement='bottom'>{button}</Tooltip>);
    } else {
        return button;
    }
}
