import React, {useEffect, useState} from 'react';
import {
    ColumnCard,
    ColumnList,
    ConfirmedWriteButton,
    Layout,
    Loading,
    MainMenu,
    ScrollableListCard,
    Text
} from "../../elements";
import {handleJson} from "../../functions";
import {Autocomplete} from "@material-ui/lab";
import {Grid, TextField} from "@material-ui/core";


function Results(props) {
    const {results} = props;
    return (<>
        {results.warnings.length > 0 ? <ScrollableListCard header='Warnings' list={results.warnings}/> : null}
        {results.loaded.length > 0 ? <ScrollableListCard header='Loaded' list={results.loaded}/> : null}
        </>);
}


function Source(props) {

    const {versions, reload, setResults} = props;
    const [version, setVersion] = useState(versions.length > 0 ? versions[0] : null);

    return (<ColumnCard header='Source'>
        <Grid item xs={12}><Text>
            <p>Enter below the source for data to import.</p>
            <p>This can be a version number
                (if sharing the same directory structure as the current install)
                or a database file.</p>
        </Text></Grid>
        <Grid item xs={9}>
            <Autocomplete options={versions} label='Source' freeSolo value={version}
                          onInputChange={(event, value) => setVersion(value)}
                          renderInput={params => <TextField {...params} label='Source' variant='outlined'/>}/>
        </Grid>
        <ConfirmedWriteButton xs={3} label='Import' variant='contained' method='post'
                              href='/api/configure/import' setData={setResults}
                              json={{'version': version}}>
            Importing the data will preserve you diary entries from the previous install.
        </ConfirmedWriteButton>
    </ColumnCard>)
}


function Status(props) {

    const {imported} = props;

    const description = Object.keys(imported).map(key =>
        `<li>${key}: ` + (imported[key] ? 'already present' : 'can be imported') + '</li>'
    ).join('');

    setTimeout(() =>
        document.getElementById('description').innerHTML = description, 0);

    return (<ColumnCard header='Status'>
        <Grid item xs={12}><Text>
            <ul id='description'/>
            <p>Constants can be imported whenever there are unset values;
                other data must be completely unset.</p>
        </Text></Grid>
    </ColumnCard>);
}


function Columns(props) {

    const {data, resultsState} = props;
    const [results, setResults] = resultsState;

    if (data === null) {
        return <Loading/>;
    } else {
        const enabled = Object.values(data.imported).some(value => !value);
        console.log(enabled, results);
        return (<ColumnList>
            <ColumnCard header='Introduction'><Grid item xs={12}><Text>
                <p>Choochoo manages three kinds of data: activity data from FIT files; user data
                    entered by hand (via the web, command line and diary); and calculated statistics.</p>
                <p>When you update to a new database, activity data can be re-read from FIT files
                    and statistics can be re-calculated.  User data, however, must be copied across
                    from the previous version.</p>
                <p>User data includes diary topics (user data associated with a given date),
                    activity topics (user data associated with a particular activity),
                    and kit details.</p>
                <p>Note that these data must be imported <b>before</b> any new data are entered manually,
                    to avoid conflicts.</p>
            </Text></Grid></ColumnCard>
            {results === null ? <Status imported={data.imported}/> : null}
            {results === null && enabled ? <Source versions={data.versions} setResults={setResults}/> : null}
            {results !== null ? <Results results={results}/> : null}
        </ColumnList>);
    }
}


export default function Import(props) {

    const {match, history} = props;
    const [data, setData] = useState(null);
    const resultsState = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/configure/import-status')
            .then(handleJson(history, setData, setError))
            .catch(reason => {
                console.warn('configure/profiles:', reason);
            });
    }, [1]);

    return (
        <Layout navigation={<MainMenu configure/>}
                content={<Columns data={data} resultsState={resultsState}/>}
                match={match} title='Import User Data' errorState={errorState}/>
    );
}
