import React, {useEffect, useState} from 'react';


export default function Image(props) {

    const {url, className} = props;
    const [image, setImage] = useState(null);

    useEffect(() => {
        fetch(url)
            .then(response => response.blob())
            .then(setImage);
    }, [url]);

    return (image === null ? <p>?</p> : <img src={URL.createObjectURL(image)} className={className}/>)
}
