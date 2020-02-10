import React from 'react';
import {mkfield} from "./field";


const IntegerField = mkfield(/^\d*$/);
export default IntegerField;
