import React, {useEffect, useState} from 'react';
import {csrfFetch} from "../functions";


export default function Image(props) {

    const {url, className} = props;
    const [image, setImage] = useState(null);

    useEffect(() => {
        csrfFetch(url)
            .then(response => response.blob())
            .then(setImage);
    }, [url]);

    return (image === null ? <p>?</p> : <img src={URL.createObjectURL(image)} className={className}/>)
}
