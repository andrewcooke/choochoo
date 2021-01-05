import React, {useEffect, useState} from 'react';
import {Layout} from "../../elements";
import {ColumnList, Loading} from "../../../common/elements";
import {useQuery} from "../../../common/functions";
import {handleJson} from "../../functions";


function StatisticsContent(props) {

    const {data, history} = props;

    return (<ColumnList>
    </ColumnList>);
}


export default function Statistics(props) {

    const {match, history} = props;
    const {name} = match.params;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const query = useQuery();
    const owner = query.get("owner");

    function setJson(json) {
        setData(fixJournals(json));
    }

    useEffect(() => {
        let url = '/api/statistics/by-date/' + name;
        if (owner) url += '?owner=' + owner;
        fetch(url).then(handleJson(history, setData, setError));
    }, [name, owner]);

    const content = data ? <StatisticsContent data={data} history={history}/> : <Loading/>;

    return <Layout title='Statistics' content={content} errorState={errorState}/>;
}
