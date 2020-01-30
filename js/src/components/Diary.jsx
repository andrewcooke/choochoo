import React from 'react';
import Layout from "./Layout";
import makeStyles from "@material-ui/core/styles/makeStyles";


const useStyles = makeStyles(theme => ({
    root: {
        display: 'flex',
    },
    toolbar: theme.mixins.toolbar,
    content: {
        flexGrow: 1,
        padding: theme.spacing(3),
    },
    nested: {
        paddingLeft: theme.spacing(4),
    },
}));


export default function Diary(props) {

    const {match} = props;

    const classes = useStyles();

    const navigation = (
        <>
            todo
        </>
    );

    const content = (
        <p>
            Diary here.
        </p>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Diary'/>
    );
}
