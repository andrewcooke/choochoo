import React from 'react';
import {TreeView, TreeItem} from '@material-ui/lab';
import {Box, Container, Typography} from "@material-ui/core";
import EditField from "./EditField";
import IntegerField from "./IntegerField";
import FloatField from "./FloatField";


export default function fmtDay(writer, json) {
    const ids = addIds(json);
    console.log(json);
    return (<TreeView defaultExpanded={ids}>{fmtJson(writer)(json)}</TreeView>);
}


function fmtJson(writer) {

    function fmtList(json) {
        if (! Array.isArray(json)) throw 'Expected array';
        const head = json[0], rest = json.slice(1);
        let dom = [], fields = [];
        rest.forEach((row) => {
            if (Array.isArray(row)) {
                if (fields.length) {
                    dom.push(<div>{fields}</div>);
                    fields = [];
                }
                dom.push(fmtList(row));
            } else {
                fields.push(fmtField(writer, row));
            }
        });
        if (fields.length) dom.push(<form>{fields}</form>);
        return <TreeItem key={json.id} nodeId={json.id} label={head.value}>{dom}</TreeItem>;
    }

    return fmtList;
}


function fmtField(writer, json) {
    if (json.type === 'edit') {
        return <EditField key={json.id} writer={writer} json={json}/>
    } else if (json.type === 'integer') {
        return <IntegerField key={json.id} writer={writer} json={json}/>
    } else if (json.type === 'float') {
        return <FloatField key={json.id} writer={writer} json={json}/>
    } else {
        return <Typography key={json.id}>{json.label}={json.value}</Typography>;
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
