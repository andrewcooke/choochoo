import React from 'react';
import {makeStyles} from '@material-ui/core/styles';
import Navigation from "./Navigation";
import BusyDialog from "./BusyDialog";
import ErrorDialog from "./ErrorDialog";


const useStyles = makeStyles(theme => ({
    root: {
        display: 'flex',
    },
    toolbar: theme.mixins.toolbar,
    content: {
        flexGrow: 1,
        padding: theme.spacing(1),  // paper has margin 1 so together we get 2 around all edges
    },
}));


export default function Layout(props) {

    const classes = useStyles();

    const {navigation, content, match, title, busyState, reload, errorState} = props;

    return (
        <div className={classes.root}>
            <Navigation content={navigation} match={match} title={title}/>
            <main className={classes.content}>
                <div className={classes.toolbar}/>
                {busyState !== undefined && reload !== undefined ?
                    <BusyDialog busyState={busyState} reload={reload}/> : null}
                {errorState !== undefined ?
                    <ErrorDialog errorState={errorState}/> : null}
                {content}
            </main>
        </div>
    )
}
