import React from 'react';
import Button from '@material-ui/core/Button';
import TopBar from './TopBar.jsx'
import {makeStyles} from '@material-ui/core/styles';
import CssBaseline from '@material-ui/core/CssBaseline';
import {ThemeProvider} from "@material-ui/styles";
import {theme} from "../../theme";


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

    return (
        <div className={classes.root}>
            <ThemeProvider theme={theme}>
                <CssBaseline/>
                <TopBar/>
                <main className={classes.content}>
                    <div className={classes.toolbar}/>
                    <Button variant="contained" color="primary">
                        Hello World
                    </Button>
                </main>
            </ThemeProvider>
        </div>
    )
}
