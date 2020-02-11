import React from 'react';
import mkfield from "./mkfield";


const ScoreField = mkfield({rx: /^\d?$/, xs: 4, md: 2});
export default ScoreField;
