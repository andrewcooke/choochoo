import React from 'react';
import {Typography} from "@material-ui/core";
import {Layout, MainMenu} from "../utils";


export default function Welcome(props) {

    const {match} = props;

    const navigation = <MainMenu/>;

    const content = (<Typography variant='body1'>
            Welcome to Choochoo. More here.
        </Typography>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Welcome'/>
    );
}
