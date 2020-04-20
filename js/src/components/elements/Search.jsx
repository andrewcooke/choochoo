import React, {useEffect, useState} from 'react';
import SearchResult from "./SearchResult";
import {FMT_DAY_TIME} from "../../constants";
import {parse} from 'date-fns';
import Loading from "./Loading";


export default function Search(props) {

    const {query, history} = props;
    const [json, setJson] = useState(null);

    console.log(json);

    function parseDate(row) {
        row.start.value = parse(row.start.value, FMT_DAY_TIME, new Date());
        return row;
    }

    useEffect(() => {
        fetch('/api/search/' + query)
            .then(response => response.json())
            .then(response => response.map(parseDate))
            .then(setJson);
    }, [query]);

    function sort(key, reverse=false) {
        let copy = json.slice();
        copy.sort((a, b) => a[key].units === null ?
            a[key].value.localeCompare(b[key].value) :
            (a[key].value - b[key].value) * (reverse ? -1 : 1));
        setJson(copy);
    }

    return (json === null ? <Loading/> : json.map(row => <SearchResult json={row} sort={sort} history={history}/>))
}
