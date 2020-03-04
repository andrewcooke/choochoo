import React from "react";
import {MenuItem} from "@material-ui/core";
import {MenuButton} from "../../../elements";
import {zip} from "../../../functions";


export default function JupyterMenu(props) {

    const {json, label, template, params} = props;
    const [, ...rest] = json;

    function mkItem(row, handleClose) {
        const urlArgs = zip(params, row.db).map(([name, value]) => name + '=' + value).join('&');
        function onClick() {
            handleClose();
            window.open('jupyter/' + template + '?' + urlArgs, '_blank');
        }
        return (<MenuItem onClick={onClick} key={row.id}>{row.value}</MenuItem>);
    }

    return (<MenuButton json={rest} label={label} mkItem={mkItem}/>);
}
