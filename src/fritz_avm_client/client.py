"""Fritz!Box client with extended functionality."""
from typing import Dict, Any, List, Optional
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzstatus import FritzStatus
from fritzconnection.lib.fritzwlan import FritzWLAN

from .config import Settings


class FritzClient:
    """Extended Fritz!Box client with advanced metrics and mesh topology support.
    
    This client extends the basic fritzconnection library with:
    - CPU temperature monitoring (requires authentication)
    - Real-time transmission rates
    - DSL quality metrics (attenuation, noise margin)
    - Enhanced mesh topology discovery
    - WLAN device-to-AP mapping
    
    Example:
        >>> from fritz_avm_client import FritzClient, Settings
        >>> settings = Settings(fritz_host="192.168.178.1", fritz_password="secret")
        >>> client = FritzClient(settings)
        >>> wan_stats = client.get_wan_stats()
        >>> print(f"Download: {wan_stats['current_download_rate']} bytes/sec")
    """

    def __init__(self, settings: Settings):
        """Initialize Fritz!Box client.
        
        Args:
            settings: Settings instance with connection parameters
        """
        self.settings = settings
        self.fc = FritzConnection(
            address=settings.fritz_host,
            port=settings.fritz_port,
            user=settings.fritz_username,
            password=settings.fritz_password,
        )
        self.hosts = FritzHosts(self.fc)
        self.status = FritzStatus(self.fc)
        self.wlan = FritzWLAN(self.fc)

    def get_all_hosts(self) -> List[Dict[str, Any]]:
        """Get all hosts from Fritz!Box.
        
        Returns:
            List of host dictionaries with device information
        """
        return self.hosts.get_hosts_info()

    def get_mesh_info(self) -> Optional[Dict[str, Any]]:
        """Get mesh topology information.
        
        Returns:
            Dictionary with mesh topology data, or None if unavailable
        """
        try:
            return self.hosts.get_mesh_topology()
        except Exception:
            return None

    def get_device_stats(self, mac_address: str) -> Dict[str, int]:
        """Get traffic statistics for a specific device by MAC address.
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            Dictionary with rx_bytes and tx_bytes
        """
        try:
            result = self.fc.call_action(
                'Hosts1', 
                'GetSpecificHostEntry', 
                NewMACAddress=mac_address
            )
            return {
                'rx_bytes': result.get('NewX_AVM-DE_RxBytes', 0),
                'tx_bytes': result.get('NewX_AVM-DE_TxBytes', 0),
            }
        except Exception:
            return {'rx_bytes': 0, 'tx_bytes': 0}

    def get_wan_stats(self) -> Dict[str, Any]:
        """Get comprehensive WAN statistics including real-time rates.
        
        Returns comprehensive dictionary with:
            - current_download_rate: Real-time download speed (bytes/sec)
            - current_upload_rate: Real-time upload speed (bytes/sec)
            - total_bytes_sent: Total bytes sent since last reset
            - total_bytes_received: Total bytes received since last reset
            - max_downstream_rate: Line capacity download (bytes/sec)
            - max_upstream_rate: Line capacity upload (bytes/sec)
            - connection_uptime: Connection uptime in seconds
            - device_uptime: Device uptime in seconds
            - external_ip: External IP address
            - is_connected: Connection status
            - attenuation: DSL line attenuation (downstream, upstream) in dB
            - noise_margin: DSL signal quality (downstream, upstream) in dB
            - cpu_temperatures: Dictionary of CPU temperatures {cpu_name: temp_celsius}
        
        Example:
            >>> stats = client.get_wan_stats()
            >>> print(f"Download: {stats['current_download_rate']} bytes/sec")
            >>> print(f"DSL SNR: {stats['noise_margin'][0]} dB")
            >>> for cpu, temp in stats['cpu_temperatures'].items():
            ...     print(f"{cpu}: {temp}°C")
        """
        try:
            # Get current transmission rates (bytes/sec)
            current_rates = self.status.transmission_rate
            
            # Get connection uptime (different from device uptime)
            connection_uptime = getattr(self.status, 'connection_uptime', 0)
            
            # Get external IP
            external_ip = getattr(self.status, 'external_ip', '')
            
            # Get DSL line quality metrics
            attenuation = self.status.attenuation
            noise_margin = self.status.noise_margin
            
            return {
                'total_bytes_sent': self.status.bytes_sent or 0,
                'total_bytes_received': self.status.bytes_received or 0,
                'max_upstream_rate': self.status.max_byte_rate[1] if self.status.max_byte_rate else 0,
                'max_downstream_rate': self.status.max_byte_rate[0] if self.status.max_byte_rate else 0,
                'current_download_rate': current_rates[0] if current_rates else 0,
                'current_upload_rate': current_rates[1] if current_rates else 0,
                'device_uptime': getattr(self.status, 'device_uptime', 0),
                'connection_uptime': connection_uptime,
                'is_connected': self.status.is_connected,
                'external_ip': external_ip,
                'attenuation': (
                    attenuation[0] if attenuation else 0,
                    attenuation[1] if attenuation else 0
                ),
                'noise_margin': (
                    noise_margin[0] if noise_margin else 0,
                    noise_margin[1] if noise_margin else 0
                ),
                'cpu_temperatures': self.get_cpu_temperatures(),
            }
        except Exception as e:
            # Return safe defaults on error
            return {
                'total_bytes_sent': 0,
                'total_bytes_received': 0,
                'max_upstream_rate': 0,
                'max_downstream_rate': 0,
                'current_download_rate': 0,
                'current_upload_rate': 0,
                'device_uptime': 0,
                'connection_uptime': 0,
                'is_connected': False,
                'external_ip': '',
                'attenuation': (0, 0),
                'noise_margin': (0, 0),
                'cpu_temperatures': {},
            }

    def get_cpu_temperatures(self) -> Dict[str, float]:
        """Get CPU temperature readings (requires authentication).
        
        Note: Not all Fritz!Box models support temperature readings.
        Requires admin authentication.
        
        Returns:
            Dictionary mapping CPU names to temperatures in Celsius
            Example: {'cpu0': 65.0, 'cpu1': 66.5, 'cpu2': 64.0}
        """
        try:
            temps = self.status.get_cpu_temperatures()
            if temps:
                result = {}
                for i, temp in enumerate(temps):
                    result[f'cpu{i}'] = temp
                return result
        except Exception:
            # Authentication required or not supported
            pass
        return {}

    def get_wlan_traffic_stats(self) -> Dict[str, int]:
        """Get WiFi interface traffic statistics.
        
        Works on both routers and repeaters.
        
        Returns:
            Dictionary with total_packets_sent and total_packets_received
        """
        wlan_stats = {}
        try:
            for service_id in range(1, 5):
                try:
                    service_name = f'WLANConfiguration{service_id}'
                    result = self.fc.call_action(service_name, 'GetStatistics')
                    
                    if service_id == 1:
                        wlan_stats = {
                            'total_packets_sent': result.get('NewTotalPacketsSent', 0),
                            'total_packets_received': result.get('NewTotalPacketsReceived', 0),
                        }
                    else:
                        wlan_stats['total_packets_sent'] += result.get('NewTotalPacketsSent', 0)
                        wlan_stats['total_packets_received'] += result.get('NewTotalPacketsReceived', 0)
                except Exception:
                    continue
        except Exception:
            pass
        return wlan_stats

    def get_wlan_devices(self) -> List[Dict[str, Any]]:
        """Get all devices connected via WLAN with their associated access point MAC.
        
        This maps WiFi clients to their access points (useful for mesh networks).
        
        Returns:
            List of dictionaries with:
                - device_mac: Client device MAC address
                - ap_mac: Access point MAC address
                - ip: Device IP address
                - signal_strength: WiFi signal strength
                - speed: Connection speed (Mbps)
                - service: WLAN service name
        """
        wlan_devices = []
        try:
            for service_id in range(1, 5):
                try:
                    service_name = f'WLANConfiguration{service_id}'
                    
                    # Get number of associated devices
                    result = self.fc.call_action(service_name, 'GetTotalAssociations')
                    total = result.get('NewTotalAssociations', 0)
                    
                    # Get BSSID (MAC address of this access point)
                    bssid_result = self.fc.call_action(service_name, 'GetInfo')
                    ap_mac = bssid_result.get('NewBSSID', '')
                    
                    # Get each associated device
                    for i in range(total):
                        try:
                            device_info = self.fc.call_action(
                                service_name,
                                'GetGenericAssociatedDeviceInfo',
                                NewAssociatedDeviceIndex=i
                            )
                            
                            device_mac = device_info.get('NewAssociatedDeviceMACAddress', '')
                            if device_mac:
                                wlan_devices.append({
                                    'device_mac': device_mac,
                                    'ap_mac': ap_mac,
                                    'service': service_name,
                                    'ip': device_info.get('NewAssociatedDeviceIPAddress', ''),
                                    'signal_strength': device_info.get('NewX_AVM-DE_SignalStrength', 0),
                                    'speed': device_info.get('NewX_AVM-DE_Speed', 0),
                                })
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
        return wlan_devices
