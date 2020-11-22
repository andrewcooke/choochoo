import React from "react";
import {Publish} from '@material-ui/icons';
import {LinkIcon} from ".";


export default function UploadIcon(props) {
    return <LinkIcon url='/upload' tooltip='Upload' icon={<Publish/>}/>;
}
