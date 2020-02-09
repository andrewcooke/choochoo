import React from 'react';
import {Box, Container, Typography} from "@material-ui/core";
import EditField from "./EditField";
import IntegerField from "./IntegerField";
import FloatField from "./FloatField";
import Grid from "@material-ui/core/Grid";


export default function Day(props) {

    const {writer, json} = props;

    if (! Array.isArray(json)) throw 'Expected array';
    const ids = addIds(json);

    return <Grid container key='outer'><Outer writer={writer} json={json}/></Grid>;
}


function Outer(props) {

    const {writer, json} = props;
    const head = json[0], rest = json.slice(1);

    let children = [], inners = [];
    rest.forEach((row) => {
        if (Array.isArray(row)) {
            if (inners.length) {
                children.push(<div>{inners}</div>);
                inners = [];
            }
            children.push(<Outer writer={writer} json={row}/>);
        } else {
            inners.push(<Inner writer={writer} json={row}/>);
        }
    });
    if (inners.length) children.push(<form>{inners}</form>);

    return <Grid item container key={json.id}>{children}</Grid>;
}


function Inner(props) {

    const {writer, json} = props;

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
        if (Array.isArray(json)) json.forEach(list);
    }

    list(json);

    return ids
}
