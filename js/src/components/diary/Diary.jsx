import React from 'react';
import Button from '@material-ui/core/Button';
import TopBar from './TopBar.jsx'
import {makeStyles} from '@material-ui/core/styles';
import CssBaseline from '@material-ui/core/CssBaseline';
import SideDrawer from "./SideDrawer";


const useStyles = makeStyles(theme => ({
    root: {
        display: 'flex',
    },
    toolbar: theme.mixins.toolbar,
    content: {
        flexGrow: 1,
        padding: theme.spacing(3),
    },
}));


export default function Diary(props) {

    const classes = useStyles();
    const {mobileOpen, handleDrawerToggle, topBar} = TopBar(props);

    return (
        <div className={classes.root}>
            <CssBaseline/>
            {topBar}
            <SideDrawer mobileOpen={mobileOpen} handleDrawerToggle={handleDrawerToggle}/>
            <main className={classes.content}>
                <div className={classes.toolbar}/>
                <Button variant="contained" color="primary">
                    Hello World
                </Button>
            </main>
        </div>
    )
}
