import React from "react";
import {Collapse, List, ListItem, ListItemText} from "@material-ui/core";
import {ExpandLess, ExpandMore} from "@material-ui/icons";
import {makeStyles} from "@material-ui/styles";


const useStyles = makeStyles(theme => ({
    nested: {
        paddingLeft: theme.spacing(4),
    },
}));


export default function ListItemExpand(props) {

    const {label, isExpanded, onClick, children} = props;
    const classes = useStyles();

    return (<>
            <ListItem button onClick={onClick}>
                <ListItemText primary={label}/>
                {isExpanded ? <ExpandLess/> : <ExpandMore/>}
            </ListItem>
            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                <List component="div" disablePadding className={classes.nested}>
                    {children}
                </List>
            </Collapse>
        </>
    );
}
