from influxdb.connection import write_data
from influxdb_client import Point
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

def create_point(measurement: str, tags: Dict[str, str], fields: Dict[str, Any], timestamp: Optional[datetime] = None) -> Point:
    """
    Helper function to create a structured InfluxDB Point.
    """
    point = Point(measurement)
    for k, v in tags.items():
        point.tag(k, v)
    for k, v in fields.items():
        point.field(k, v)
    if timestamp:
        point.time(timestamp)
    else:
        point.time(datetime.utcnow())
    return point

def write_sensor_data(
    measurement: str,
    device_id: str,
    sensor_data: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    High-level handler to transform sensor data into Point and write to InfluxDB.

    :param measurement: Measurement name (e.g., 'WaterLevelSensor')
    :param device_id: ID of the device/sensor
    :param sensor_data: Dictionary of fields, e.g., {"water_level": 45.3}
    :param timestamp: Optional timestamp
    :return: Tuple of (success: bool, result: str, error: str)
    """
    try:
        point = create_point(
            measurement=measurement,
            tags={"device_id": device_id},
            fields=sensor_data,
            timestamp=timestamp
        )
        write_data(point)
        return True, "Data successfully written", None
    except Exception as e:
        return False, None, str(e)
