# Fritz!Box AVM Client

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Extended Python client for AVM Fritz!Box routers with support for:
- 📊 **Advanced Metrics**: CPU temperatures, DSL quality, real-time transmission rates
- 🌐 **Mesh Topology Discovery**: Automatic discovery of repeaters, powerline adapters
- 🔐 **Authentication Support**: Access protected metrics like CPU temperature
- 📈 **Prometheus Ready**: Designed for monitoring and observability

This library extends [fritzconnection](https://github.com/kbr/fritzconnection) with additional features specifically for monitoring and network topology visualization.

## Features

### ✨ Beyond Standard fritzconnection

- **CPU Temperature Monitoring** (requires authentication)
- **Real-time Transmission Rates** (bytes/sec, not just totals)
- **DSL Quality Metrics** (attenuation, noise margin)
- **Connection Uptime** (separate from device uptime)
- **Mesh Hierarchy Discovery** (parent-child relationships)
- **Device-to-Node Mapping** (which device connects to which repeater)
- **Typed Data Models** (Pydantic models for type safety)

## Installation

```bash
pip install fritz-avm-client
```

## Quick Start

```python
from fritz_avm_client import FritzClient, Settings

# Initialize client
settings = Settings(
    fritz_host="192.168.178.1",
    fritz_username="your-username",
    fritz_password="your-password"
)
client = FritzClient(settings)

# Get WAN statistics with real-time rates
wan_stats = client.get_wan_stats()
print(f"Download: {wan_stats['current_download_rate']} bytes/sec")
print(f"Upload: {wan_stats['current_upload_rate']} bytes/sec")
print(f"External IP: {wan_stats['external_ip']}")

# Get CPU temperatures (requires authentication)
cpu_temps = client.get_cpu_temperatures()
for cpu, temp in cpu_temps.items():
    print(f"{cpu}: {temp}°C")

# Get mesh topology
mesh_info = client.get_mesh_info()
print(f"Found {len(mesh_info['nodes'])} mesh nodes")
```

## Advanced Usage

### Mesh Network Discovery

```python
from fritz_avm_client import MeshDiscovery

discovery = MeshDiscovery(client)
nodes, devices = discovery.discover()

# Iterate mesh nodes (router, repeaters, powerline)
for node in nodes:
    print(f"{node.name} ({node.mac})")
    print(f"  IP: {node.ip}")
    print(f"  Type: {'Router' if node.is_router else 'Repeater' if node.is_repeater else 'Powerline'}")
    print(f"  Parent: {node.parent_node}")

# Iterate client devices
for device in devices:
    print(f"{device.name} - {device.ip}")
    print(f"  Connected to: {device.connected_node}")
    print(f"  RX: {device.rx_bytes_total}, TX: {device.tx_bytes_total}")
```

### DSL Quality Monitoring

```python
wan_stats = client.get_wan_stats()

# DSL line quality metrics
downstream_atten, upstream_atten = wan_stats['attenuation']
downstream_noise, upstream_noise = wan_stats['noise_margin']

print(f"Downstream attenuation: {downstream_atten} dB")
print(f"Downstream SNR margin: {downstream_noise} dB")
```

### All Available Metrics

```python
wan_stats = client.get_wan_stats()

# Returns dictionary with:
{
    'current_download_rate': int,      # bytes/sec (real-time)
    'current_upload_rate': int,        # bytes/sec (real-time)
    'total_bytes_sent': int,
    'total_bytes_received': int,
    'max_downstream_rate': int,        # bytes/sec (line capacity)
    'max_upstream_rate': int,          # bytes/sec (line capacity)
    'connection_uptime': int,          # seconds
    'device_uptime': int,              # seconds
    'external_ip': str,
    'is_connected': bool,
    'attenuation': tuple[int, int],    # (downstream, upstream) in dB
    'noise_margin': tuple[int, int],   # (downstream, upstream) in dB
}
```

## Data Models

The library provides typed data models using Pydantic:

```python
from fritz_avm_client.models import Node, Device

# Node represents mesh infrastructure (router, repeater, powerline)
node = Node(
    name="Living Room Repeater",
    mac="AA:BB:CC:DD:EE:FF",
    ip="192.168.178.50",
    is_router=False,
    is_repeater=True,
    is_powerline=False,
    extra={},
    parent_node="Router"
)

# Device represents client devices (phone, TV, etc.)
device = Device(
    name="iPhone",
    mac="11:22:33:44:55:66",
    ip="192.168.178.100",
    online=True,
    interface_type="wlan",
    connected_node="Living Room Repeater",
    rx_bytes_total=1024000,
    tx_bytes_total=512000
)
```

## Configuration

Using Pydantic Settings:

```python
from fritz_avm_client import Settings

settings = Settings(
    fritz_host="192.168.178.1",
    fritz_port=49000,
    fritz_username="admin",
    fritz_password="secret",
    fritz_use_tls=False
)
```

Or via environment variables:

```bash
export FRITZ_HOST=192.168.178.1
export FRITZ_USERNAME=admin
export FRITZ_PASSWORD=secret
```

## Requirements

- Python 3.9+
- Fritz!Box with TR-064 enabled (default: enabled)
- For CPU temperatures: Fritz!Box user with admin rights

## Tested Devices

- ✅ Fritz!Box 7590 AX
- ✅ Fritz!Repeater 6000
- ✅ Fritz!Repeater 3000 AX
- ✅ Fritz!Powerline 1260E

Should work with most Fritz!Box models that support TR-064 protocol.

## Comparison with fritzconnection

| Feature | fritzconnection | fritz-avm-client |
|---------|----------------|------------------|
| Basic device info | ✅ | ✅ |
| WAN statistics | ✅ (totals only) | ✅ (+ real-time rates) |
| CPU temperatures | ❌ | ✅ |
| DSL quality metrics | ❌ | ✅ |
| Mesh hierarchy | ❌ | ✅ |
| Device-to-node mapping | ❌ | ✅ |
| Typed models | ❌ | ✅ (Pydantic) |
| Prometheus ready | ❌ | ✅ |

## Use Cases

- **Home Network Monitoring**: Track internet speed, device connections
- **Prometheus Exporters**: Ready-to-use metrics for Grafana dashboards
- **Network Topology Visualization**: Build interactive network graphs
- **Smart Home Integration**: Presence detection, bandwidth monitoring
- **Troubleshooting**: DSL quality, connection stability monitoring

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built on top of the excellent [fritzconnection](https://github.com/kbr/fritzconnection) library by Klaus Bremer.

## Support

- 📝 [Documentation](https://github.com/domehahn/fritz-avm-client)
- 🐛 [Issue Tracker](https://github.com/domehahn/fritz-avm-client/issues)
- 💬 [Discussions](https://github.com/domehahn/fritz-avm-client/discussions)
