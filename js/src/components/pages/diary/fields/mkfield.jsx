import React, {useState} from 'react';
import {Grid, TextField} from "@material-ui/core";
import {useWriterRx} from "../../../../workers/useWriter";


export default function mkfield(args) {

    const {rx, multiline=false, ...rest} = args;

    return (props) => {
        const {json, writer} = props;
        const [error, setError] = useState();
        const [value, handleChange] = useWriterRx(json, writer, rx, setError);

        let label = json.label;
        if (json.units) label += '/' + json.units

        return (<Grid item {...rest} spacing={0}>
            <TextField label={label} value={value} onChange={handleChange} error={error}
                       fullWidth multiline={multiline} variant="filled"/>
        </Grid>);
    }
}
