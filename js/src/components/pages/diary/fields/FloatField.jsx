import React from 'react';
import mkfield from "./mkfield";


const FloatField = mkfield({rx: /^\d*$/, xs: 4});
export default FloatField;
