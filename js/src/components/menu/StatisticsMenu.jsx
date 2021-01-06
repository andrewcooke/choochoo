import React, {useEffect, useState} from "react";
import {List, ListItem} from "@material-ui/core";
import {ListItemLink, Loading} from "../../common/elements";
import {makeStyles} from "@material-ui/styles";
import ListItemText from "@material-ui/core/ListItemText";
import {KeyboardArrowLeft} from "@material-ui/icons";
import {useHistory} from 'react-router-dom';
import {handleJson} from "../functions";


const useStyles = makeStyles(theme => ({
    root: {
        width: '100%',
        maxWidth: 360,
        backgroundColor: theme.palette.background.paper,
    },
    right: {
        textAlign: 'right',
    },
    nested: {
        paddingLeft: theme.spacing(4),
    },
}));


export default function StatisticsMenu(props) {

    const {setStatisticsOpen} = props;
    const history = useHistory();
    const classes = useStyles();
    const [statistics, setStatistics] = useState([]);

    useEffect(() => {
        fetch('/api/statistics/plottable').then(handleJson(history, setStatistics));
    }, []);

    const makeUrl = statistic => {
        let url = `/statistics/${statistic.name}`
        if (statistic.owner) url = url + `?owner=${statistic.owner}`
        return url;
    }

    const children = statistics ?
        statistics.map(statistic => <ListItemLink primary={statistic.title} to={makeUrl(statistic)}/>) :
        <Loading/>;

    return (<List component="nav" className={classes.root}>
        <ListItemLink primary='Choochoo' to='/'/>
        <ListItem button onClick={() => setStatisticsOpen(0)}>
            <ListItemText>Statistics</ListItemText>
            <KeyboardArrowLeft/>
        </ListItem>
        <List component="div" disablePadding className={classes.nested}>
            {children}
        </List>
    </List>);
}
