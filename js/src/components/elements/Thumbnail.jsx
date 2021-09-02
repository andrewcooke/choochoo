import React, {useEffect, useState} from 'react';
import {csrfFetch} from "../functions";


export default function Thumbnail(props) {

    /* TODO - is this needed?!!  look at thumbnail in SectorField */

    const {activity_id, className} = props;
    const [image, setImage] = useState(null);

    useEffect(() => {
        csrfFetch('/api/thumbnail/' + encodeURIComponent(activity_id))
            .then(response => response.blob())
            .then(setImage);
    }, [activity_id]);

    return (image === null ?
        <p>?</p> :
        <img alt='' src={URL.createObjectURL(image)} className={className}/>)
}
