import React, {useEffect, useState} from 'react';
import SearchResult from "./SearchResult";
import {FMT_DAY_TIME} from "../../constants";
import {parse} from 'date-fns';
import Loading from "./Loading";
import TextCard from "./TextCard";


function SearchError(props) {
    const {error} = props;
    return <TextCard header='Error'>
        <p>{error}</p>
    </TextCard>
}


export default function SearchResults(props) {

    const {query, advanced = true} = props;
    const [json, setJson] = useState(null);

    function fixDate(json) {
        if (json !== null && json.results !== undefined) json.results = json.results.map(parseDate)
        return json;
    }

    function parseDate(row) {
        row.start.value = parse(row.start.value, FMT_DAY_TIME, new Date());
        return row;
    }

    function sort(key, reverse = false) {
        let copy = {results: json.results.slice()};
        copy.results.sort((a, b) => a[key].units === null ?
            a[key].value.localeCompare(b[key].value) :
            (a[key].value - b[key].value) * (reverse ? -1 : 1));
        setJson(copy);
    }

    useEffect(() => {
        if (query !== null && query !== '') {
            if (json !== null) setJson(null);
            fetch('/api/search/activity/' + encodeURIComponent(query) + '?advanced=' + advanced)
                .then(response => response.json())
                .then(fixDate)
                .then(setJson);
        }
    }, [query]);

    if (query === null || query === '') {
        return null
    } else if (json === null) {
        return <Loading small/>
    } else if (json.results !== undefined) {
        if (json.results.length) {
            return json.results.map((row, i) => <SearchResult json={row} sort={sort} key={i}/>);
        } else {
            return <SearchError error='No matches.'/>
        }
    } else {
        return <SearchError error={json.error}/>
    }
}
