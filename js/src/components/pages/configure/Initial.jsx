import React, {useEffect, useState} from 'react';
import {Grid, Menu, MenuItem, Button} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, MainMenu, P, Loading, Text} from "../../elements";
import {handleGet} from "../../functions";
import {Link} from "react-router-dom";


function Directory(props) {

    const {data} = props;

    return (<ColumnCard header='Directories'><Text>
        <p>Choochoo uses two separate directories for storage:</p>
        <ul>
            <li>Database, log files, and Jupyter notebooks are stored at<br/>
                <pre>{data.directory}</pre>
                This location can only be changed by specifying an alternative when
                starting the web server:<br/>
                <pre>ch2 --dir DIRECTORY web start</pre>
            </li>
            <li>Uploaded FITS files are stored in DATA_DIR which is
                a <Link to='/configure/constants'>constant</Link> that can be configured later.
            </li>
        </ul>
    </Text></ColumnCard>)
}


function Profiles(props) {

    const {data} = props;
    const profiles = Object.keys(data.profiles).map(name => [name, data.profiles[name]]);
    const [anchor, setAnchor] = React.useState(null);
    const [profile, setProfile] = useState(profiles.findIndex(entry => entry[0] === 'default'));

    setTimeout(() => document.getElementById('description').innerHTML = profiles[profile][1], 0);

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
            <p>Explanation here.</p>
        </Text>
        <Button variant='outlined' onClick={onButtonClick}>{profiles[profile][0]}</Button>
        <Menu keepMounted open={Boolean(anchor)} onClose={onMenuClose} anchorEl={anchor}>
            {profiles.map(
                (entry, index) =>
                    <MenuItem onClick={() => onItemClick(index)} selected={index === profile}>
                        {entry[0].toUpperCase()}
                    </MenuItem>)}
        </Menu>
        <Text><div id='description'/></Text>
    </Text></ColumnCard>)

}


function Columns(props) {

    const {data} = props;

    if (data === null) {
        return <Loading/>;
    } else if (data.configured) {
        return (<ColumnList>
            <Directory data={data}/>
            <ColumnCard><Grid item xs={12}>
                <P>The initial configuration has already been made.</P>
            </Grid></ColumnCard>
        </ColumnList>);
    } else {
        return (<ColumnList>
            <Directory data={data}/>
            <Profiles data={data}/>
        </ColumnList>);
    }
}


export default function Initial(props) {

    const {match, history} = props;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/configure/profiles')
            .then(handleGet(history, setData, setError));
    }, [1]);

    return (
        <Layout navigation={<MainMenu configure/>}
                content={<Columns data={data}/>}
                match={match} title='Configure' errorState={errorState}/>
    );
}
