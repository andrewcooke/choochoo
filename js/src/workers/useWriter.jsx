import React from "react";


export default function useWriter(json, writer) {

    const [value, setValue] = React.useState(json.value === null ? '' : json.value);

    function handleChange(event) {
        setValue(event.target.value);
        let data = {};
        data[json.label] = event.target.value;
        writer.postMessage(data);
    }

    return [value, handleChange]
}
