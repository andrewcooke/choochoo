import React from 'react';
import mkfield from "./mkfield";


const EditField = mkfield({rx: /^.*$/, xs: 6, multiline: true});
export default EditField;
