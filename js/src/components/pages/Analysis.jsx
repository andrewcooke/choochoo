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

    const {params, busyState, reload} = props;

    if (params === null) {
        return <Loading busyState={busyState} reload={reload}/>;  // undefined initial data
    } else {
        return (<ColumnList busyState={busyState} reload={reload}>
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
    const [params, setParams] = useState(null);
    const busyState = useState(null);
    const [error, setError] = useState(null);
    const [reads, setReads] = useState(0);

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        setParams(null);
        fetch('/api/analysis/parameters')
            .then(handleGet(history, setParams, busyState, setError));
    }, [reads]);

    return (
        <Layout navigation={<MainMenu/>}
                content={<Columns params={params} reload={reload} busyState={busyState}/>}
                match={match} title='Analysis'/>
    );
}
