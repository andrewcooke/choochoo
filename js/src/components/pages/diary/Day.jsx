import React from 'react';
import {Grid, Typography} from "@material-ui/core";
import {EditField, IntegerField, FloatField, ScoreField} from "./fields";


export default function Day(props) {

    const {writer, json} = props;

    if (!Array.isArray(json)) throw 'Expected array';
    const ids = addIds(json);

    // drop outer date label since we already have that in the page
    return (<Grid container direction='column'>
        {json.slice(1).map(row => <Outer writer={writer} json={row}/>)}
    </Grid>);
}


function Outer(props) {

    // start level at 3 because 'Choochoo' is 1
    const {writer, json, level=2} = props;
    const head = json[0], rest = json.slice(1);

    let children = [];
    rest.forEach((row) => {
        if (Array.isArray(row)) {
            children.push(<Outer writer={writer} json={row} level={level + 1}/>);
        } else {
            children.push(<Inner writer={writer} json={row}/>);
        }
    });

    return (<Grid item container spacing={1} key={json.id}>
        <Grid item xs={12} key={head.id}>
            <Typography variant={'h' + level}>{head.value}</Typography>
        </Grid>
        <Grid item xs={1} key={json.id + 'indent'}/>
        <Grid item container xs={11} spacing={2} key={json.id + 'content'}>
            {children}
        </Grid>
    </Grid>);
}


function Inner(props) {

    const {writer, json} = props;

    if (json.type === 'edit') {
        return <EditField key={json.id} writer={writer} json={json}/>
    } else if (json.type === 'integer') {
        return <IntegerField key={json.id} writer={writer} json={json}/>
    } else if (json.type === 'float') {
        return <FloatField key={json.id} writer={writer} json={json}/>
    } else if (json.type === 'score') {
        return <ScoreField key={json.id} writer={writer} json={json}/>
    } else {
        console.log('no support for type: ' + json.type)
        return (<Grid item xs={4}>
            <Typography variant='body1' key={json.id}>{json.label}={json.value}</Typography>
        </Grid>);
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
