import React from 'react';
import {TreeView, TreeItem} from '@material-ui/lab';
import {Typography} from "@material-ui/core";
import EditField from "./EditField";


export default function fmtDay(writer, json) {
    const ids = addIds(json);
    console.log(json);
    return (<TreeView defaultExpanded={ids}>{fmtList(writer)(json)}</TreeView>);
}


function fmtList(writer) {

    function fmt(json) {
        if (Array.isArray(json)) {
            const head = json[0];
            return (<TreeItem key={json.id} nodeId={json.id} label={head.value}>{
                json.slice(1).map(fmt)
            }</TreeItem>);
        } else {
            return fmtField(writer, json);
        }
    }

    return fmt;
}


function fmtField(writer, json) {
    if (json.type === 'edit') {
        return <EditField writer={writer} json={json}/>
    } else {
        return (<TreeItem key={json.id} nodeId={json.id} label={
            <Typography>{json.label}={json.value}</Typography>
        }/>);
    }
}


function addIds(json) {

    /* react docs say keys only need to be unique amongst siblings.
       if that's literally true then this is overkill. */

    function add(base) {
        return (json, index) => {
            const id = (base === undefined) ? `${index}` : `${base},${index}`;
            json.id = id;
            if (Array.isArray(json)) json.map(add(id));
        }
    }

    add()(json, 0);

    let ids = [];

    function list(json) {
        ids.push(json.id);
        if (Array.isArray(json)) json.map(list);
    }

    list(json);

    return ids
}
