import React from 'react';
import {Link, Typography, Grid} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, MainMenu} from "../elements";


export default function Error(props) {

    const {match} = props;

    const navigation = <MainMenu/>;

    const content = (<ColumnList>
        <ColumnCard><Grid item xs={12}><Typography variant='body1'>
            Ooops!<br/>
            (try checking the web service logs or the javascript console)
        </Typography></Grid></ColumnCard>
    </ColumnList>);

    return (
        <Layout navigation={navigation} content={content} match={match} title='Error'/>
    );
}
