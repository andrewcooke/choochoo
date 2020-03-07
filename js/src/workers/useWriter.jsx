import React, {useState} from "react";


export function useWriter(json, writer) {

    // used like useState, but the equivalent of setValue also writes back to the server.

    const [value, setValue] = useState(json.value === null ? '' : json.value);

    function handleChange(event) {
        setValue(event.target.value);
        let data = {};
        data[json.db] = event.target.value;
        writer.postMessage(data);
    }

    return [value, handleChange]
}


export function useWriterRx(json, writer, rx, setError) {

    // as above, but validates using an rx first, and only writes if ok.

    const [value, setValue] = useState(json.value === null ? '' : json.value);

    function handleChange(event) {
        const value = event.target.value;
        setValue(value);
        const ok = rx.test(value);
        setError(! ok);
        if (ok) {
            let data = {};
            data[json.db] = value;
            writer.postMessage(data);
        }
    }

    return [value, handleChange]
}
