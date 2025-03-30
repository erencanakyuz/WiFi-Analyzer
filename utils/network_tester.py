"""
Network Tester Module

This module provides functions for testing network performance including ping, 
packet loss measurement, jitter calculation, throughput estimation, and DNS resolution testing.
"""

import subprocess
import re
import socket
import time
import statistics
import logging
import threading
from typing import Dict, List, Tuple, Optional, Union, Any
import urllib.request
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class NetworkTester:
    """
    A class to handle various network performance tests.
    
    This class provides methods for testing network performance, including
    ping tests, packet loss measurement, jitter calculation, throughput
    estimation, and DNS resolution speed testing.
    """
    
    def __init__(self):
        """Initialize the NetworkTester."""
        self.recent_results = {}
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 60  # seconds
        self.monitor_history = []
        self.monitor_callback = None
    
    def ping_test(self, target: str = '8.8.8.8', count: int = 4, 
                 timeout: int = 1000, size: int = 32) -> Dict[str, Any]:
        """
        Perform a ping test to measure latency and packet loss.
        
        Args:
            target: The host to ping (IP or hostname)
            count: Number of ping packets to send
            timeout: Timeout in milliseconds
            size: Size of the ping packet in bytes
            
        Returns:
            Dictionary containing:
                - min_latency: Minimum round-trip time in ms
                - max_latency: Maximum round-trip time in ms
                - avg_latency: Average round-trip time in ms
                - packet_loss: Packet loss percentage
                - packets_sent: Number of packets sent
                - packets_received: Number of packets received
                - jitter: Jitter (variation in latency) in ms
                - success: Whether the test was successful
                - error: Error message if the test failed
        """
        result = {
            'min_latency': None,
            'max_latency': None,
            'avg_latency': None,
            'packet_loss': 100,
            'packets_sent': count,
            'packets_received': 0,
            'jitter': None,
            'success': False,
            'error': None
        }
        
        try:
            # Windows ping command with specific parameters
            cmd = ['ping', '-n', str(count), '-w', str(timeout), '-l', str(size), target]
            
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            # Check for basic connectivity failure
            if process.returncode != 0:
                result['error'] = f"Ping failed with return code {process.returncode}"
                return result
            
            # Extract data from ping output
            output = process.stdout
            
            # Extract packet loss
            loss_match = re.search(r'(\d+)% loss', output)
            if loss_match:
                result['packet_loss'] = int(loss_match.group(1))
                result['packets_received'] = count - int(count * result['packet_loss'] / 100)
            
            # Extract latency statistics
            stats_match = re.search(r'Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms', output)
            if stats_match:
                result['min_latency'] = int(stats_match.group(1))
                result['max_latency'] = int(stats_match.group(2))
                result['avg_latency'] = int(stats_match.group(3))
                
                # If we have min and max, we can estimate jitter
                result['jitter'] = (result['max_latency'] - result['min_latency']) / 2
                
                result['success'] = True
            else:
                # If we couldn't extract stats but the command succeeded,
                # it might mean all packets were lost
                result['error'] = "Could not parse ping statistics"
                if result['packet_loss'] == 100:
                    result['error'] = "100% packet loss"
            
            # Store the recent result
            self.recent_results['ping'] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error during ping test: {str(e)}")
            result['error'] = str(e)
            return result
    
    def dns_resolution_test(self, hostnames: List[str] = None) -> Dict[str, Any]:
        """
        Test DNS resolution speed for a list of hostnames.
        
        Args:
            hostnames: List of hostnames to resolve, defaults to popular websites
            
        Returns:
            Dictionary containing:
                - avg_time: Average resolution time in ms
                - min_time: Minimum resolution time in ms
                - max_time: Maximum resolution time in ms
                - success_rate: Percentage of successful resolutions
                - results: List of individual resolution results
        """
        if hostnames is None:
            hostnames = ['www.google.com', 'www.amazon.com', 'www.microsoft.com', 
                        'www.apple.com', 'www.github.com']
        
        results = []
        success_count = 0
        resolution_times = []
        
        for hostname in hostnames:
            start_time = time.time()
            try:
                socket.gethostbyname(hostname)
                end_time = time.time()
                elapsed_ms = (end_time - start_time) * 1000
                resolution_times.append(elapsed_ms)
                results.append({
                    'hostname': hostname,
                    'success': True,
                    'time_ms': elapsed_ms
                })
                success_count += 1
            except socket.gaierror:
                results.append({
                    'hostname': hostname,
                    'success': False,
                    'time_ms': None
                })
        
        result = {
            'avg_time': statistics.mean(resolution_times) if resolution_times else None,
            'min_time': min(resolution_times) if resolution_times else None,
            'max_time': max(resolution_times) if resolution_times else None,
            'success_rate': (success_count / len(hostnames) * 100) if hostnames else 0,
            'results': results
        }
        
        # Store the recent result
        self.recent_results['dns'] = result
        
        return result
    
    def throughput_test(self, url: str = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db',
                        timeout: int = 10) -> Dict[str, Any]:
        """
        Estimate download throughput by downloading a file.
        
        Args:
            url: URL of the file to download
            timeout: Timeout in seconds
            
        Returns:
            Dictionary containing:
                - speed_mbps: Download speed in Mbps
                - size_bytes: Size of the downloaded file in bytes
                - time_seconds: Time taken to download in seconds
                - success: Whether the test was successful
                - error: Error message if the test failed
        """
        result = {
            'speed_mbps': None,
            'size_bytes': None,
            'time_seconds': None,
            'success': False,
            'error': None
        }
        
        try:
            start_time = time.time()
            response = urllib.request.urlopen(url, timeout=timeout)
            data = response.read()
            end_time = time.time()
            
            size_bytes = len(data)
            time_seconds = end_time - start_time
            speed_bps = (size_bytes * 8) / time_seconds
            speed_mbps = speed_bps / 1_000_000
            
            result['speed_mbps'] = round(speed_mbps, 2)
            result['size_bytes'] = size_bytes
            result['time_seconds'] = round(time_seconds, 2)
            result['success'] = True
            
            # Store the recent result
            self.recent_results['throughput'] = result
            
        except Exception as e:
            logger.error(f"Error during throughput test: {str(e)}")
            result['error'] = str(e)
        
        return result
    
    def check_gateway_connectivity(self) -> Dict[str, Any]:
        """
        Check connectivity to the default gateway.
        
        Returns:
            Dictionary containing:
                - gateway_ip: IP address of the default gateway
                - reachable: Whether the gateway is reachable
                - latency: Round-trip time to the gateway in ms
                - error: Error message if the test failed
        """
        result = {
            'gateway_ip': None,
            'reachable': False,
            'latency': None,
            'error': None
        }
        
        try:
            # Get default gateway IP (Windows-specific command)
            gateway_cmd = ['ipconfig']
            gateway_output = subprocess.run(gateway_cmd, capture_output=True, text=True, check=True).stdout
            
            gateway_match = re.search(r'Default Gateway . . . . . . . . . : (\d+\.\d+\.\d+\.\d+)', gateway_output)
            if gateway_match:
                gateway_ip = gateway_match.group(1)
                result['gateway_ip'] = gateway_ip
                
                # Ping the gateway
                ping_result = self.ping_test(target=gateway_ip, count=1)
                result['reachable'] = ping_result['success']
                result['latency'] = ping_result['avg_latency']
                
                if not result['reachable']:
                    result['error'] = "Gateway is not reachable"
            else:
                result['error'] = "Could not determine default gateway"
        
        except Exception as e:
            logger.error(f"Error checking gateway connectivity: {str(e)}")
            result['error'] = str(e)
        
        # Store the recent result
        self.recent_results['gateway'] = result
        
        return result
    
    def start_monitoring(self, interval: int = 60, 
                        callback: Optional[callable] = None) -> bool:
        """
        Start background monitoring of network performance.
        
        Args:
            interval: Time between tests in seconds
            callback: Function to call with results after each test
            
        Returns:
            Boolean indicating whether monitoring was successfully started
        """
        if self.monitoring:
            return False
        
        self.monitoring = True
        self.monitor_interval = interval
        self.monitor_callback = callback
        
        def monitor_thread_func():
            while self.monitoring:
                try:
                    results = {
                        'timestamp': datetime.now(),
                        'ping': self.ping_test(),
                        'dns': self.dns_resolution_test(),
                        'gateway': self.check_gateway_connectivity()
                    }
                    
                    # Add to history (limit to last 100 entries to avoid memory issues)
                    self.monitor_history.append(results)
                    if len(self.monitor_history) > 100:
                        self.monitor_history.pop(0)
                    
                    # Call callback if provided
                    if self.monitor_callback is not None:
                        try:
                            self.monitor_callback(results)
                        except Exception as e:
                            logger.error(f"Error in monitoring callback: {str(e)}")
                    
                except Exception as e:
                    logger.error(f"Error during network monitoring: {str(e)}")
                
                # Sleep for the interval
                time.sleep(self.monitor_interval)
        
        self.monitor_thread = threading.Thread(target=monitor_thread_func)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Stop background monitoring of network performance.
        
        Returns:
            Boolean indicating whether monitoring was successfully stopped
        """
        if not self.monitoring:
            return False
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            self.monitor_thread = None
        
        return True
    
    def is_monitoring(self) -> bool:
        """
        Check if monitoring is currently active.
        
        Returns:
            Boolean indicating whether monitoring is active
        """
        return self.monitoring
    
    def get_monitoring_history(self) -> List[Dict[str, Any]]:
        """
        Get historical monitoring data.
        
        Returns:
            List of monitoring results
        """
        return self.monitor_history.copy()
    
    def calculate_jitter(self, ping_results: List[float]) -> float:
        """
        Calculate jitter from a series of ping results.
        
        Jitter is calculated as the mean deviation of latency differences.
        
        Args:
            ping_results: List of ping latencies in ms
            
        Returns:
            Jitter value in ms
        """
        if len(ping_results) < 2:
            return 0
        
        # Calculate differences between consecutive pings
        differences = [abs(ping_results[i] - ping_results[i-1]) 
                     for i in range(1, len(ping_results))]
        
        # Jitter is the average of these differences
        return sum(differences) / len(differences)
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """
        Run a comprehensive network test including all available tests.
        
        Returns:
            Dictionary with results from all tests
        """
        results = {
            'timestamp': datetime.now(),
            'ping': self.ping_test(),
            'dns': self.dns_resolution_test(),
            'gateway': self.check_gateway_connectivity(),
            'throughput': self.throughput_test()
        }
        
        return results