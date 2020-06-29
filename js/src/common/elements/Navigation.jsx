import React from 'react';
import {AppBar, IconButton, Toolbar, Typography} from '@material-ui/core';
import MenuIcon from '@material-ui/icons/Menu';
import {SideDrawer} from '.'
import {makeStyles} from '@material-ui/core/styles';
import {drawerWidth} from '../constants'


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

    const {menu, title, icons} = props;
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
                        {icons}
                    </span>
                </Toolbar>
            </AppBar>
            <SideDrawer mobileOpen={mobileOpen} handleDrawerToggle={handleDrawerToggle} content={menu}/>
        </>
    )
}
