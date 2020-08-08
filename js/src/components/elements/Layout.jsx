import React from 'react';
import {makeStyles} from '@material-ui/core/styles';
import {ErrorDialog, Navigation} from "../../common/elements";
import {Menu} from "..";
import {LatestIcon, UploadIcon} from ".";


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

    const {title, content, errorState} = props;

    return (
        <div className={classes.root}>
            <Navigation menu={<Menu/>} title={title} icons={<><UploadIcon/><LatestIcon/></>}/>
            <main className={classes.content}>
                <div className={classes.toolbar}/>
                {errorState !== undefined ?
                    <ErrorDialog errorState={errorState}/> : null}
                {content}
            </main>
        </div>
    )
}
