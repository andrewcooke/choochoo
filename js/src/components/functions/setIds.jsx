
export default function setIds(json, id=0, keys=null) {
    json.id = id;
    if (Array.isArray(json)) {
        id = json.reduce((acc, row) => setIds(row, acc, keys), id);
    } else {
        Object.keys(json).forEach(key => {
            if (keys !== null && keys.includes(key)) {
                id = setIds(json[key], id, keys);
            }
        })
    }
    return id+1;
}
