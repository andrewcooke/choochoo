import React from 'react';
import mkfield from "./mkfield";


const ScoreField = mkfield({rx: /^\d?$/, xs: 4});
export default ScoreField;
