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


function ConfirmedWriteButton(props) {

    const {children, href, data={}, label, xs = 12, update=null, disabled=false} = props;
    const classes = useStyles();
    const [openConfirm, setOpenConfirm] = React.useState(false);
    const [openWait, setOpenWait] = React.useState(false);
    const theme = useTheme();
    const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));

    function handleClickOpen() {
        setOpenConfirm(true);
    }

    function handleWrite() {
        setOpenWait(false);
        if (update !== null) update();
    }

    function handleCancel() {
        setOpenConfirm(false);
    }

    function handleOk() {
        handleCancel();
        setOpenWait(true);
        console.log(data);
        fetch(href,
            {method: 'put',
                  headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
                  body: JSON.stringify(data)})
            .then((response) => {
                console.log(response);
                handleWrite();
            })
            .catch(handleWrite);
    }

    return (
        <Grid item xs={xs} className={classes.right}>
            <Button variant="outlined" onClick={handleClickOpen} disabled={disabled}>{label}</Button>
            <Dialog fullScreen={fullScreen} open={openConfirm} onClose={handleCancel}>
                <DialogTitle>{'Confirm modification?'}</DialogTitle>
                <DialogContent>
                    <DialogContentText>{children}</DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button autoFocus onClick={handleCancel}>Cancel</Button>
                    <Button onClick={handleOk} autoFocus>OK</Button>
                </DialogActions>
            </Dialog>
            <Dialog fullScreen={fullScreen} open={openWait}>
                <DialogTitle>{'Please wait'}</DialogTitle>
                <DialogContent>
                    <DialogContentText>Saving data.</DialogContentText>
                </DialogContent>
            </Dialog>
        </Grid>
    );
}


function ModelShow(props) {

    const {item, model, component, update} = props;
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
        <ConfirmedWriteButton xs={3} label='Replace' disabled={disabled}
                              href='/api/kit/replace-model' update={update}
                              data={{'item': item.db, 'component': component.db, 'model': newModel}}>
            Adding a new model will replace the current value from today's date.
        </ConfirmedWriteButton>
    </>);
}


function AddComponent(props) {

    const {item, update, allComponents} = props;
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
        <ConfirmedWriteButton xs={3} label='Add' disabled={disabled}
                              href='/api/kit/add-component' update={update}
                              data={{'item': item.db, 'component': component, 'model': model}}>
            Adding a new component and model will extend this item from today's date.
        </ConfirmedWriteButton>
    </>);
}


function ItemShow(props) {
    const {item, group, update, allComponents} = props;
    let model_dbs = item.models.map(model => model.db);
    return (<ColumnCard>
        <Grid item xs={9}>
            <Typography variant='h2'>{item.name} / {group.name} / {item.added}</Typography>
        </Grid>
        <ConfirmedWriteButton xs={3} label='Retire'
                              href='/api/kit/retire-item' update={update} data={{'item': item.db}}>
            Retiring this item will remove it and all components from today's date.
        </ConfirmedWriteButton>
        {item.components.map(
            component => component.models.filter(model => model_dbs.includes(model.db)).map(
                model => <ModelShow item={item} model={model} component={component}
                                    update={update} key={model.db}/>)).flat()}
        <AddComponent item={item} update={update} allComponents={allComponents}/>
    </ColumnCard>);
}


function Columns(props) {

    const {groups, update} = props;

    if (groups === null) {
        return <Loading/>;  // undefined initial data
    } else {
        const allComponents = {};
        groups.forEach(group => group.items.forEach(item => item.components.forEach(
            component => allComponents[component.name] = component.models)));
        return (<ColumnList>
            {groups.map(
                group => group.items.map(
                    item => <ItemShow item={item} group={group} update={update} key={item.db}
                                      allComponents={allComponents}/>)).flat()}
        </ColumnList>);
    }
}


export default function Edit(props) {

    const {match} = props;
    const [json, setJson] = useState(null);
    const [edits, setEdits] = useState(0);

    function update() {
        setEdits(edits + 1);
    }

    useEffect(() => {
        setJson(null);
        fetch('/api/kit/edit')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [edits]);

    return (
        <Layout navigation={<MainMenu kit/>}
                content={<Columns groups={json} update={update}/>}
                match={match} title='Edit Kit'/>
    );
}
