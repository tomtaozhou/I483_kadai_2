from machine import I2C
import time

_I2C_ADDR = 0x38

_REG_MODE_CONTROL    = 0x41
_REG_ALS_PS_CONTROL  = 0x42
_REG_DATA0_LSB       = 0x46
_REG_MANUFACT_ID     = 0x92

_MANUFACT_ID_EXPECTED = 0xE0

_MODE_CONTROL_INIT   = 0x89
_ALS_PS_CONTROL_INIT = 0x02


class RPR0521RS:
    def __init__(self, i2c, addr=_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr
        self._t_als_ms = 400
        self._g0 = 1
        self._g1 = 1
        self._alpha = 1.0
        self._init_sensor()

    def _init_sensor(self):
        mid = self.i2c.readfrom_mem(self.addr, _REG_MANUFACT_ID, 1)[0]
        if mid != _MANUFACT_ID_EXPECTED:
            raise RuntimeError("RPR-0521RS not detected: 0x{:02X}".format(mid))

        self.i2c.writeto_mem(self.addr, _REG_MODE_CONTROL, bytes([0x00]))
        time.sleep_ms(50)

        self.i2c.writeto_mem(self.addr, _REG_MODE_CONTROL,
                             bytes([_MODE_CONTROL_INIT, _ALS_PS_CONTROL_INIT]))

        time.sleep_ms(500)

    def reinit(self):
        try:
            self._init_sensor()
            return True
        except Exception as e:
            print("RPR0521 reinit failed:", e)
            return False

    def read_raw(self):
        b = self.i2c.readfrom_mem(self.addr, _REG_DATA0_LSB, 4)
        data0 = b[0] | (b[1] << 8)
        data1 = b[2] | (b[3] << 8)
        return data0, data1

    def _normalize(self, data0, data1):
        t_scale = 100.0 / self._t_als_ms
        d0n = (data0 / self._g0) * t_scale
        d1n = (data1 / self._g1) * t_scale
        return d0n, d1n

    def read_lux(self):
        data0, data1 = self.read_raw()
        if data0 == 0:
            return 0.0
        d0n, d1n = self._normalize(data0, data1)
        return d0n * self._alpha

    def calibrate_with(self, reference_lux, samples=5):
        if reference_lux < 1:
            return self._alpha
        d0_sum = 0
        for _ in range(samples):
            d0, d1 = self.read_raw()
            d0n, _ = self._normalize(d0, d1)
            d0_sum += d0n
            time.sleep_ms(450)
        d0_avg = d0_sum / samples
        if d0_avg < 1:
            return self._alpha
        self._alpha = reference_lux / d0_avg
        return self._alpha