# FreeMASTER Lite Configuration File Examples

Reference for `freemaster-lite-configuration-file`. Load on demand when a complete or advanced configuration example is needed.

---

## Full configuration

```json
{
  "port": 8090,
  "host": "0.0.0.0",
  "web_root": "./html/",
  "open_path": "/",
  "mock_api": false,
  "connections": [
    {
      "connection_string": "RS232;port=COM3;speed=115200",
      "name": "Main UART",
      "description": "S32K344 EVB",
      "elf": "C:/workspace/my_project/Debug/my_project.elf"
    }
  ],
  "variables": [
    {
      "name": "myVar",
      "addr": 536870912,
      "type": "uint",
      "size": 4
    }
  ],
  "ssl": {
    "key": "C:/certs/server.key",
    "cert": "C:/certs/server.crt"
  }
}
```

---

## TCP/IP (NET plugin)

```json
{
  "port": 8090,
  "connections": [
    {
      "connection_string": "NET;192.168.1.50;port=3344;timeout=500;type=TCP",
      "name": "Remote target via TCP",
      "elf": "C:/workspace/my_project/Debug/my_project.elf"
    }
  ]
}
```

---

## CAN plugin

```json
{
  "port": 8090,
  "connections": [
    {
      "connection_string": "CAN;drv=vector;port=1;bitrate=500000;cmdid=0x7aa;rspid=0x7aa;tmo=500",
      "name": "CAN via Vector"
    }
  ]
}
```

---

## RS232 timeout customization

All timeout values are in milliseconds. Defaults are shown:

| Option | Default |
|--------|---------|
| `tmoRI` (Read Interval Timeout) | 40 |
| `tmoRTM` (Read Total Timeout Multiplier) | 40 |
| `tmoRTC` (Read Total Timeout Constant) | 50 |
| `tmoWTM` (Write Total Timeout Multiplier) | 40 |
| `tmoWTC` (Write Total Timeout Constant) | 50 |

Example with custom timeouts:
```
RS232;port=COM3;speed=115200;tmoRI=100;tmoRTC=200
```

---

## Dirs (file system access rules)

```json
{
  "port": 8090,
  "dirs": [
    {
      "path": "C:/workspace/my_project/assets",
      "exts": ["json", "csv"],
      "opts": "r"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `path` | Absolute or relative (to config file) directory path |
| `exts` | Comma-separated string or array of allowed extensions |
| `opts` | Node.js file system flags: `r` (read), `w` (write), etc. |

---

## Fractional variable

```json
{
  "name": "motorTorque",
  "addr": "0x20005000",
  "type": "fract",
  "size": 4,
  "q_m": 1,
  "q_n": 30
}
```

`q_m + q_n` must equal `8 * size - 1` for `fract` (here 31) or `8 * size` for `ufract` (here 32).
