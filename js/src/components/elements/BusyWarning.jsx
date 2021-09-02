import {Warning} from "../../common/elements";
import React, {useEffect, useState} from "react";
import {useHistory} from "react-router-dom";
import {csrfFetch, handleJson} from "../functions";


export default function BusyWarning(props) {

    const {setError} = props;
    const [busy, setBusy] = useState(false);
    const history = useHistory()

    useEffect(() => {
        csrfFetch('/api/busy').then(handleJson(history, setBusy, setError));
    }, [setError]);

    return busy ? (<Warning title='Busy'
                            warning='Background processes are running so data may be incomplete.'/>) : <></>;
}
