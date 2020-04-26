import React, {useState} from "react";
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle} from "@material-ui/core";
import {P} from "./index";


export default function ErrorDialog(props) {

    // see handleJson

    const {errorState} = props;
    const [error, setError] = errorState;
    const [open, setOpen] = useState(error !== null);

    function handleOk() {
        console.log('OK clicked');
        setError(null);
        setOpen(false);
        window.location.reload();
    }

    console.log(`Error current state: open ${open}; error:`);
    console.log(error);

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
