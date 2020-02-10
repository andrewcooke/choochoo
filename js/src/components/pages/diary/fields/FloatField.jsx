import React from 'react';
import mkfield from "./mkfield";


const FloatField = mkfield({rx: /^\d*$/, sm: 4, md: 2});
export default FloatField;
