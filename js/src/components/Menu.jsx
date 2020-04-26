import React, {useState} from 'react';
import {Collapse, List, ListItem, ListItemText} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {ExpandLess, ExpandMore, KeyboardArrowRight} from "@material-ui/icons";
import {ListItemLink, ListItemButton} from "./elements";
import format from 'date-fns/format';
import {FMT_DAY, FMT_MONTH, FMT_YEAR} from "../constants";
import {useLocation, useHistory} from 'react-router-dom';
import DiaryMenu from "./menu/DiaryMenu";


const useStyles = makeStyles(theme => ({
    list: {
        width: '100%',
        maxWidth: 360,
        backgroundColor: theme.palette.background.paper,
    },
    nested: {
        paddingLeft: theme.spacing(4),
    },
}));


function match(pattern) {
    return location => location.match(pattern);
}


export default function Menu(props) {

    const classes = useStyles();
    const location = useLocation().pathname;
    const history = useHistory();

    const isDiary = match(/\/\d+(-\d+(-\d+)?)?/);
    const isDay = match(/\/\d+-\d+-\d+/);
    const isMonth = match(/\/\d+-\d+$/);
    const isYear = match(/\/\d+$/);
    const isKit = match(/\/kit\/.*/);
    const isConfigure = match(/\/configure\/.*/);

    // diary is 0 for closed, 1 for open d/m/y and 2 for dedicated menu
    const [diaryOpen, setDiaryOpen] = useState(isDiary(location) ? 2 : 0);
    const [kitOpen, setKitOpen] = useState(isKit(location));
    const [configureOpen, setConfigureOpen] = useState(isConfigure(location));

    function closeAll() {
        setDiaryOpen(0);
        setKitOpen(false);
        setConfigureOpen(false);
    }

    if (diaryOpen === 2 && isDiary(location)) {
        return <DiaryMenu setDiaryOpen={setDiaryOpen}/>
    } else {
        return (<List component="nav" className={classes.list}>
            <ListItemLink primary='Choochoo' to='/'/>
            <ListItem button onClick={() => {closeAll(); setDiaryOpen(!diaryOpen);}}>
                <ListItemText primary='Diary'/>
                {diaryOpen > 0 ? <ExpandLess/> : <ExpandMore/>}
            </ListItem>
            <Collapse in={diaryOpen} timeout="auto" unmountOnExit>
                <List component="div" disablePadding className={classes.nested}>
                    <ListItemButton primary='Day' onClick={() => {
                        setDiaryOpen(2);
                        if (!isDay(location)) history.push('/' + format(new Date(), FMT_DAY));
                    }} icon={<KeyboardArrowRight/>}/>
                    <ListItemButton primary='Month' onClick={() => {
                        setDiaryOpen(2);
                        if (!isMonth(location)) {
                            if (isDay(location)) {
                                history.push(location.split('-').slice(0, 2).join('-'));
                            } else {
                                history.push('/' + format(new Date(), FMT_MONTH));
                            }
                        }
                    }} icon={<KeyboardArrowRight/>}/>
                    <ListItemButton primary='Year' onClick={() => {
                        setDiaryOpen(2);
                        if (!isYear(location)) {
                            if (isDay(location) || isMonth(location)) {
                                history.push(location.split('-').slice(0, 1).join('-'));
                            } else {
                                history.push('/' + format(new Date(), FMT_Year));
                            }
                        }
                    }} icon={<KeyboardArrowRight/>}/>
                </List>
            </Collapse>
            <ListItemLink primary='Analysis' to='/analysis'/>
            <ListItem button onClick={() => {closeAll(); setKitOpen(!kitOpen);}}>
                <ListItemText primary='Kit'/>
                {kitOpen ? <ExpandLess/> : <ExpandMore/>}
            </ListItem>
            <Collapse in={kitOpen} timeout="auto" unmountOnExit>
                <List component="div" disablePadding className={classes.nested}>
                    <ListItemLink primary='Snapshot' to={'/kit/' + format(new Date(), FMT_DAY)}/>
                    <ListItemLink primary='Edit' to={'/kit/edit'}/>
                    <ListItemLink primary='Statistics' to={'/kit/statistics'}/>
                </List>
            </Collapse>
            <ListItemLink primary='Upload' to='/upload'/>
            <ListItem button onClick={() => {closeAll(); setConfigureOpen(!configureOpen);}}>
                <ListItemText primary='Configure'/>
                {configureOpen ? <ExpandLess/> : <ExpandMore/>}
            </ListItem>
            <Collapse in={configureOpen} timeout="auto" unmountOnExit>
                <List component="div" disablePadding className={classes.nested}>
                    <ListItemLink primary='Initial' to={'/configure/initial'}/>
                    <ListItemLink primary='Upgrade' to={'/configure/upgrade'}/>
                    <ListItemLink primary='Constants' to={'/configure/constants'}/>
                </List>
            </Collapse>
        </List>);
    }
}
