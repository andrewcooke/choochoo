import React from 'react';
import TreeItem from "@material-ui/lab/TreeItem";
import TextField from "@material-ui/core/TextField";
import useWriter from "../../../workers/useWriter";


export default function IntegerField(props) {

    const {json, writer} = props;
    const [value, handleChange] = useWriter(json, writer);

    return <TreeItem key={props.json.id} nodeId={props.json.id} label={
        <TextField label={props.json.label} value={value} onChange={handleChange}
                   variant="filled"/>
    }/>;
}
