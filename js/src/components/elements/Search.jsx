import React, {useEffect, useState} from 'react';
import SearchResult from "./SearchResult";

export default function Search(props) {
    const {query} = props;
    const [json, setJson] = useState(null);

    console.log(json);

    useEffect(() => {
        fetch('/api/search/' + query)
            .then(response => response.json())
            .then(setJson);
    }, [query]);

    return (json === null ? <p>?</p> : json.map(row => <SearchResult json={row}/>))
}
