import React from 'react';
import {TreeView, TreeItem} from '@material-ui/lab';


export default function fmtDay(json) {
    const ids = addIds(json);
    return (<TreeView defaultExpanded={ids}>{fmtList(json)}</TreeView>);
}


function fmtList(json) {
    if (Array.isArray(json)) {
        const head = json[0];
        return <TreeItem key={json.id} nodeId={json.id} label={head.value}>{json.slice(1).map(fmtList)}</TreeItem>;
    } else {
        return <p key={json.id}>{json.label}={json.value}</p>;
    }
}


function addIds(json) {

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
