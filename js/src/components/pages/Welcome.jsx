import React, {useState} from 'react';
import Layout from "../utils/Layout";
import {ListItemText, List, ListItem, Collapse, Typography} from "@material-ui/core";
import makeStyles from "@material-ui/core/styles/makeStyles";
import {ExpandLess, ExpandMore} from "@material-ui/icons";
import ListItemLink from "../utils/ListItemLink";
import format from 'date-fns/format';


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

    const [open, setOpen] = useState(true);
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
                        <ListItemLink primary='Day' to={'/' + format(new Date(), 'yyyy-MM-dd')}/>
                        <ListItemLink primary='Month' to={'/' + format(new Date(), 'yyyy-MM')}/>
                        <ListItemLink primary='Year' to={'/' + format(new Date(), 'yyyy')}/>
                    </List>
                </Collapse>
                <ListItemLink primary='Analysis' to='/analysis'/>
            </List>
        </>
    );

    const content = (
        <Typography variant='body1'>
            Welcome to Choochoo. More here.
        </Typography>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Welcome'/>
    );
}
