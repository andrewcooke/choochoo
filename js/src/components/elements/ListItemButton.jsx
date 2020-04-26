import React from 'react';
import {ListItem, ListItemText, ListItemIcon} from "@material-ui/core";


export default function ListItemButton(props) {

    const {icon=null, onClick, primary, ...rest} = props;

    return (
        <ListItem button onClick={onClick}>
            <ListItemText primary={primary} {...rest}/>
            {icon !== null ? <ListItemIcon>{icon}</ListItemIcon> : null}
        </ListItem>
    );
}
