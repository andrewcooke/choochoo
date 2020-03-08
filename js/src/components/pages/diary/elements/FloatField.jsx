import React from 'react';
import mkEditableField from "./mkEditableField";


const FloatField = mkEditableField({rx: /^(\d+(.\d*)?)|(\d*.\d+)$/, xs: 4});
export default FloatField;
