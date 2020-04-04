import React, {useState} from 'react';
import {Collapse, List, ListItem, ListItemText} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {ExpandLess, ExpandMore} from "@material-ui/icons";
import ListItemLink from ".//ListItemLink";
import format from 'date-fns/format';
import {FMT_DAY, FMT_MONTH, FMT_YEAR} from "../../constants";


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


export default function MainMenu(props) {

    const {kit=false, configure=false} = props;
    const classes = useStyles();

    const [openDiary, setOpenDiary] = useState(false);
    const handleDiaryClick = () => {
        setOpenDiary(!openDiary);
    };

    const [openKit, setOpenKit] = useState(kit);
    const handleKitClick = () => {
        setOpenKit(!openKit);
    };

    const [openConfigure, setOpenConfigure] = useState(configure);
    const handleConfigureClick = () => {
        setOpenConfigure(!openConfigure);
    };

    return (<List component="nav" className={classes.root}>
        <ListItem button onClick={handleDiaryClick}>
            <ListItemText primary='Diary'/>
            {openDiary ? <ExpandLess/> : <ExpandMore/>}
        </ListItem>
        <Collapse in={openDiary} timeout="auto" unmountOnExit>
            <List component="div" disablePadding className={classes.nested}>
                <ListItemLink primary='Day' to={'/' + format(new Date(), FMT_DAY)}/>
                <ListItemLink primary='Month' to={'/' + format(new Date(), FMT_MONTH)}/>
                <ListItemLink primary='Year' to={'/' + format(new Date(), FMT_YEAR)}/>
            </List>
        </Collapse>
        <ListItemLink primary='Analysis' to='/analysis'/>
        <ListItem button onClick={handleKitClick}>
            <ListItemText primary='Kit'/>
            {openKit ? <ExpandLess/> : <ExpandMore/>}
        </ListItem>
        <Collapse in={openKit} timeout="auto" unmountOnExit>
            <List component="div" disablePadding className={classes.nested}>
                <ListItemLink primary='Snapshot' to={'/kit/' + format(new Date(), FMT_DAY)}/>
                <ListItemLink primary='Edit' to={'/kit/edit'}/>
                <ListItemLink primary='Statistics' to={'/kit/statistics'}/>
            </List>
        </Collapse>
        <ListItemLink primary='Upload' to='/upload'/>
        <ListItem button onClick={handleConfigureClick}>
            <ListItemText primary='Configure'/>
            {openConfigure ? <ExpandLess/> : <ExpandMore/>}
        </ListItem>
        <Collapse in={openConfigure} timeout="auto" unmountOnExit>
            <List component="div" disablePadding className={classes.nested}>
                <ListItemLink primary='Initial' to={'/configure/initial'}/>
            </List>
        </Collapse>
    </List>);
}
