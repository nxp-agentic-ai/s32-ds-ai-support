# FreeMASTER Web Application Examples

Reference for `freemaster-lite-web-application`. Load on demand when a complete HTML page, Node.js script, or async/await pattern is needed.

---

## Complete HTML page — start communication and read a variable

```html
<html>
<head>
  <script type="text/javascript" src="/simple-jsonrpc-js.js"></script>
  <script type="text/javascript" src="/freemaster-client.js"></script>
</head>
<body onload="init()">
  <p id="status">Connecting...</p>
  <script type="text/javascript">
    var pcm;

    function init() {
      pcm = new PCM('127.0.0.1:8090', on_connect);
    }

    function on_connect() {
      document.getElementById('status').textContent = 'Connected';
      pcm.StartComm('RS232;port=COM3;speed=115200')
        .then(() => pcm.IsBoardDetected())
        .then(() => pcm.GetDetectedBoardInfo())
        .then(r => {
          document.getElementById('status').textContent =
            'Board: ' + JSON.stringify(r.data);
        })
        .catch(e => {
          document.getElementById('status').textContent = 'Error: ' + e;
        });
    }
  </script>
</body>
</html>
```

---

## Polling a variable periodically

```javascript
function on_connect() {
  pcm.StartComm('RS232;port=COM3;speed=115200')
    .then(() => setInterval(poll, 500));
}

function poll() {
  pcm.ReadVariable('g_motorSpeed')
    .then(r => console.log('speed:', r.data))
    .catch(e => console.warn('read failed:', e));
}
```

---

## Defining a variable dynamically then reading it

```javascript
pcm.DefineVariable({
  name: 'g_speed',
  addr: '0x20004040',
  type: 'float',
  size: 4
})
.then(() => pcm.GetVariableInfo('g_speed'))
.then(r => console.log('var info:', r.data))
.then(() => pcm.ReadVariable('g_speed'))
.then(r => console.log('value:', r.data))
.catch(e => console.error(e));
```

---

## Writing a variable

```javascript
pcm.WriteVariable('g_kp', 1.5)
  .then(() => pcm.ReadVariable('g_kp'))
  .then(r => console.log('confirmed kp =', r.data))
  .catch(e => console.error('write failed:', e));
```

> WriteVariable modifies live target memory. Confirm with the user before writing safety-critical variables.

---

## async/await pattern

```javascript
async function run() {
  await pcm.StartComm('RS232;port=COM3;speed=115200');
  const board = await pcm.GetDetectedBoardInfo();
  console.log('board:', board.data);
  await pcm.ReadELF();
  const val = await pcm.ReadVariable('g_motorSpeed');
  console.log('speed:', val.data);
}

// Call from on_connect:
function on_connect() { run().catch(console.error); }
```

---

## Node.js (npm package)

```javascript
const { PCM } = require('freemaster-client');

const pcm = new PCM('127.0.0.1:8090', async () => {
  await pcm.StartComm('RS232;port=COM3;speed=115200');
  const r = await pcm.ReadVariable('g_speed');
  console.log('speed:', r.data);
});
```

The npm package is located in the FreeMASTER installation root directory when **FreeMASTER Node.js Modules** was selected during installation.

---

## Mock API (no hardware)

Start FreeMASTER Lite with `--mock_api` or `mock_api: true` in the `.fmcfg` file. All PCM calls resolve with mock responses — no physical target needed.

```javascript
// Works identically with mock — PCM API is unchanged
pcm.ReadVariable('g_speed').then(r => console.log(r.data));
```
