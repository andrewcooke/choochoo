import React, {useEffect, useState} from 'react';
import {ConfirmedWriteButton, Layout, Map, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {handleJson} from "../../functions";
import {Grid, Slider, TextField} from "@material-ui/core";
import log from "loglevel";
import {makeStyles} from "@material-ui/styles";


const useStyles = makeStyles(theme => ({
    button: {
        width: '100%',
    },
}));


function SectorContent(props) {

    // todo - what if 0 or 1 sectors matched?
    const {sector, data, history} = props;
    const [sectors, setSectors] = useState(data['sectors']);
    const [showDistance, setShowDistance] = useState(true);
    const [i, setI] = useState(0);
    const [j, setJ] = useState(1);

    // todo - return map, plot and sorted list of sectors
    // see search result handling in Month
}


export default function Sector(props) {

    const {match, history} = props;
    const {id} = match.params;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/sector/' + id)
            .then(handleJson(history, setData, setError));
    }, [id]);

    log.debug(`id ${id}`)

    const content = data === null ? <Loading/> :
        <SectorContent sector={id} data={data} history={history}/>;

    return <Layout title='Sector Analysis' content={content} errorState={errorState}/>;
}
