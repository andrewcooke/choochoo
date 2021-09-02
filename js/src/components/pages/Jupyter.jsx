import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, Loading} from "../../common/elements";
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
} from "./jupyter";
import {csrfFetch, handleJson} from "../functions";
import {Layout} from "../elements";


function Columns(props) {

    const {params} = props;

    if (params === null) {
        return <Loading/>;
    } else if (params.activities_start === null) {
        return (<ColumnList>
            <ColumnCard header='No Data'/>
        </ColumnList>);
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


export default function Jupyter(props) {

    const {history} = props;
    const [params, setParams] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        setParams(null);
        csrfFetch('/api/jupyter/parameters')
            .then(handleJson(history, setParams, setError));
    }, []);

    return (
        <Layout title='Jupyter' content={<Columns params={params}/>} errorState={errorState}/>
    );
}
