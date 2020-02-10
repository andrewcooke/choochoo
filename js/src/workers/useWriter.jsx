import React, {useState} from "react";


export function useWriter(json, writer) {

    const [value, setValue] = useState(json.value === null ? '' : json.value);

    function handleChange(event) {
        setValue(event.target.value);
        let data = {};
        data[json.label] = event.target.value;
        writer.postMessage(data);
    }

    return [value, handleChange]
}


export function useWriterRx(json, writer, rx, setError) {

    const [value, setValue] = useState(json.value === null ? '' : json.value);

    function handleChange(event) {
        const value = event.target.value;
        setValue(value);
        const ok = rx.test(value);
        setError(! ok);
        if (ok) {
            let data = {};
            data[json.label] = value;
            writer.postMessage(data);
        }
    }

    return [value, handleChange]
}
