import React from 'react';
import {MapContainer, TileLayer} from "react-leaflet";
import {Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/styles";
import {last} from '../../common/functions';


const useStyles = makeStyles(theme => ({
    map: {
        height: 300,
    },
    map_container: {
        height: '100%',
    }
}));


export default function OSMap(props) {

    const classes = useStyles();

    const {latlon, routes} = props;

    const lats = latlon.map(latlon => latlon[0]).sort();
    const lons = latlon.map(latlon => latlon[1]).sort();
    const bounds = [[lats[0], last(lons)], [last(lats), lons[0]]];

    return (
        <Grid item xs={12} className={classes.map}>
            <MapContainer bounds={bounds} scrollWheelZoom={false}
                          className={classes.map_container}>
                <TileLayer attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
                           url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
                {routes}
            </MapContainer>
        </Grid>);
}
