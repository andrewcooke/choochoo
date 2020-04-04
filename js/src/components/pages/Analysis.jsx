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
import {handleGet} from "../functions";


function Columns(props) {

    const {params} = props;

    if (params === null || params.activities_start === null) {
        return <Loading/>;
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

    const {match, history} = props;
    const [params, setParams] = useState(null);
    const busyState = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const [reads, setReads] = useState(0);

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        setParams(null);
        fetch('/api/analysis/parameters')
            .then(handleGet(history, setParams, setError, busyState));
    }, [reads]);

    return (
        <Layout navigation={<MainMenu/>}
                content={<Columns params={params}/>}
                match={match} title='Analysis' reload={reload}
                busyState={busyState} errorState={errorState}/>
    );
}
