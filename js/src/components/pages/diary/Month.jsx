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
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        setJson(null);
        fetch('/api/diary/' + date)
            .then(handleJson(history, setJson, setError));
    }, [date]);

    return (
        <Layout title={`Diary: ${date}`}
                content={<Schedule json={json} history={history} start={datetime} ymdSelected={1} setError={setError}/>}
                errorState={errorState}/>
    );
}
