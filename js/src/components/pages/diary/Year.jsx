import React, {useEffect, useState} from 'react';
import {Layout} from "../../elements";
import {parse} from 'date-fns';
import {csrfFetch, handleJson} from "../../functions";
import {Schedule} from "./elements";
import {FMT_YEAR} from "../../../constants";


export default function Year(props) {

    const {match, history} = props;
    const {date} = match.params;
    const datetime = parse(date, FMT_YEAR, new Date());
    const [json, setJson] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        setJson(null);
        csrfFetch('/api/diary/' + date)
            .then(handleJson(history, setJson, setError));
    }, [date]);

    return (
        <Layout title={`Diary: ${date}`}
                content={<Schedule json={json} history={history} start={datetime} ymdSelected={0} setError={setError}/>}
                errorState={errorState}/>
    );
}
