import React from 'react';
import mkEditableField from "./mkEditableField";


const ScoreField = mkEditableField({rx: /^\d?$/, xs: 4});
export default ScoreField;
