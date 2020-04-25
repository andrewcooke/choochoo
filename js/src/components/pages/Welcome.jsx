import React from 'react';
import {Grid, Link} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, MainMenu, P} from "../elements";


export default function Welcome(props) {

    const {match} = props;

    const navigation = <MainMenu/>;

    const content = (<ColumnList>
        <ColumnCard><Grid item xs={12}>
            <P>Welcome to Choochoo - an open, hackable and free training diary.</P>
            <P>This is the web interface, which is under active development.
                To get started select an option from the menu.</P>
            <P>For more information on Choochoo please see the <Link
                href='https://andrewcooke.github.io/choochoo/'>documentation</Link> or <Link
                href='https://github.com/andrewcooke/choochoo'>source</Link>. You can report bugs <Link
                href='https://github.com/andrewcooke/choochoo/issues'>here</Link>.</P>
        </Grid></ColumnCard>
    </ColumnList>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Welcome' history={history}/>
    );
}
