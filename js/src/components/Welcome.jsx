import React from 'react';
import Layout from "./Layout";
import List from "@material-ui/core/List";
import {ListItemText} from "@material-ui/core";
import makeStyles from "@material-ui/core/styles/makeStyles";
import ListItem from "@material-ui/core/ListItem";
import {ExpandLess, ExpandMore} from "@material-ui/icons";
import Collapse from "@material-ui/core/Collapse";
import ListItemLink from "./ListItemLink";


const useStyles = makeStyles(theme => ({
    root: {
        width: '100%',
        maxWidth: 360,
        backgroundColor: theme.palette.background.paper,
    },
    nested: {
        paddingLeft: theme.spacing(4),
    },
}));


export default function Welcome(props) {

    const {match} = props;

    const classes = useStyles();

    const [open, setOpen] = React.useState(true);
    const handleClick = () => {
        setOpen(!open);
    };

    const navigation = (
        <>
            <List component="nav" className={classes.root}>
                <ListItem button onClick={handleClick}>
                    <ListItemText primary='Diary'/>
                    {open ? <ExpandLess/> : <ExpandMore/>}
                </ListItem>
                <Collapse in={open} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding className={classes.nested}>
                        <ListItemLink primary='Day' to='/2020-01-30'/>
                        <ListItemLink primary='Month' to='/2020-01'/>
                        <ListItemLink primary='Year' to='/2020'/>
                    </List>
                </Collapse>
                <ListItemLink primary='Analysis' to='/analysis'/>
            </List>
        </>
    );

    const content = (
        <p>
            Welcome to Choochoo. More here (replace p with Typography).
        </p>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Welcome'/>
    );
}
