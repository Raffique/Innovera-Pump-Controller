from pump_station import PumpStation

if __name__ == "__main__":
    # Station 1 (river pump)
    station1 = PumpStation(station_id=1, control_pump=True, has_tank=False)

    # Station 2 (intermediate station)
    #station2 = PumpStation(station_id=2, control_pump=True, has_tank=True)

    # Station 3 (monitoring only)
    #station3 = PumpStation(station_id=3, control_pump=False, has_tank=True)