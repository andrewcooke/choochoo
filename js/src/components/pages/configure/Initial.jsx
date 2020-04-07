import React, {useEffect, useState} from 'react';
import {Dialog, DialogContent, DialogContentText, DialogTitle, Grid, TextField} from "@material-ui/core";
import {ColumnCard, ColumnList, ConfirmedWriteButton, Layout, Loading, MainMenu, P, Text} from "../../elements";
import {handleJson} from "../../functions";
import {Link} from "react-router-dom";
import {Autocomplete} from "@material-ui/lab";


function Directory(props) {

    const {data} = props;

    return (<ColumnCard header='Directories'><Grid item xs={12}><Text>
        <p>Choochoo uses two separate directories for storage:</p>
        <ul>
            <li>Database, log files, and Jupyter notebooks are stored below the base
                directory by version number:<br/>
                <pre>{data.directory}</pre>
                The base directory can be changed by specifying an alternative when
                starting the web server:<br/>
                <pre>ch2 --base DIRECTORY web start</pre>
            </li>
            <li>Uploaded FITS files are stored in DATA_DIR which is
                a <Link to='/configure/constants'>constant</Link> that can be configured later.
            </li>
        </ul>
    </Text></Grid></ColumnCard>)
}


function Delete(props) {

    const {data, reload} = props;
    const [wait, setWait] = useState(false);

    function onComplete() {
        console.log('complete');
        setWait(true);
        reload();
    }

    return (<>
        <ColumnCard header='Reset'>
            <Grid item xs={12}><Text>
                <p>You can delete the current version from the base directory,
                    removing all data in the database,
                    along with old logs and jupyter notebooks.</p>
                <p>Activity data can then imported from FIT files (assuming they were saved to DATA_DIR).
                    In most cases, user data from a previous version can also be imported
                    (assuming the previous database still exists).</p>
            </Text></Grid>
            <Grid item xs={9}/>
            <ConfirmedWriteButton xs={3} label='Delete' variant='contained' method='post'
                                  href='/api/configure/delete' setData={reload}
                                  json={{}} onComplete={onComplete}>
                Some data can be recalculated from the FITS files (which are <b>not</b> deleted),
                but you will lose any information entered directly into the diary.
            </ConfirmedWriteButton>
        </ColumnCard>
        <Dialog fullScreen={fullScreen} open={wait}>
            <DialogTitle>{'Please wait'}</DialogTitle>
            <DialogContent>
                <DialogContentText>Server is restarting.</DialogContentText>
            </DialogContent>
        </Dialog>
    </>)
}


function Profiles(props) {

    const {data, reload} = props;
    const profiles = data.profiles;
    const [profile, setProfile] = useState('default');

    // do this after the DOM has been created
    setTimeout(() =>
        document.getElementById('description').innerHTML = profiles[profile], 0);

    return (<ColumnCard header='Profiles'>
        <Grid item xs={12}><Text>
            <p>Profiles allow you to choose how the system is configured.</p>
            <p>If you want a custom configuration you will need to add your own profile
                (ie write custom code) to the package ch2.config.profile - it will then
                appear here.</p>
            <p>As the interface improves this may become less necessary, with more features
                being selectable after the initial configuration.</p>
        </Text></Grid>
        <Grid item xs={9}>
            <Autocomplete options={Object.keys(profiles)} filterSelectedOptions value={profile}
                          onChange={(event, value) =>
                              setProfile(value == null ? 'default' : value)}
                          renderInput={params => <TextField {...params} label='Profile' variant='outlined'/>}/>
        </Grid>
        <Grid item xs={12}><Text><div id='description'/></Text></Grid>
        <Grid item xs={9}/>
        <ConfirmedWriteButton xs={3} label='Configure' variant='contained' method='post'
                              href='/api/configure/initial' setData={reload}
                              json={{'profile': profile}}>
            Configuring the system will allow you to start uploading and analysing data.
        </ConfirmedWriteButton>
    </ColumnCard>)
}


function ConfiguredYes(props) {

    const {data, reload} = props;

    return (<ColumnList>
        <ColumnCard header='Configured'><Grid item xs={12}><Text>
            <P>The system is configured (version {data.version}).</P>
        </Text></Grid></ColumnCard>
        <Directory data={data}/>
        <Delete reload={reload}/>
    </ColumnList>);
}


function ConfiguredNo(props) {

    const {data ,reload} = props;

    return (<ColumnList>
        <ColumnCard header='Introduction'><Grid item xs={12}><Text>
            <p>A freshly installed system does not 'know' what to do.  The initial
                configuration defines pipelines for loading data, calculating statistics,
                and displaying results, as well as defining what entries are present in
                the diary.</p>
        </Text></Grid></ColumnCard>
        <Directory data={data}/>
        <Profiles data={data} reload={reload}/>
    </ColumnList>);
}


function Columns(props) {

    const {data ,reload} = props;

    if (data === null) {
        return <Loading/>;
    } else if (data.configured) {
        return <ConfiguredYes data={data} reload={reload}/>;
    } else {
        return <ConfiguredNo data={data} reload={reload}/>;
    }
}


export default function Initial(props) {

    const {match, history} = props;
    const [data, setData] = useState(null);
    const [reads, setReads] = useState(0);
    const errorState = useState(null);
    const [error, setError] = errorState;

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        fetch('/api/configure/profiles')
            .then(handleJson(history, setData, setError))
            .catch(reason => {
                console.warn('configure/profiles:', reason);
                console.log('will retry in 1s')
                setTimeout(reload, 1000);
            });
    }, [reads]);

    return (
        <Layout navigation={<MainMenu configure/>}
                content={<Columns data={data} reload={reload}/>}
                match={match} title='Initial Configuration' errorState={errorState}/>
    );
}
