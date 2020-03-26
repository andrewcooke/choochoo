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


const useStyles = makeStyles(theme => ({
    right: {
        textAlign: 'right',
    },
}));


export default function ConfirmedWriteButton(props) {

    const {children, href, data={}, label, xs=12, reload=null, disabled=false} = props;
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
        if (reload !== null) reload();
    }

    function handleCancel() {
        setOpenConfirm(false);
    }

    function handleOk() {
        handleCancel();
        setOpenWait(true);
        fetch(href,
            {method: 'put',
                headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
                body: JSON.stringify(data)})
            .then(handleWrite)
            .catch(handleWrite);
    }

    return (
        <Grid item xs={xs} className={classes.right}>
            <Button variant="outlined" onClick={handleClickOpen} disabled={disabled}>{label}</Button>
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


