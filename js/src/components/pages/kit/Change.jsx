import React, {useEffect, useState} from 'react';
import {Break, ColumnCard, ColumnList, Layout, LinkButton, Loading, MainMenu, Text} from "../../elements";
import {
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Grid,
    TextField,
    Typography,
    useMediaQuery, useTheme
} from "@material-ui/core";
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


function ConfirmButton(props) {

    const {children, href, label, xs = 12, disabled = false} = props;
    const classes = useStyles();
    const [open, setOpen] = React.useState(false);
    const theme = useTheme();
    const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));

    function handleClickOpen() {
        setOpen(true);
    }

    function handleClose() {
        setOpen(false);
    }

    function handleCloseOk() {
        handleClose();
        // do something here
    }

    return (
        <Grid item xs={xs} className={classes.right}>
            <Button variant="outlined" onClick={handleClickOpen} disabled={disabled}>{label}</Button>
            <Dialog fullScreen={fullScreen} open={open} onClose={handleClose}>
                <DialogTitle>{'Confirm modification?'}</DialogTitle>
                <DialogContent>
                    <DialogContentText>{children}</DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button autoFocus onClick={handleClose} color="primary">Cancel</Button>
                    <Button onClick={handleCloseOk} color="primary" autoFocus>OK</Button>
                </DialogActions>
            </Dialog>
        </Grid>
    );
}


function ModelShow(props) {

    const {model, component} = props;
    const classes = useStyles();
    const [newModel, setNewModel] = useState(model.name);
    const disabled = newModel === '';

    return (<>
        <Grid item xs={12} className={classes.h3}>
            <Typography variant='h3'>{component.name} / {model.added}</Typography>
        </Grid>
        <Grid item xs={9}>
            <Autocomplete options={component.models.map(model => model.name)} freeSolo value={newModel}
                          onInputChange={(event, value) => setNewModel(value)}
                          renderInput={params => <TextField {...params} label='Model' variant='outlined'/>}/>
        </Grid>
        <ConfirmButton xs={3} label='Replace' disabled={disabled}>
            Adding a new model will replace the current value from today's date.
        </ConfirmButton>
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
                          renderInput={params => <TextField {...params} label='Component' variant='outlined'/>}/>
        </Grid><Break/>
        <Grid item xs={9}>
            <Autocomplete options={models} label='Model' freeSolo value={model}
                          onInputChange={(event, value) => setModel(value)}
                          renderInput={params => <TextField {...params} label='Model' variant='outlined'/>}/>
        </Grid>
        <ConfirmButton xs={3} label='Add' disabled={disabled}>
            Adding a new component and model will extend this item from today's date.
        </ConfirmButton>
    </>);
}


function ItemShow(props) {
    const {item, group, allComponents} = props;
    let model_dbs = item.models.map(model => model.db);
    return (<ColumnCard>
        <Grid item xs={9}>
            <Typography variant='h2'>{item.name} / {group.name} / {item.added}</Typography>
        </Grid>
        <ConfirmButton xs={3} label='Retire'>
            Retiring this item will remove it and all components from today's date.
        </ConfirmButton>
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
