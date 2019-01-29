# cannot

Small python3 library to encode/decode CAN bus messages.

```py
from cannot.dbcfile import J1939DBC

j1939 = J1939DBC.from_file(flags.dbc)  
id = 0x18f00430
data = b'\xFF\xFF\xFF\x68\x13\xFF\xFF'
decoding = j1939.decode(id, data)
assert decoding.message.id == 61444
assert decoding.message.name == 'EEC1'
assert decoding.params['EngSpeed'] == 621
```
