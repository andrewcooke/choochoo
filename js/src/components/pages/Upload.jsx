import React, {useEffect, useState} from 'react';
import {
    ColumnCard,
    ColumnList,
    ConfirmedWriteButton,
    Layout,
    Loading,
    MainMenu,
    P,
    PercentBar,
    Text
} from "../elements";
import {
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Grid,
    IconButton,
    TextField
} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {Autocomplete} from "@material-ui/lab";
import {Clear} from '@material-ui/icons';
import {handleGet} from "../functions";


const useStyles = makeStyles(theme => ({
    input: {
        display: 'none',
    },
    center: {
        textAlign: 'center',
    },
    right: {
        textAlign: 'right',
    },
    wide: {
        width: '100%',
    },
    noPadding: {
        padding: '0px',
    },
    baseline: {
        alignItems: 'baseline',
    },
}));



function FileList(props) {

    const {files, onClick} = props;
    const classes = useStyles();

    if (files.length === 0) {
        return <></>;
    } else {
        // don't understand why this is still generating the key warning
        return files.map((file, index) => (<>
            <Grid item xs={11} className={classes.baseline} key={`a${index}`}>
                <Text key={`b${index}`}>{file.name}</Text>
            </Grid>
            <Grid item xs={1} className={classes.baseline} key={`c${index}`}>
                <IconButton onClick={() => onClick(index)} className={classes.noPadding} key={`d${index}`}>
                    <Clear key={`e${index}`}/>
                </IconButton>
            </Grid>
        </>));
    }
}


function FileSelect(props) {

    const {items, reload} = props;
    const classes = useStyles();
    const [files, setFiles] = useState([]);
    const [kit, setKit] = useState([]);

    function addFiles() {
        const input = document.getElementById('upload-input');
        let newFiles = [...files];
        const names = files.map(file => file.name);
        for (let i = 0; i < input.files.length; i++) {
            const newFile = input.files.item(i);
            if (! names.includes(newFile.name)) {
                newFiles.push(newFile);
                names.push(newFile.name);
            }
        }
        setFiles(newFiles);
    }

    function deleteFile(index) {
        let newFiles = [...files];
        newFiles.splice(index, 1);
        setFiles(newFiles);
    }

    return (<>
        <Grid item xs={12}>
            <input accept='*/*' id='upload-input' multiple type='file' onChange={addFiles} className={classes.input}/>
            <label htmlFor='upload-input'>
                <Button variant='outlined' component='span'>Select files</Button>
            </label>
        </Grid>
        <FileList files={files} onClick={deleteFile}/>
        <Grid item xs={12}>
            <Autocomplete multiple options={items.map(item => item.name)} filterSelectedOptions
                          className={classes.wide} size='small'
                          renderInput={params => (<TextField {...params} variant='outlined' label='Kit'/>)}
                          onChange={(event, value) => setKit(value)}/>
        </Grid>
        <Grid item xs={12} className={classes.right}>
            <ConfirmedWriteButton disabled={files.length === 0} label='Upload' href='/api/upload'
                                  reload={reload} form={{'files': files, 'kit': kit}}>
                The ingest process will take some time.
            </ConfirmedWriteButton>
        </Grid>
    </>);
}


function Columns(props) {

    const {items, busy, reload} = props;

    if (items === null) {
        return (<>
            <Loading busy={busy}/>
        </>);
    } else {
        return (<>
            <ColumnList busy={busy}>
                <ColumnCard>
                    <FileSelect items={items} reload={reload}/>
                </ColumnCard>
            </ColumnList>
        </>);
    }
}


function BusyDialog(props) {

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


export default function Upload(props) {

    const {match, history} = props;
    const [items, setItems] = useState(null);
    const [busyPercent, setBusyPercent] = useState(null);  // non-null indicates busy is 'active'
    const [busyMessage, setBusyMessage] = useState(null);
    const [reads, setReads] = useState(0);

    function reload() {
        setReads(reads + 1);
    }

    function setBusy(json) {
        console.log('setBusy:');
        console.log(json);
        if (json === undefined) {  // special indication we're done from handleGet
            if (busyPercent !== null && busyPercent < 100) setBusyPercent(100);
        } else {
            setBusyMessage(json.message);
            setBusyPercent(json.percent);
        }
    }

    useEffect(() => {
        setItems(null);
        fetch('/api/kit/items').then(handleGet(history, busyPercent, setItems, setBusy));
    }, [reads]);

    console.log(`Percent ${busyPercent}`);

    const busy = <BusyDialog percent={busyPercent} setPercent={setBusyPercent} message={busyMessage} reload={reload}/>;

    return (
        <Layout navigation={<MainMenu/>}
                content={<Columns items={items} reload={reload} busy={busy}/>}
                match={match} title='Upload'/>
    );
}
