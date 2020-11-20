import React, {useState} from 'react';
import {Circle, Polyline} from "react-leaflet";
import {last} from '../../common/functions';


export default function Route(props) {

    const {latlon, color='grey', weight=3, main=true} = props;

    const [opacity, setOpacity] = useState(1.0);
    const red = {fillColor: 'red', color: 'red',
        fillOpacity: main ? 1 : 0.5, opacity: main ? 1 : 0.5};
    const green = {fillColor: 'green', color: 'green',
        fillOpacity: main ? 1 : 0.5, opacity: main ? 1 : 0.5};

    return (<>
        <Polyline pathOptions={{color: color, weight: weight, opacity: opacity}} positions={latlon}
                  eventHandlers={{mouseover: e => setOpacity(0.5),
                      mouseout: e => setOpacity(1.0)}}/>
        <Circle center={last(latlon)} radius={main ? 100 : 40} pathOptions={red} key={1}/>
        <Circle center={latlon[0]} radius={main ? 80: 40} pathOptions={green} key={2}/>
    </>);
}
