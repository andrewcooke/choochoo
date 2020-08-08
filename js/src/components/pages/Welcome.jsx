import React, {useEffect, useState} from 'react';
import {Grid, Link} from "@material-ui/core";
import {ColumnCard, ColumnList, P, Warning} from "../../common/elements";
import {BusyWarning, Layout} from "../elements";
import handleJson from "../functions/handleJson";
import {useHistory} from "react-router-dom";


function ConfigWarning(props) {

    const {warning} = props;
    const extra = (<P>For more information on how to configure docker see&nbsp;
            <Link href='https://andrewcooke.github.io/choochoo/docker'>here</Link>.</P>);

    return <Warning title={warning.title} warning={warning.text} extra={extra}/>;
}


function Warnings(props) {

    const {setError} = props;
    const [warnings, setWarnings] = useState([]);
    const history = useHistory()

    useEffect(() => {
        fetch('/api/warnings').then(handleJson(history, setWarnings, setError));
    }, [1]);

    return warnings.map((warning, i) => <ConfigWarning warning={warning} key={i}/>);
}


export default function Welcome(props) {

    const errorState = useState(null);
    const [error, setError] = errorState;

    const content = (<ColumnList>
        <ColumnCard><Grid item xs={12}>
            <P>Welcome to Choochoo - an open, hackable and free training diary.</P>
            <P>This is the web interface, which is under active development.
                To get started select an option from the menu.</P>
            <P>For more information on Choochoo please see the <Link
                href='https://andrewcooke.github.io/choochoo/'>documentation</Link> or <Link
                href='https://github.com/andrewcooke/choochoo'>source</Link>. You can report bugs <Link
                href='https://github.com/andrewcooke/choochoo/issues'>here</Link>.</P>
        </Grid></ColumnCard>
        <Warnings setError={setError}/>
        <BusyWarning setError={setError}/>
    </ColumnList>);

    return (
        <Layout title='Welcome' content={content} errorState={errorState}/>
    );
}
