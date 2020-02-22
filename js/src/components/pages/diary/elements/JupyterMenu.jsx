import React from "react";
import {MenuItem} from "@material-ui/core";
import {MenuButton, zip} from "../../../utils";


export default function JupyterMenu(props) {

    const {json, label, template, params} = props;
    const [, ...rest] = json;

    function mkItem(row, handleClose) {
        const urlArgs = zip(params, row.db).map(([name, value]) => name + '=' + value).join('&');
        function onClick() {
            handleClose();
            window.open('jupyter/' + template + '?' + urlArgs, '_blank');
        }
        return (<MenuItem onClick={onClick}>{row.value}</MenuItem>);
    }

    return (<MenuButton json={rest} label={label} mkItem={mkItem}/>);
}
