import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, ConfirmedWriteButton, Layout, Loading, Text} from "../elements";
import {Button, Grid, IconButton, TextField, FormControlLabel, Checkbox, Link} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {Autocomplete} from "@material-ui/lab";
import {Clear} from '@material-ui/icons';
import {handleJson} from "../functions";
import {Link as RouterLink} from "react-router-dom";


const useStyles = makeStyles(theme => ({
    input: {
        display: 'none',
    },
    button: {
        width: '100%',
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


function Help(props) {
    return (<ColumnCard header='Introduction'><Grid item xs={12}>
        <Text>
            <p>SELECT FILES will let you select FIT files to upload.
                If you have <Link component={RouterLink} to='/kit'>kit</Link> defined
                you can select which kit was used in the activities.
                Once you have selected your files, click UPLOAD.
            </p>
            <p>You can also click UPLOAD without selecting any files.
                This will process any new files that are found on disk
                (if you added them manually to the data directory, for example)
                or, if the checkbox is selected, will reprocess all data.</p>
        </Text>
    </Grid></ColumnCard>)
}


function FileList(props) {

    const {files, onClick} = props;
    const classes = useStyles();

    if (files.length === 0) {
        return <></>;
    } else {
        // don't understand why this is still generating the key warning
        return files.map((file, i) => (<>
            <Grid item xs={11} className={classes.baseline} key={i}>
                <Text>{file.name}</Text>
            </Grid>
            <Grid item xs={1} className={classes.baseline} key={i + 0.5}>
                <IconButton onClick={() => onClick(i)} className={classes.noPadding}>
                    <Clear/>
                </IconButton>
            </Grid>
        </>));
    }
}


function FileSelect(props) {

    const {items, reload, setError} = props;
    const classes = useStyles();
    const [files, setFiles] = useState([]);
    const [kit, setKit] = useState([]);
    const [force, setForce] = useState(false);

    function addFiles() {
        const input = document.getElementById('upload-input');
        let newFiles = [...files];
        const names = files.map(file => file.name);
        for (let i = 0; i < input.files.length; i++) {
            const newFile = input.files.item(i);
            if (!names.includes(newFile.name)) {
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

    function onSubmit() {
        setFiles([]);
        reload();
    }

    const empty = files.length === 0 ? (<Grid item xs={12}><Text><p>
        Upload with no files selected will still run the processing pipeline
        (calculating missing or stale statistics).
    </p></Text></Grid>) : null;

    const warning = force ? 'Reprocessing all data will take a long time.' :
        'The ingest process will take some time.';

    return (<ColumnCard>
        <Grid item xs={8}>
            <Autocomplete multiple options={items.map(item => item.name)} filterSelectedOptions
                          className={classes.wide} size='small'
                          renderInput={params => (<TextField {...params} variant='outlined' label='Kit'/>)}
                          onChange={(event, value) => setKit(value)}/>
        </Grid>
        <Grid item xs={4}>
            <input accept='*/*' id='upload-input' multiple type='file' onChange={addFiles} className={classes.input}/>
            <label htmlFor='upload-input'>
                <Button variant='outlined' className={classes.button} component='span'>Select files</Button>
            </label>
        </Grid>
        <FileList files={files} onClick={deleteFile}/>
        {empty}
        <Grid item xs={8}>
            <FormControlLabel
                control={<Checkbox checked={force} onChange={event => setForce(event.target.checked)}/>}
                label='Reprocess all data'/>
        </Grid>
        <ConfirmedWriteButton label='Upload' href='/api/upload' variant='contained'
                              setData={onSubmit} setError={setError}
                              form={{'files': files, 'kit': kit, 'force': force}}>
            {warning}
        </ConfirmedWriteButton>
    </ColumnCard>);
}


function Columns(props) {

    const {items, reload, setError} = props;

    if (items === null) {
        return (<>
            <Loading/>
        </>);
    } else {
        return (<>
            <ColumnList>
                <Help/>
                <FileSelect items={items} reload={reload} setError={setError}/>
            </ColumnList>
        </>);
    }
}


export default function Upload(props) {

    const {history} = props;
    const [items, setItems] = useState(null);
    const busyState = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const [reads, setReads] = useState(0);

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        fetch('/api/kit/items').then(handleJson(history, setItems, setError, busyState));
    }, [reads]);

    return (
        <Layout title='Upload'
                content={<Columns items={items} reload={reload} setError={setError}/>}
                reload={reload} busyState={busyState} errorState={errorState}/>
    );
}
