import React from 'react';
import {Link, Typography} from "@material-ui/core";
import {Card, Layout, MainMenu} from "../elements";


export default function Welcome(props) {

    const {match} = props;

    const navigation = <MainMenu/>;

    const content = (<Card><Typography variant='body1'>
        <p>Welcome to Choochoo - an open, hackable and free training diary.</p>
        <p>This is the web interface, which is under active development.  Currently, you can read and modify diary entries and run analysis templates in Jupyter.  To get started select an option from the menu.</p>
        <p>For more information on Choochoo please see the <Link href='https://andrewcooke.github.io/choochoo/'>documentation</Link> or <Link href='https://github.com/andrewcooke/choochoo'>source</Link>.  You can report bugs <Link href='https://github.com/andrewcooke/choochoo/issues'>here</Link>.</p>
    </Typography></Card>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Welcome'/>
    );
}
