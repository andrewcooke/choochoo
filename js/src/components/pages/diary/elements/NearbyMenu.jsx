import React from "react";
import {MenuItem, Grid} from "@material-ui/core";
import {MenuButton} from "../../../elements";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    center: {
        textAlign: 'center',
    },
}));


export default function NearbyMenu(props) {

    const {json, history} = props;
    const [head, ...rest] = json;
    const classes = useStyles();

    function mkItem(row, handleClose, i) {
        const date = row.db[0].split(' ')[0];
        function onClick() {
            handleClose();
            history.push('/' + date);
        }
        return (<MenuItem onClick={onClick} key={i}>{row.value}</MenuItem>);
    }

    return (<Grid item xs={4} className={classes.center}>
        <MenuButton json={rest} label={head.value} mkItem={mkItem}/>
    </Grid>);
}
