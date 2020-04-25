import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, ConfirmedWriteButton, Layout, Loading, MainMenu, Text} from "../elements";
import {Button, Grid, IconButton, TextField} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {Autocomplete} from "@material-ui/lab";
import {Clear} from '@material-ui/icons';
import {handleJson} from "../functions";


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

    const {items, reload, setError} = props;
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

    function onSubmit() {
        setFiles([]);
        reload();
    }

    const empty = files.length === 0 ? (<Grid item xs={12}><Text><p>
        Upload with no files selected will rescan existing data.
    </p></Text></Grid>) : null;

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
        {empty}
        <Grid item xs={12} className={classes.right}>
            <ConfirmedWriteButton label='Upload' href='/api/upload'
                                  setData={onSubmit} setError={setError}
                                  form={{'files': files, 'kit': kit}}>
                The ingest process will take some time.
            </ConfirmedWriteButton>
        </Grid>
    </>);
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
                <ColumnCard>
                    <FileSelect items={items} reload={reload} setError={setError}/>
                </ColumnCard>
            </ColumnList>
        </>);
    }
}


export default function Upload(props) {

    const {match, history} = props;
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
        <Layout navigation={<MainMenu/>}
                content={<Columns items={items} reload={reload} setError={setError}/>}
                match={match} title='Upload' reload={reload} history={history}
                busyState={busyState} errorState={errorState}/>
    );
}
