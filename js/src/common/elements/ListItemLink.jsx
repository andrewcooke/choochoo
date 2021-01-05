import React from 'react';
import {ListItem, ListItemIcon, ListItemText} from "@material-ui/core";
import {Link} from "react-router-dom";


export default function ListItemLink(props) {

    const {icon=null, primary, to, also, ...rest} = props;

    const renderLink = React.useMemo(
        () => React.forwardRef(
            (itemProps, ref) =>
                <Link to={to} ref={ref} {...itemProps} />),
        [to],
    );

    return (
        <ListItem button component={renderLink} onClick={also}>
            <ListItemText primary={primary} {...rest}/>
            {icon !== null ? <ListItemIcon>{icon}</ListItemIcon> : null}
        </ListItem>
    );
}
