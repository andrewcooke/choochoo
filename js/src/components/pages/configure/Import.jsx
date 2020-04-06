import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, ConfirmedWriteButton, Layout, Loading, MainMenu, Text} from "../../elements";
import {handleJson} from "../../functions";


function Status(props) {

    const {imported} = props;

    setTimeout(() =>
        document.getElementById('description').innerHTML = profiles[profile][1], 0);

    return (<ColumnCard header='Status'>
        <Text>
            <p>text here</p>
            <div id='description'/>
        </Text>
        <ConfirmedWriteButton xs={3} label='Import' variant='contained' method='post'
                              href='/api/configure/initial'
                              json={{}}>
            Configuring the system will allow you to start uploading and analysing data.
        </ConfirmedWriteButton>
    </ColumnCard>)
}


function Columns(props) {

    const {imported} = props;

    if (imported === null) {
        return <Loading/>;
    } else {
        return (<ColumnList>
            <ColumnCard header='Introduction'><Text>
                <p>Diary and activity topics (the information you enter manually via the diary)
                    can be imported from a previous version.</p>
                <p>Note that these data must be imported <b>before</b> any new data are entered manually,
                    to avoid conflicts.</p>
                <p>Activity data, which is read from FIT files, will be re-read automatically when
                    new activities are uploaded.</p>
            </Text></ColumnCard>
            <Status imported={imported}/>
        </ColumnList>);
    }
}


export default function Import(props) {

    const {match, history} = props;
    const [imported, setImported] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/configure/import-status')
            .then(handleJson(history, setImported, setError))
            .catch(reason => {
                console.warn('configure/profiles:', reason);
            });
    }, [1]);

    return (
        <Layout navigation={<MainMenu configure/>}
                content={<Columns imported={imported}/>}
                match={match} title='Import Old Data' errorState={errorState}/>
    );
}
