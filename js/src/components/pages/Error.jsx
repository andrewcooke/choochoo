import React from 'react';
import {Grid} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, MainMenu, P} from "../elements";


export default function Error(props) {

    const {match} = props;

    const navigation = <MainMenu/>;

    const content = (<ColumnList>
        <ColumnCard><Grid item xs={12}>
            <P>Ooops!</P>
            <P>(try checking the web service logs or the javascript console)</P>
        </Grid></ColumnCard>
    </ColumnList>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Error'/>
    );
}
