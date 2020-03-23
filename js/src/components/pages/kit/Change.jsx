import React, {useEffect, useState} from 'react';
import {Break, ColumnCard, ColumnList, Layout, LinkButton, Loading, MainMenu, Text} from "../../elements";
import {Grid, Typography, TextField, Box} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {Autocomplete} from "@material-ui/lab";


const useStyles = makeStyles(theme => ({
    right: {
        textAlign: 'right',
    },
    center: {
        textAlign: 'center',
    },
    left: {
        textAlign: 'left',
    },
    h3: {
        marginTop: theme.spacing(2),
    },
}));


function Button(props) {
    const {href, label, xs=12, disabled=false} = props;
    const classes = useStyles();
    return (<Grid item xs={xs} className={classes.right}>
        <LinkButton href={href} disabled={disabled}>{label}</LinkButton>
    </Grid>);
}


function ModelShow(props) {
    const {model, component} = props;
    const classes = useStyles();
    return (<>
        <Grid item xs={12} className={classes.h3}>
            <Typography variant='h3'>{component.name} / {model.added}</Typography>
        </Grid>
        <Grid item xs={9}>
            <Autocomplete options={component.models.map(model => model.name)} freeSolo
                          defaultValue={model.name}
                          renderInput={params => <TextField {...params} label=''/>}/>
        </Grid>
        <Button xs={3} label='Replace'/>
    </>);
}


function AddComponent(props) {

    const {item, allComponents} = props;
    const [component, setComponent] = useState('');
    const [model, setModel] = useState('');
    const existing = item.components.map(component => component.name);
    const components = Object.keys(allComponents).filter(component => ! existing.includes(component));
    const models = components.includes(component) ? allComponents[component].map(model => model.name) : [];
    const disabled = component === '' || model === '';

    return (<>
        <Grid item xs={12}>
            <Box mt={3}><Text>To add a completely new component and model:</Text></Box>
        </Grid>
        <Grid item xs={9}>
            <Autocomplete options={components} label='Component' freeSolo value={component}
                          onInputChange={(event, value) => setComponent(value)}
                          renderInput={params => <TextField {...params} label=''/>}/>
        </Grid><Break/>
        <Grid item xs={9}>
            <Autocomplete options={models} label='Model' freeSolo value={model}
                          onInputChange={(event, value) => setModel(value)}
                          renderInput={params => <TextField {...params} label=''/>}/>
        </Grid>
        <Button xs={3} label='Add' disabled={disabled}/>
    </>);
}


function ItemShow(props) {
    const {item, group, allComponents} = props;
    let model_dbs = item.models.map(model => model.db);
    return (<ColumnCard>
        <Grid item xs={9}>
            <Typography variant='h2'>{item.name} / {group.name} / {item.added}</Typography>
        </Grid>
        <Button xs={3} label='Retire'/>
        {item.components.map(
            component => component.models.filter(model => model_dbs.includes(model.db)).map(
                model => <ModelShow model={model} component={component} key={model.db}/>)).flat()}
        <AddComponent item={item} allComponents={allComponents}/>
    </ColumnCard>);
}


function Columns(props) {

    const {groups} = props;

    if (groups === null) {
        return <Loading/>;  // undefined initial data
    } else {
        const allComponents = {};
        groups.forEach(group => group.items.forEach(item => item.components.forEach(
            component => allComponents[component.name] = component.models)))
        return (<ColumnList>
            {groups.map(
                group => group.items.map(
                    item => <ItemShow item={item} group={group} key={item.db} allComponents={allComponents}/>)).flat()}
        </ColumnList>);
    }
}


export default function Change(props) {

    const {match} = props;
    const [json, setJson] = useState(null);

    useEffect(() => {
        setJson(null);
        fetch('/api/kit/change')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [1]);

    return (
        <Layout navigation={<MainMenu/>} content={<Columns groups={json}/>} match={match} title='Change Kit'/>
    );
}
