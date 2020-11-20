import React, {useEffect, useState} from 'react';
import {Loading} from "../../common/elements";
import {Map, Route} from ".";


export default function ActivityMap(props) {

    const {json} = props;
    const [data, setData] = useState(null);

    useEffect(() => {
        fetch('/api/route/' + json.db[0] + '/' + encodeURIComponent(json.db[1]))
            .then(response => response.json())
            .then(setData);
    }, [json.db]);

    return (data === null ? <Loading/> : <Map latlon={data['latlon']} routes={activity_routes(data)}/>)
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
