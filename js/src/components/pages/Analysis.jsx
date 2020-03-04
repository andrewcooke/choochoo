import React from 'react';
import {Layout, MainMenu, ColumnList} from "../elements";
import {Calendar} from "./analysis";


function Columns(props) {
    return (<ColumnList>
        <Calendar/>
    </ColumnList>);
}


export default function Analysis(props) {
    const {match} = props;
    const navigation = <MainMenu/>;
    const content = <Columns/>;
    return (
        <Layout navigation={navigation} content={content} match={match} title='Analysis'/>
    );
}
