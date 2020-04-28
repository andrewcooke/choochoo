import React, {useEffect, useState} from 'react';
import SearchResult from "./SearchResult";
import {FMT_DAY_TIME} from "../../constants";
import {parse} from 'date-fns';
import Loading from "./Loading";


export default function SearchResults(props) {

    const {query, advanced = true} = props;
    const [json, setJson] = useState(null);

    function parseDate(row) {
        row.start.value = parse(row.start.value, FMT_DAY_TIME, new Date());
        return row;
    }

    function sort(key, reverse = false) {
        let copy = json.slice();
        copy.sort((a, b) => a[key].units === null ?
            a[key].value.localeCompare(b[key].value) :
            (a[key].value - b[key].value) * (reverse ? -1 : 1));
        setJson(copy);
    }

    useEffect(() => {
        if (query !== null && query !== '') {
            if (json !== null) setJson(null);
            fetch('/api/search/activity/' + encodeURIComponent(query) + '?advanced=' + advanced)
                .then(response => response.json())
                .then(response => response.map(parseDate))
                .then(setJson);
        }
    }, [query]);

    if (query === null || query === '') {
        return null
    } else if (json === null) {
        return <Loading small/>
    } else {
        return json.map(row => <SearchResult json={row} sort={sort}/>);
    }
}
