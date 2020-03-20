import React, {useEffect, useState} from 'react';
import {Layout, Loading, MainMenu} from "../../elements";


function Columns(props) {

    const {params} = props;

    if (params === null) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<p>todo</p>);
    }
}


export default function Change(props) {

    const {match} = props;
    const [json, setJson] = useState(null);

    useEffect(() => {
        setJson(null);
        fetch('/api/kit/show')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [1]);

    return (
        <Layout navigation={<MainMenu/>} content={<Columns params={json}/>} match={match} title='Change Kit'/>
    );
}
