import React from 'react';
import Drawer from '@material-ui/core/Drawer';
import Hidden from '@material-ui/core/Hidden';
import {makeStyles, useTheme} from '@material-ui/core/styles';
import {drawerWidth} from '../../constants'
import Divider from "@material-ui/core/Divider";
import List from "@material-ui/core/List";
import ListItemLink from "./ListItemLink";
import {ListItemText} from "@material-ui/core";
import ListItem from "@material-ui/core/ListItem";


const useStyles = makeStyles(theme => ({
    drawer: {
        [theme.breakpoints.up('sm')]: {
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
                    <ListItemLink primary='Choochoo' to='/'/>
                </List>
            )
        } else {
            return (
                <List>
                    <ListItem>
                        <ListItemText primary='Choochoo'/>
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
            <Divider/>
            {content}
        </>
    );
}


export default function SideDrawer(props) {

    const {container, content, mobileOpen, handleDrawerToggle, match} = props;

    const classes = useStyles();
    const theme = useTheme();

    return (
        <nav className={classes.drawer}>
            <Hidden smUp implementation="css">
                <Drawer
                    container={container}
                    variant="temporary"
                    anchor={theme.direction === 'rtl' ? 'right' : 'left'}
                    open={mobileOpen}
                    onClose={handleDrawerToggle}
                    classes={{
                        paper: classes.drawerPaper,
                    }}
                    ModalProps={{
                        keepMounted: true, // Better open performance on mobile.
                    }}
                >
                    <Content match={match} content={content}/>
                </Drawer>
            </Hidden>
            <Hidden xsDown implementation="css">
                <Drawer
                    classes={{
                        paper: classes.drawerPaper,
                    }}
                    variant="permanent"
                    open
                >
                    <Content match={match} content={content}/>
                </Drawer>
            </Hidden>
        </nav>
    );
}
