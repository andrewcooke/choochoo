import React from 'react';
import mkfield from "./mkfield";


const IntegerField = mkfield({rx: /^\d*$/, xs: 4});
export default IntegerField;
