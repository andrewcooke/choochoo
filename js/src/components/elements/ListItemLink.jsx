import React from 'react';
import {ListItem, ListItemIcon, ListItemText} from "@material-ui/core";
import {Link} from "react-router-dom";


export default function ListItemLink(props) {

    const {icon=null, primary, to, ...rest} = props;

    const renderLink = React.useMemo(
        () => React.forwardRef(
            (itemProps, ref) =>
                <Link to={to} ref={ref} {...itemProps} />),
        [to],
    );

    return (
        <li>
            <ListItem button component={renderLink}>
                {icon !== null ? <ListItemIcon>{icon}</ListItemIcon> : null}
                <ListItemText primary={primary} {...rest}/>
            </ListItem>
        </li>
    );
}
