import React, {useEffect, useState} from 'react';
import {Loading} from "../../common/elements";
import {OSMap, Route} from ".";
import {csrfFetch, handleJson} from "../functions";


export default function ActivityMap(props) {

    const {json} = props;
    const [data, setData] = useState(null);

    useEffect(() => {
        csrfFetch('/api/route/latlon/' + json.db[0] + '/' + encodeURIComponent(json.db[1]))
            .then(handleJson(history, setData));
    }, [json.db]);

    return (data === null || ! data['latlon'] || ! data['latlon'][0] ?
        <Loading/> : <OSMap latlon={data['latlon']} routes={activity_routes(data)}/>)
}


function activity_routes(data) {
    const latlon = data['latlon'];
    const routes = [<Route latlon={latlon} key={-1}/>]
    if ('sectors' in data) {
        return [...routes,
            ...data['sectors'].map((sector, i) =>
                <Route latlon={sector['latlon']}
                       color={sector['type'] === 1 ? 'cyan' : 'black'}
                       main={false} key={i}/>)];
    } else {
        return routes;
    }
}
