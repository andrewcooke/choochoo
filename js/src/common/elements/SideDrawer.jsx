import React from 'react';
import {makeStyles, useTheme} from '@material-ui/core/styles';
import {drawerWidth} from '../constants'
import {ListItemLink} from ".";
import {ListItemText, ListItemIcon, ListItem, List, Divider, Drawer, Hidden} from "@material-ui/core";
import {HomeOutlined, Home} from "@material-ui/icons";


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


function Content(props) {

    const {match, content} = props;
    const classes = useStyles();

    function Back() {
        if (match.path !== '/') {
            return (
                <List>
                    <ListItemLink primaryTypographyProps={{variant: 'h1'}}
                                  icon={<Home/>} primary='Choochoo' to='/'/>
                </List>
            )
        } else {
            return (
                <List>
                    <ListItem>
                        <ListItemIcon><HomeOutlined/></ListItemIcon>
                        <ListItemText primaryTypographyProps={{variant: 'h1'}}
                                      primary='Choochoo'/>
                    </ListItem>
                </List>
            )
        }
    }

    return (
        <>
            <div className={classes.toolbar}>
                <Back/>
            </div>
            {content}
        </>
    );
}


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
