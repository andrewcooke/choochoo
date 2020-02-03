import React from 'react';
import {TreeView, TreeItem} from '@material-ui/lab';
import {Typography} from "@material-ui/core";


export default function fmtDay(json) {
    const ids = addIds(json);
    console.log(json);
    return (<TreeView defaultExpanded={ids}>{fmtList(json)}</TreeView>);
}


function fmtList(json) {
    if (Array.isArray(json)) {
        const head = json[0];
        return <TreeItem key={json.id} nodeId={json.id} label={head.value}>{json.slice(1).map(fmtList)}</TreeItem>;
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
