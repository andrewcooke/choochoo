import React, {useState} from 'react';
import {Grid, TextField} from "@material-ui/core";
import {useWriterRx} from "../../../workers/useWriter";


export function mkfield(rx) {
    return (props) => {
        const {json, writer} = props;
        const [error, setError] = useState();
        const [value, handleChange] = useWriterRx(json, writer, rx, setError);

        return (<Grid item xs={4} md={2}>
            <TextField label={props.json.label} value={value} onChange={handleChange} error={error}
                       variant="filled"/>
        </Grid>);
    }
}
