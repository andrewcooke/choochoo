import React, {useState} from "react";
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle} from "@material-ui/core";
import {P} from ".";
import log from "loglevel";


export default function ErrorDialog(props) {

    // see handleJson

    const {errorState} = props;
    const [error, setError] = errorState;
    const [open, setOpen] = useState(error !== null);

    function handleOk() {
        setError(null);
        setOpen(false);
        window.location.reload();
    }

    log.debug(`Error current state: open ${open}; error:`, error);

    if (! open && error !== null) setOpen(true);

    return (<Dialog open={open}>
        <DialogTitle>Oh Crap</DialogTitle>
        <DialogContent>
            <DialogContentText>
                <P>{error}</P>
            </DialogContentText>
        </DialogContent>
        <DialogActions>
            <Button onClick={handleOk}>OK</Button>
        </DialogActions>
    </Dialog>);
}
