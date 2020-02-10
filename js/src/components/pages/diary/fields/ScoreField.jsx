import React from 'react';
import mkfield from "./mkfield";


const ScoreField = mkfield({rx: /^\d?$/, sm: 4, md: 2});
export default ScoreField;
