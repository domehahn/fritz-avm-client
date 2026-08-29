"""Example usage of fritz-avm-client library."""
from fritz_avm_client import FritzClient, MeshDiscovery, Settings


def main():
    """Demonstrate basic usage of the library."""

    # Initialize client with settings
    settings = Settings(
        fritz_host="192.168.178.1",
        fritz_username="admin",  # Optional, required for CPU temps
        fritz_password="your-password"  # Optional
    )

    client = FritzClient(settings)

    # 1. Get WAN Statistics
    print("=" * 60)
    print("WAN Statistics")
    print("=" * 60)
    wan_stats = client.get_wan_stats()

    # Real-time speeds
    download_mbps = (wan_stats['current_download_rate'] * 8) / 1_000_000
    upload_mbps = (wan_stats['current_upload_rate'] * 8) / 1_000_000
    print(f"Download: {download_mbps:.2f} Mbps")
    print(f"Upload: {upload_mbps:.2f} Mbps")

    # Connection info
    print(f"External IP: {wan_stats['external_ip']}")
    print(f"Connected: {wan_stats['is_connected']}")
    print(f"Connection Uptime: {wan_stats['connection_uptime']} seconds")

    # DSL Quality
    downstream_atten, upstream_atten = wan_stats['attenuation']
    downstream_snr, upstream_snr = wan_stats['noise_margin']
    print(f"\nDSL Quality:")
    print(f"  Downstream: Attenuation {downstream_atten} dB, SNR {downstream_snr} dB")
    print(f"  Upstream: Attenuation {upstream_atten} dB, SNR {upstream_snr} dB")

    # 2. Get CPU Temperatures (requires authentication)
    print("\n" + "=" * 60)
    print("CPU Temperatures")
    print("=" * 60)
    cpu_temps = wan_stats['cpu_temperatures']
    if cpu_temps:
        for cpu, temp in cpu_temps.items():
            print(f"{cpu}: {temp}°C")
    else:
        print("CPU temperatures not available (authentication required or not supported)")

    # 3. Discover Mesh Network
    print("\n" + "=" * 60)
    print("Mesh Network Topology")
    print("=" * 60)

    discovery = MeshDiscovery(client)
    nodes, devices = discovery.discover()

    print(f"Found {len(nodes)} mesh nodes:")
    for node in nodes:
        node_type = "Router" if node.is_router else "Repeater" if node.is_repeater else "Powerline"
        parent_info = f" (parent: {node.parent_node})" if node.parent_node else " (root)"
        print(f"  {node.name} ({node.mac}) - {node_type}{parent_info}")

    # 4. Show Connected Devices
    print(f"\n{len(devices)} total devices:")
    online_devices = [d for d in devices if d.online]
    print(f"  {len(online_devices)} online")

    # Group devices by connection point
    devices_by_node = {}
    for device in online_devices:
        node_name = device.connected_node or "Unknown"
        if node_name not in devices_by_node:
            devices_by_node[node_name] = []
        devices_by_node[node_name].append(device)

    print(f"\nDevices grouped by connection point:")
    for node_name, node_devices in sorted(devices_by_node.items()):
        print(f"\n  {node_name} ({len(node_devices)} devices):")
        for device in node_devices[:5]:  # Show max 5 per node
            traffic = ""
            if device.rx_bytes_total and device.tx_bytes_total:
                rx_mb = device.rx_bytes_total / 1_000_000
                tx_mb = device.tx_bytes_total / 1_000_000
                traffic = f" - RX: {rx_mb:.1f} MB, TX: {tx_mb:.1f} MB"
            print(f"    - {device.name} ({device.ip}){traffic}")
        if len(node_devices) > 5:
            print(f"    ... and {len(node_devices) - 5} more")

    # 5. WLAN Statistics
    print("\n" + "=" * 60)
    print("WLAN Statistics")
    print("=" * 60)
    wlan_stats = client.get_wlan_traffic_stats()
    if wlan_stats:
        print(f"Total packets sent: {wlan_stats.get('total_packets_sent', 0):,}")
        print(f"Total packets received: {wlan_stats.get('total_packets_received', 0):,}")


if __name__ == "__main__":
    main()
