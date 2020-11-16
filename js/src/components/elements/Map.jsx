import React, {useEffect, useState} from 'react';
import {MapContainer} from "react-leaflet";
import {Marker, Popup, TileLayer} from "react-leaflet";
import {Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/styles";

const useStyles = makeStyles(theme => ({
    map: {
        height: 300,
    },
    map_container: {
        height: '100%',
    }
}));


export default function Map(props) {

    const classes = useStyles();

    const {json} = props;

    return (
        <Grid item xs={12} className={classes.map}>
            <MapContainer center={[51.505, -0.09]} zoom={13} scrollWheelZoom={false}
                          className={classes.map_container}>
                <TileLayer attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
                           url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
                <Marker position={[51.505, -0.09]}>
                    <Popup>A pretty CSS3 popup. <br /> Easily customizable.</Popup>
                </Marker>
            </MapContainer>
        </Grid>);
}
