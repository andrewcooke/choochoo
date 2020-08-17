import React from "react";
import {MenuItem, Grid} from "@material-ui/core";
import {MenuButton} from "../../../../common/elements";
import {zip} from "../../../../common/functions";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    center: {
        textAlign: 'center',
    },
}));


export default function JupyterMenu(props) {

    const {json, label, template, params} = props;
    const classes = useStyles();

    function mkItem(row, handleClose, i) {
        const urlArgs = zip(params, row.db).map(([name, value]) => name + '=' + value).join('&');
        function onClick() {
            handleClose();
            window.open('api/jupyter/' + template + '?' + urlArgs, '_blank');
        }
        return (<MenuItem onClick={onClick} key={i}>{row.value}</MenuItem>);
    }

    return (<Grid item xs={4} className={classes.center}>
        <MenuButton json={json} label={label} mkItem={mkItem}/>
    </Grid>);
}
