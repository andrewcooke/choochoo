import React from 'react';
import {AppBar, Toolbar, IconButton, Typography} from '@material-ui/core';
import MenuIcon from '@material-ui/icons/Menu';
import SideDrawer from './SideDrawer'
import {makeStyles} from '@material-ui/core/styles';
import {drawerWidth} from '../../constants'
import LatestIcon from "./LatestIcon";
import Menu from "../Menu";
import UploadIcon from "./UploadIcon";


const useStyles = makeStyles(theme => ({
    appBar: {
        [theme.breakpoints.up('lg')]: {
            width: `calc(100% - ${drawerWidth}px)`,
            marginLeft: drawerWidth,
        },
    },
    menuButton: {
        marginRight: theme.spacing(2),
        [theme.breakpoints.up('lg')]: {
            display: 'none',
        },
    },
    toolbar: {
        justifyContent: 'space-between',
    },
}));


export default function Navigation(props) {

    const {title} = props;
    const classes = useStyles();
    const [mobileOpen, setMobileOpen] = React.useState(false);

    function handleDrawerToggle() {
        setMobileOpen(!mobileOpen);
    }

    return (
        <>
            <AppBar position="fixed" className={classes.appBar} color='primary'>
                <Toolbar className={classes.toolbar}>
                    <IconButton color="inherit" aria-label="open drawer" edge="start"
                                onClick={handleDrawerToggle} className={classes.menuButton}>
                        <MenuIcon/>
                    </IconButton>
                    <Typography variant='h1' noWrap>
                        {title}
                    </Typography>
                    <span>
                        <UploadIcon/>
                        <LatestIcon/>
                    </span>
                </Toolbar>
            </AppBar>
            <SideDrawer mobileOpen={mobileOpen} handleDrawerToggle={handleDrawerToggle} content={<Menu/>}/>
        </>
    )
}
