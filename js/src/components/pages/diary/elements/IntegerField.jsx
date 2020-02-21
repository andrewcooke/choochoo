import React from 'react';
import mkEditableField from "./mkEditableField";


const IntegerField = mkEditableField({rx: /^\d*$/, xs: 4});
export default IntegerField;
