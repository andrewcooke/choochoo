import React from 'react';
import {makeStyles, useTheme} from '@material-ui/core/styles';
import {drawerWidth} from '../constants'
import {Drawer, Hidden} from "@material-ui/core";


const useStyles = makeStyles(theme => ({
    drawer: {
        [theme.breakpoints.up('lg')]: {
            width: drawerWidth,
            flexShrink: 0,
        },
    },
    toolbar: theme.mixins.toolbar,
    drawerPaper: {
        width: drawerWidth,
    },
}));


export default function SideDrawer(props) {

    const {container, content, mobileOpen, handleDrawerToggle} = props;

    const classes = useStyles();
    const theme = useTheme();

    // todo - fix up classes below
    return (
        <nav className={classes.drawer}>
            <Hidden lgUp implementation="css">
                <Drawer container={container} variant="temporary"
                        anchor={theme.direction === 'rtl' ? 'right' : 'left'}
                        open={mobileOpen} onClose={handleDrawerToggle}
                        classes={{
                            paper: classes.drawerPaper,
                        }}
                        ModalProps={{
                            keepMounted: true, // Better open performance on mobile.
                        }}>
                    {content}
                </Drawer>
            </Hidden>
            <Hidden mdDown implementation="css">
                <Drawer
                    classes={{
                        paper: classes.drawerPaper,
                    }}
                    variant="permanent" open>
                    {content}
                </Drawer>
            </Hidden>
        </nav>
    );
}
