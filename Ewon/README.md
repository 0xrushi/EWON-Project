To test page switch on nextion display

```
import struct
import serial
port = serial.Serial(
    port='/dev/ttyS0',
    baudrate =9600,
    parity=serial.PARITY_NONE)

eof = struct.pack('B', 0xff)
port.write("page 1".encode())
port.write(eof)
port.write(eof)
port.write(eof)
```


To test text on nextion display, `pip install nextion`

```
import asyncio
import logging
import random

from nextion import Nextion, EventType

class App:
    def __init__(self):
        self.client = Nextion('/dev/ttyS0', 9600, self.event_handler)

    # Note: async event_handler can be used only in versions 1.8.0+ (versions 1.8.0+ supports both sync and async versions)
    async def event_handler(self, type_, data):
        if type_ == EventType.STARTUP:
            print('We have booted up!')
        elif type_ == EventType.TOUCH:
            print('A button (id: %d) was touched on page %d' % (data.component_id, data.page_id))

        logging.info('Event %s data: %s', type, str(data))

        print(await self.client.get('t0.txt'))

    async def run(self):
        await self.client.connect()

        # await client.sleep()
        # await client.wakeup()

        # await client.command('sendxy=0')

        print(await self.client.get('sleep'))
        print(await self.client.get('t0.txt'))

        await self.client.set('t0.txt', 'hello')

        print('finished')

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler()
        ])
    loop = asyncio.get_event_loop()
    app = App()
    asyncio.ensure_future(app.run())
    loop.run_forever()
```
