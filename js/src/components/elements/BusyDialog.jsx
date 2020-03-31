import React, {useState} from "react";
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle} from "@material-ui/core";
import {P, PercentBar} from "./index";


export default function BusyDialog(props) {

    // see handleGet

    const {percent, setPercent, message, reload} = props;
    const [open, setOpen] = useState(percent !== null);
    const [okDisabled, setOkDisabled] = useState(percent === null || percent < 100);

    function handleOk() {
        console.log('OK clicked');
        setPercent(null);
        setOpen(false);
        setOkDisabled(true);
    }

    console.log(`Busy current state: open ${open}; percent ${percent}; OK disabled ${okDisabled}`);
    // i don't really understand why this line is needed
    if (! open && (percent !== null && percent < 100)) setOpen(true);
    if (open && percent !== 100) setTimeout(reload, 1000);

    return (<Dialog open={open}>
        <DialogTitle>Busy</DialogTitle>
        <DialogContent>
            <DialogContentText>
                <P>{message}</P>
                <PercentBar percent={percent === null ? 100 : percent} fraction={1}/>
            </DialogContentText>
        </DialogContent>
        <DialogActions>
            <Button disabled={okDisabled} onClick={handleOk}>OK</Button>
        </DialogActions>
    </Dialog>);
}
