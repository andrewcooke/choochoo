import React from 'react';
import Button from '@material-ui/core/Button';
import Layout from "../Layout";
import List from "@material-ui/core/List";


export default function Welcome(props) {

    const {match} = props

    const navigation = (
        <>
            <List component="nav">
                poop
            </List>
        </>
    );

    const content = (
        <Button variant="contained" color="primary">
            Welcome
        </Button>);

    return (
      <Layout navigation={navigation} content={content} match={match} title='Welcome'/>
    );
}
