import React from "react";
import {Button, Menu, MenuItem, Grid} from "@material-ui/core";
import Text from "../../../utils/Text";
import MenuIcon from '@material-ui/icons/Menu'
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    icon: {
        verticalAlign: 'middle',
    },
}));


export default function NearbyMenu(props) {

    const {json, history} = props;
    const [head, ...rest] = json;
    const [anchor, setAnchor] = React.useState(null);
    const classes = useStyles();

    const handleClick = event => {
        setAnchor(event.currentTarget);
    };

    const handleClose = () => {
        setAnchor(null);
    };

    const items = rest.map(row => {
        const date = row.db[0].split(' ')[0];
        function onClick() {
            handleClose();
            history.push('/' + date);
        }
        return (<MenuItem onClick={onClick}>{row.value}</MenuItem>);
    });

    return (<Grid item xs={4}>
        <Button onClick={handleClick}>
            <MenuIcon className={classes.icon}/>
            <Text>{head.value}</Text>
        </Button>
        <Menu anchorEl={anchor} keepMounted open={Boolean(anchor)} onClose={handleClose}>{items}</Menu>
    </Grid>);
}
