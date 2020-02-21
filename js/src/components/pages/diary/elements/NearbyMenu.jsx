import React from "react";
import {MenuItem} from "@material-ui/core";
import {MenuButton} from "../../../utils";


export default function NearbyMenu(props) {

    const {json, history} = props;
    const [head, ...rest] = json;

    function mkItem(row, handleClose) {
        const date = row.db[0].split(' ')[0];
        function onClick() {
            handleClose();
            history.push('/' + date);
        }
        return (<MenuItem onClick={onClick}>{row.value}</MenuItem>);
    }

    return (<MenuButton json={rest} label={head.value} mkItem={mkItem}/>);
}
