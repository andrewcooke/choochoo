import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, Layout, LinkButton, Loading, MainMenu, Text} from "../../elements";
import {Grid, Typography} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";


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
    const {href, label, xs=12} = props;
    const classes = useStyles();
    return (<Grid item xs={xs} className={classes.right}>
        <LinkButton href={href}>{label}</LinkButton>
    </Grid>);
}


function Added(props) {
    const {added} = props;
    return (<>
        <Grid item xs={2}><Text>Added</Text></Grid>
        <Grid item xs={2}><Text>{added}</Text></Grid>
    </>);
}


function ModelShow(props) {
    const {model, component} = props;
    const classes = useStyles();
    return (<>
        <Grid item xs={12} className={classes.h3}>
            <Typography variant='h3'>{model.name} / {component.name}</Typography>
        </Grid>
        <Added added={model.added}/>
        <Grid xs={5}>Autocomplete</Grid>
        <Button xs={3} label='Replace'/>
    </>);
}


function ItemShow(props) {
    const {item, group} = props;
    return (<ColumnCard header={`${item.name} / ${group.name}`}>
        <Added added={item.added}/>
        <Button xs={8} label='Retire'/>
        {item.components.map(
            component => component.models.map(
                model => <ModelShow model={model} component={component} key={model.db}/>)).flat()}
    </ColumnCard>);
}


function Columns(props) {

    const {groups} = props;

    if (groups === null) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<ColumnList>
            {groups.map(
                group => group.items.map(
                    item => <ItemShow item={item} group={group} key={item.db}/>)).flat()}
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
