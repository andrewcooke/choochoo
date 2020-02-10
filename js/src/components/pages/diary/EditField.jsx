import React from 'react';
import TextField from "@material-ui/core/TextField";
import {useWriter} from "../../../workers/useWriter";
import Grid from "@material-ui/core/Grid";


export default function EditField(props) {

    const {json, writer} = props;
    const [value, handleChange] = useWriter(json, writer);

    return (<Grid item xs={12} m={6}>
        <TextField label={props.json.label} value={value} onChange={handleChange}
                   multiline fullWidth variant="filled"/>
    </Grid>);
}
