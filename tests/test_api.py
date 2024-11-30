from src.api import API

async def test_get_data():
    api = API("192.168.1.54")
    data = await api.get_data()
    assert data is not None

async def test_set_speed():
    api = API("192.168.1.54")
    assert await api.set_speed(1500)

async def test_turn_on():
    api = API("192.168.1.54")
    assert await api.turn_on()

async def test_turn_off():
    api = API("192.168.1.54")
    assert await api.turn_off()

async def test_get_schedules():
    api = API("192.168.1.54")
    schedules = await api.get_schedules()
    assert schedules is not None
