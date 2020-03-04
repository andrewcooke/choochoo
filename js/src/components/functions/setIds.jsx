
export default function setIds(json, id=0) {
    json.id = id;
    if (Array.isArray(json)) {
        id = json.reduce((acc, row) => setIds(row, acc), id+1);
    }
    return id+1;
}
