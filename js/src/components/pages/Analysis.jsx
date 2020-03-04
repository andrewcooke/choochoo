import React, {useState, useEffect} from 'react';
import {Layout, MainMenu, ColumnList, Loading} from "../elements";
import {Calendar} from "./analysis";
import AllActivities from "./analysis/AllActivities";


function Columns(props) {

    const {params} = props;

    if (params === null) {
        return <Loading/>;  // undefined initial data
    } else {
        console.log(params);
        return (<ColumnList>
            <Calendar/>
            <AllActivities params={params}/>
        </ColumnList>);
    }
}


export default function Analysis(props) {

    const {match} = props;
    const [json, setJson] = useState(null);

    useEffect(() => {
        setJson(null);
        fetch('/api/analysis-parameters')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [1]);

    return (
        <Layout navigation={<MainMenu/>} content={<Columns params={json}/>} match={match} title='Analysis'/>
    );
}
