import React from "react";
import {
    Button,
    Dialog, DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Grid,
    useMediaQuery,
    useTheme
} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {handleJson} from "../functions";


const useStyles = makeStyles(theme => ({
    right: {
        textAlign: 'right',
    },
}));


export default function ConfirmedWriteButton(props) {

    const {children, href, json=null, form=null, label, xs=12, reload=null, disabled=false, setError,
           variant='outlined', method='put'} = props;
    const classes = useStyles();
    const [openConfirm, setOpenConfirm] = React.useState(false);
    const [openWait, setOpenWait] = React.useState(false);
    const theme = useTheme();
    const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));

    function appendToForm(form, name, value) {
        if (Array.isArray(value)) {
            value.forEach(subValue => appendToForm(form, name, subValue));
        } else if (value instanceof File) {
            form.append(name, value, value.name);
        } else {
            form.append(name, value);
        }
    }

    function buildData() {
        if (json !== null) {
            const data = JSON.stringify(json);
            console.log(`Sending JSON data ${data}`);
            if (form !== null) console.warn(`Ignoring form data ${form}`);
            return data;
        } else if (form !== null) {
            const data = new FormData();
            Object.keys(form).forEach(key => appendToForm(data, key, form[key]));
            console.log(`Sending form data ${data}`);
            return data;
        } else {
            console.log('Sending empty data');
        }
    }

    function buildRequest() {
        const request = {method: method, body: buildData()};
        if (json !== null) request['headers'] = {'Accept': 'application/json', 'Content-Type': 'application/json'};
        return request;
    }

    function handleClickOpen() {
        setOpenConfirm(true);
    }

    function handleWrite(response) {
        setOpenWait(false);
        handleJson(undefined, reload, undefined, setError)(response);
    }

    function handleCancel() {
        setOpenConfirm(false);
    }

    function handleOk() {
        handleCancel();
        setOpenWait(true);
        fetch(href, buildRequest())
            .then(handleWrite)
            .catch(handleWrite);
    }

    return (
        <Grid item xs={xs} className={classes.right}>
            <Button variant={variant} onClick={handleClickOpen} disabled={disabled}>{label}</Button>
            <Dialog fullScreen={fullScreen} open={openConfirm} onClose={handleCancel}>
                <DialogTitle>{'Confirm?'}</DialogTitle>
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


