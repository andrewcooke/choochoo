import createMuiTheme from "@material-ui/core/styles/createMuiTheme";
import {green, grey} from "@material-ui/core/colors";


export const theme = createMuiTheme({
  palette: {
    primary: grey,
    secondary: green
  },
});

theme.typography.h1.fontSize = '1.5rem';
theme.typography.h2.fontSize = '1.1rem';
theme.typography.h3.fontSize = '1.1rem';
theme.typography.h4.fontSize = '1.0rem';

theme.typography.h1.fontWeight = 300;
theme.typography.h2.fontWeight = 500;
theme.typography.h3.fontWeight = 400;
theme.typography.h4.fontWeight = 400;
