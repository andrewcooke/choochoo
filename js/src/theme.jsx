import createMuiTheme from "@material-ui/core/styles/createMuiTheme";
import {deepOrange, lime} from "@material-ui/core/colors";


export const theme =  createMuiTheme({
  palette: {
    type: 'dark',
    primary: lime,
    secondary: deepOrange,
  },
});

theme.typography.h1.fontSize = '1.7rem';
theme.typography.h2.fontSize = '1.3rem';
theme.typography.h3.fontSize = '1.1rem';
theme.typography.h4.fontSize = '1.0rem';

theme.typography.h1.fontWeight = 100;
theme.typography.h2.fontWeight = 400;
theme.typography.h3.fontWeight = 400;
theme.typography.h4.fontWeight = 400;

theme.typography.h1.lineHeight = 'normal';
theme.typography.h2.lineHeight = '200%';
theme.typography.h3.lineHeight = '200%';
theme.typography.h4.lineHeight = '200%';

