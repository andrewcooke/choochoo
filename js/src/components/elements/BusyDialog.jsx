import React, {useState} from "react";
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle} from "@material-ui/core";
import {P, PercentBar} from "./index";


export default function BusyDialog(props) {

    // see handleGet

    const {busyState, reload} = props;
    const [busy, setBusy] = busyState;
    const [open, setOpen] = useState(busy !== null);
    const [okDisabled, setOkDisabled] = useState(busy === null || busy.percent < 100);

    function handleOk() {
        console.log('OK clicked');
        setBusy(null);
        setOpen(false);
        setOkDisabled(true);
    }

    console.log(`Busy current state: open ${open}; OK disabled ${okDisabled}; busy:`);
    console.log(busy);
    // i don't really understand why these lines are needed (but they are)
    if (! open && (busy !== null && busy.percent < 100)) setOpen(true);
    if (okDisabled && busy !== null && busy.percent === 100) setOkDisabled(false);
    if (open && busy.percent !== 100) setTimeout(reload, 1000);

    return (<Dialog open={open}>
        <DialogTitle>Busy</DialogTitle>
        <DialogContent>
            <DialogContentText>
                <P>{busy === null ? '' : busy.message}</P>
                <PercentBar percent={busy === null ? 100 : busy.percent} fraction={1}/>
            </DialogContentText>
        </DialogContent>
        <DialogActions>
            <Button disabled={okDisabled} onClick={handleOk}>OK</Button>
        </DialogActions>
    </Dialog>);
}
