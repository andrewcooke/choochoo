import {Warning} from "../../common/elements";
import React, {useEffect, useState} from "react";
import {useHistory} from "react-router-dom";
import handleJson from "../functions/handleJson";


export default function BusyWarning(props) {

    const {setError} = props;
    const [busy, setBusy] = useState(false);
    const history = useHistory()

    useEffect(() => {
        fetch('/api/busy').then(handleJson(history, setBusy, setError));
    }, [1]);

    return busy ? (<Warning title='Busy'
                            warning='Background processes are running so data may be incomplete.'/>) : <></>;
}
