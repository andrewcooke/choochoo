import React, {useEffect, useState} from 'react';
import {Layout} from "../../elements";
import {ColumnList, Loading} from "../../../common/elements";
import {handleJson} from "../../functions";


function Columns(props) {

    const {route} = props;

    if (route === null) {
        return (<>
            <Loading/>
        </>);
    } else {
        return (<>
            <ColumnList>
                <p>map here</p>
            </ColumnList>
        </>);
    }
}


export default function Create(props) {

    const {match, history} = props;
    const {id} = match.params;
    const [route, setRoute] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/route/activity/' + id)
            .then(handleJson(history, setRoute, setError));
    }, [id]);

    return (
        <Layout title='New Sector'
                content={<Columns route={route}/>}
                errorState={errorState}/>
    );
}
