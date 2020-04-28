import React, {useState} from 'react';
import {List} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {KeyboardArrowRight} from "@material-ui/icons";
import {ListItemButton, ListItemLink} from "./elements";
import {format} from 'date-fns';
import {FMT_DAY, FMT_MONTH} from "../constants";
import {useHistory, useLocation} from 'react-router-dom';
import {DiaryMenu, ListItemExpand} from "./menu";


const useStyles = makeStyles(theme => ({
    list: {
        width: '100%',
        maxWidth: 360,
        backgroundColor: theme.palette.background.paper,
    },
}));


function match(pattern) {
    return location => location.match(pattern);
}


export default function Menu(props) {

    const classes = useStyles();
    const location = useLocation().pathname;
    const history = useHistory();

    const isDiary = match(/^\/\d+(-\d+(-\d+)?)?$/);
    const isDay = match(/^\/\d+-\d+-\d+$/);
    const isMonth = match(/^\/\d+-\d+$/);
    const isYear = match(/^\/\d+$/);
    const isKit = match(/^\/kit\/.*$/);
    const isConfigure = match(/\/configure\/.*$/);

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
            <ListItemExpand label='Diary' isExpanded={diaryOpen > 0}
                            onClick={() => {closeAll(); setDiaryOpen(diaryOpen > 0 ? 0 : 1);}}>
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
                            // weird bug - undefined ref for FMT_YEAR
                            history.push('/' + format(new Date(), 'yyyy'));
                            // history.push('/' + format(new Date(), FMT_YEAR));
                        }
                    }
                }} icon={<KeyboardArrowRight/>}/>
            </ListItemExpand>
            <ListItemLink primary='Analysis' to='/analysis'/>
            <ListItemLink primary='Search' to='/search'/>
            <ListItemLink primary='Upload' to='/upload'/>
            <ListItemExpand label='Kit' isExpanded={kitOpen}
                            onClick={() => {closeAll(); setKitOpen(!kitOpen);}}>
                <ListItemLink primary='Snapshot' to={'/kit/' + format(new Date(), FMT_DAY)}/>
                <ListItemLink primary='Edit' to={'/kit/edit'}/>
                <ListItemLink primary='Statistics' to={'/kit/statistics'}/>
            </ListItemExpand>
            <ListItemExpand label='Configure' isExpanded={configureOpen}
                            onClick={() => {closeAll(); setConfigureOpen(!configureOpen);}}>
                <ListItemLink primary='Initial' to={'/configure/initial'}/>
                <ListItemLink primary='Upgrade' to={'/configure/upgrade'}/>
                <ListItemLink primary='Constants' to={'/configure/constants'}/>
            </ListItemExpand>
        </List>);
    }
}
