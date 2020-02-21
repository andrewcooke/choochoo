import React from "react";
import {Link, MenuItem} from "@material-ui/core";
import {zip, MenuButton} from "../../../utils";


export default function JupyterMenu(props) {

    const {json, label, template, params} = props;
    const [, ...rest] = json;

    function mkItem(row, handleClose) {
        const urlArgs = zip(params, row.db).map(([name, value]) => name + '=' + value).join('&');
        return (<MenuItem onClick={handleClose} key={row.id}>
            <Link href={'jupyter/' + template + '?' + urlArgs} target='_blank'>{row.value}</Link>
        </MenuItem>);
    }

    return (<MenuButton json={rest} label={label} mkItem={mkItem}/>);
}
