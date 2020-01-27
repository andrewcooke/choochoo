import React from 'react';
import Drawer from '@material-ui/core/Drawer';
import Hidden from '@material-ui/core/Hidden';
import {makeStyles, useTheme} from '@material-ui/core/styles';
import {drawerWidth} from '../../layout'
import AppBar from "@material-ui/core/AppBar";
import Tabs from "@material-ui/core/Tabs";
import Tab from "@material-ui/core/Tab";
import Typography from "@material-ui/core/Typography";
import Box from "@material-ui/core/Box";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Button from "@material-ui/core/Button";
import ArrowBackIcon from '@material-ui/icons/ArrowBack';


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
    button: {
        'min-width': 79,
    },
}));


function TabPanel(props) {

    const {children, value, index, ...other} = props;

    return (
        <Typography
            component="div"
            role="tabpanel"
            hidden={value !== index}
            id={`simple-tabpanel-${index}`}
            aria-labelledby={`simple-tab-${index}`}
            {...other}
        >
            {value === index && <Box p={3}>{children}</Box>}
        </Typography>
    );
}


function MainMenu(props) {

    const {onClick} = props;

    return (
        <div>
            <List component="nav">
                <ListItem button onClick={() => onClick(1)}>
                    <ListItemText primary="Diary" />
                </ListItem>
            </List>
        </div>)
}


function DiaryMenu(props) {

    const {back} = props;

    const [value, setValue] = React.useState(0);
    const handleChange = (event, newValue) => {
        setValue(newValue);
    };

    const classes = useStyles();

    return (
        <div>
            <Button onClick={back}>
                <ArrowBackIcon/>
            </Button>
            <AppBar position="static">
                <Tabs value={value} variant="fullWidth" onChange={handleChange}>
                    <Tab label="Day" className={classes.button}/>
                    <Tab label="Month" className={classes.button}/>
                    <Tab label="Year" className={classes.button}/>
                </Tabs>
            </AppBar>
            <TabPanel value={value} index={0}>
                Day Picker
            </TabPanel>
            <TabPanel value={value} index={1}>
                Month Picker
            </TabPanel>
            <TabPanel value={value} index={2}>
                Year Picker
            </TabPanel>
        </div>
    );
}


export default function SideDrawer(props) {

    const {container, mobileOpen, handleDrawerToggle} = props;

    const [topMenu, setTopMenu] = React.useState(0);
    const handleChange = (event, newValue) => {
        setTopMenu(newValue);
    };

    const classes = useStyles();
    const theme = useTheme();

    const mainMenuTabs = (
        <div>
            <div className={classes.toolbar}/>
            <TabPanel value={topMenu} index={0}>
                <MainMenu back={() => setTopMenu(0)} onClick={setTopMenu}/>
            </TabPanel>
            <TabPanel value={topMenu} index={1}>
                <DiaryMenu back={() => setTopMenu(0)}/>
            </TabPanel>
        </div>
    );

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
                    {mainMenuTabs}
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
                    {mainMenuTabs}
                </Drawer>
            </Hidden>
        </nav>
    );
}