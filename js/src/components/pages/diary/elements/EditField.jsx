import React from 'react';
import mkEditableField from "./mkEditableField";


const EditField = mkEditableField({rx: /^.*$/, xs: 12, multiline: true});
export default EditField;
