import React, {useEffect, useState} from 'react';
import {Layout} from "../../elements";
import {parse} from 'date-fns';
import {handleJson} from "../../functions";
import {Schedule} from "./elements";
import {FMT_MONTH} from "../../../constants";


export default function Month(props) {

    const {match, history} = props;
    const {date} = match.params;
    const datetime = parse(date, FMT_MONTH, new Date());
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
                content={<Schedule json={json} history={history} start={datetime} ymdSelected={1}/>}
                reload={reload} busyState={busyState} errorState={errorState}/>
    );
}
