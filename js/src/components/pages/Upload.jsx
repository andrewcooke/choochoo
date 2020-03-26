import React, {useEffect, useState} from 'react';
import {ColumnList, Layout, Loading, MainMenu, ColumnCard} from "../elements";
import {Button, Grid, TextField} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {Autocomplete} from "@material-ui/lab";


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
}));


function FileSelect(props) {

    const {items} = props;
    const classes = useStyles();
    const [files, setFiles] = useState([]);
    console.log(files);

    function onChange() {
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

    return (<>
        <Grid item xs={12}>
            <input accept='*/*' id='upload-input' multiple type='file' onChange={onChange} className={classes.input}/>
            <label htmlFor='upload-input'>
                <Button variant='outlined' component='span'>Select files</Button>
            </label>
        </Grid>
        <Grid item xs={8}>
            <p>file list</p>
        </Grid>
        <Grid item xs={12}>
            <Autocomplete multiple options={items.map(item => item.name)} filterSelectedOptions
                          className={classes.wide} size='small'
                          renderInput={params => (<TextField {...params} variant='outlined' label='Kit'/>)}/>
        </Grid>
        <Grid item xs={12} className={classes.right}>
            <Button variant='outlined' component='span' disabled={files.length === 0}>Upload</Button>
        </Grid>
    </>);
}


function Columns(props) {

    const {items} = props;

    if (items === null) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<ColumnList>
            <ColumnCard>
                <FileSelect items={items}/>
            </ColumnCard>
        </ColumnList>);
    }
}


export default function Upload(props) {

    const {match} = props;
    const [json, setJson] = useState(null);

    useEffect(() => {
        setJson(null);
        fetch('/api/kit/items')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [1]);

    return (
        <Layout navigation={<MainMenu/>} content={<Columns items={json}/>} match={match} title='Upload'/>
    );
}
