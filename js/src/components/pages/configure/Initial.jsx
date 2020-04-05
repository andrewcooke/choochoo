import React, {useEffect, useState} from 'react';
import {Button, Dialog, DialogContent, DialogContentText, DialogTitle, Grid, Menu, MenuItem} from "@material-ui/core";
import {ColumnCard, ColumnList, ConfirmedWriteButton, Layout, Loading, MainMenu, P, Text} from "../../elements";
import {handleJson} from "../../functions";
import {Link} from "react-router-dom";


function Directory(props) {

    const {data} = props;

    return (<ColumnCard header='Directories'><Text>
        <p>Choochoo uses two separate directories for storage:</p>
        <ul>
            <li>Database, log files, and Jupyter notebooks are stored in the base directory:<br/>
                <pre>{data.directory}</pre>
                This location can only be changed by specifying an alternative when
                starting the web server:<br/>
                <pre>ch2 --base DIRECTORY web start</pre>
            </li>
            <li>Uploaded FITS files are stored in DATA_DIR which is
                a <Link to='/configure/constants'>constant</Link> that can be configured later.
            </li>
        </ul>
        <p>If you configure the system incorrectly you can start over by deleting the
            base directory.  You will not lose the FIT files containing your
            activities, which can be reloaded, but you <b>will</b> lose any diary
            entries you have added.  To avoid this you can use the scripts in the
            ch2.migrate.reload package.  Hopefully this will become simpler in a
            future release.</p>
    </Text></ColumnCard>)
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
        <ColumnCard header='Reset'><Text>
            <Text>
                <p>You can delete the base directory, removing all data in the database.</p>
            </Text>
            <ConfirmedWriteButton xs={3} label='Delete' variant='contained' method='post'
                                  href='/api/configure/delete' reload={reload}
                                  json={{}} onComplete={onComplete}>
                Some data can be recalculated from the FITS files (which are <b>not</b> deleted),
                but you will lose any information entered directly into the diary.
            </ConfirmedWriteButton>
        </Text></ColumnCard>
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
    const profiles = Object.keys(data.profiles).map(name => [name, data.profiles[name]]);
    const [anchor, setAnchor] = React.useState(null);
    const [profile, setProfile] = useState(profiles.findIndex(entry => entry[0] === 'default'));

    // do this after the DOM has been created
    setTimeout(() =>
        document.getElementById('description').innerHTML = profiles[profile][1], 0);

    function onButtonClick(event) {
        setAnchor(event.currentTarget);
    }

    function onMenuClose() {
        setAnchor(null);
    }

    function onItemClick(index) {
        setProfile(index);
        setAnchor(null);
    }

    return (<ColumnCard header='Profiles'><Text>
        <Text>
            <p>Profiles allow you to choose how the system is configured.</p>
            <p>If you want a custom configuration you will need to add your own profile
                (ie write custom code) to the package ch2.config.profile - it will then
                appear here.</p>
            <p>As the interface improves this may become less necessary, with more features
                being selectable after the initial configuration.</p>
            <p>Selected profile:
                <Button variant='outlined' onClick={onButtonClick}>{profiles[profile][0]}</Button>
                <Menu keepMounted open={Boolean(anchor)} onClose={onMenuClose} anchorEl={anchor}>
                    {profiles.map(
                        (entry, index) =>
                            <MenuItem onClick={() => onItemClick(index)} selected={index === profile}>
                                {entry[0].toUpperCase()}
                            </MenuItem>)}
                </Menu></p>
            <div id='description'/>
        </Text>
        <ConfirmedWriteButton xs={3} label='Configure' variant='contained' method='post'
                              href='/api/configure/initial' reload={reload}
                              json={{'profile': profiles[profile][0]}}>
            Configuring the system will allow you to start uploading and analysing data.
        </ConfirmedWriteButton>
    </Text></ColumnCard>)
}


function ConfiguredYes(props) {

    const {data, reload} = props;

    return (<ColumnList>
        <ColumnCard header='Configured'><Grid item xs={12}>
            <P>The initial system is configured (version {data.version}).</P>
        </Grid></ColumnCard>
        <Directory data={data}/>
        <Delete reload={reload}/>
    </ColumnList>);
}


function ConfiguredNo(props) {

    const {data ,reload} = props;

    return (<ColumnList>
        <ColumnCard header='Introduction'><Text>
            <p>A freshly installed system does not 'know' what to do.  The initial
                configuration defines pipelines for loading data, calculating statistics,
                and displaying results, as well as defining what entries are present in
                the diary.</p>
        </Text></ColumnCard>
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
