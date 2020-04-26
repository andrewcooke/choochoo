import React, {useEffect, useState} from 'react';
import {Layout} from "../elements";
import {parse} from 'date-fns';
import {Day, Schedule} from './diary';
import {FMT_DAY, FMT_MONTH, FMT_YEAR} from "../../constants";
import {handleJson} from "../functions";


function classifyDate(date) {
    const ymdSelected = (date.match(/-/g) || []).length;
    switch (ymdSelected) {
        case 0:
            return {ymdSelected, dateFmt: FMT_YEAR, component: Schedule};
        case 1:
            return {ymdSelected, dateFmt: FMT_MONTH, component: Schedule};
        case 2:
            return {ymdSelected, dateFmt: FMT_DAY, component: Day};
        default:
            throw 'Bad date ' + date;
    }
}


export default function Diary(props) {

    const {match, history, writer} = props;
    const {date} = match.params;
    const {ymdSelected, dateFmt, component} = classifyDate(date);
    const datetime = parse(date, dateFmt, new Date());
    const [json, setJson] = useState(null);
    const busyState = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const [reads, setReads] = useState(0);

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        setJson(null);
        fetch('/api/diary/' + date)
            .then(handleJson(history, setJson, setError, busyState));
    }, [`${date} ${reads}`]);

    return (
        <Layout title={`Diary: ${date}`}
                content={component({json, writer, history, datetime, ymdSelected})}
                reload={reload} busyState={busyState} errorState={errorState}/>
    );
}
