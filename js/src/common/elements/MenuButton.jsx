import React from "react";
import {Button, Menu, MenuItem, Grid, Link} from "@material-ui/core";
import {Text} from '.';
import MenuIcon from '@material-ui/icons/Menu'
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    icon: {
        verticalAlign: 'middle',
        color: theme.palette.text.disabled, /* secondary isn't visible */
    },
    button: {
        width: '100%',
    },
}));


export default function MenuButton(props) {

    const {json, label, mkItem} = props;
    const [anchor, setAnchor] = React.useState(null);
    const classes = useStyles();

    const handleClick = event => {
        setAnchor(event.currentTarget);
    };

    const handleClose = () => {
        setAnchor(null);
    };

    const items = json.map((row, i) => mkItem(row, handleClose, i));

    return (<>
        <Button variant='outlined' onClick={handleClick} className={classes.button}>
            <MenuIcon className={classes.icon}/>
            <Text>{label}</Text>
        </Button>
        <Menu anchorEl={anchor} keepMounted open={Boolean(anchor)} onClose={handleClose}>{items}</Menu>
    </>);
}
