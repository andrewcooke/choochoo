
const pause_ms = 1000;
let timeout;

let data = {};


const close = self.close;

self.close = () => {
  write();
  close();
};


function queue(event) {
    Object.entries(event.data).forEach(([key, value]) => {
        console.log(`queue ${key}:${value}`);
        data[key] = value;
    });
}


function write() {

    function onError(response) {
        response.text().then((msg) => console.log(msg));
    }

    function onSuccess(response) {
        data = {};
        console.log('written');
    }

    if (Object.keys(data).length > 0) {
        Object.entries(data).forEach(([key, value]) => {
            console.log(`write ${key}:${value}`);
        });
        fetch('/api/statistics', {method: 'post', body: JSON.stringify(data)})
            .then((response) => {
                if (response.ok) {
                    onSuccess(response);
                } else {
                    onError(response);
                }
            })
            .catch(onError);
    }
}


self.addEventListener('message', (event) => {
    if (timeout !== undefined) clearTimeout(timeout);
    queue(event);
    timeout = setTimeout(write, pause_ms);
});
