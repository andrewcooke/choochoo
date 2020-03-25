import React, {useEffect, useState} from 'react';
import {ColumnList, Layout, Loading, MainMenu} from "../elements";
import {
    ActivityDetails,
    AllActivities,
    Calendar,
    CompareActivities,
    Health,
    Month,
    NearbyActivities,
    SimilarActivities,
    SomeActivities
} from "./analysis";


function Columns(props) {

    const {params} = props;

    if (params === null) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<ColumnList>
            <ActivityDetails params={params}/>
            <CompareActivities params={params}/>
            <AllActivities params={params}/>
            <SimilarActivities params={params}/>
            <NearbyActivities params={params}/>
            <Month/>
            <Calendar/>
            <Health/>
            <SomeActivities/>
        </ColumnList>);
    }
}


export default function Analysis(props) {

    const {match} = props;
    const [json, setJson] = useState(null);

    useEffect(() => {
        setJson(null);
        fetch('/api/diary/analysis-parameters')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [1]);

    return (
        <Layout navigation={<MainMenu/>} content={<Columns params={json}/>} match={match} title='Analysis'/>
    );
}
