import React from 'react';
import {Grid, Link} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, MainMenu, P} from "../elements";


export default function Configure(props) {

    const {match} = props;

    const navigation = <MainMenu/>;

    const content = (<ColumnList>
        <ColumnCard><Grid item xs={12}>
            <P>Configure.</P>
        </Grid></ColumnCard>
    </ColumnList>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Configure'/>
    );
}
