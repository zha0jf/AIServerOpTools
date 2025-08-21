#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced InfiniBand Traffic Monitor
===============================

An enhanced tool to monitor InfiniBand traffic on AI servers with improved UI.
"""

import argparse
import subprocess
import time
import sys
from datetime import datetime
from prettytable import PrettyTable


def get_ib_interfaces():
    """Get list of InfiniBand interfaces."""
    try:
        result = subprocess.run(['ibstat', '-p'], capture_output=True, text=True, check=True)
        interfaces = result.stdout.strip().split('\n')
        return [iface for iface in interfaces if iface]
    except subprocess.CalledProcessError:
        print("Error: Unable to get InfiniBand interfaces. Make sure 'ibstat' is installed and accessible.")
        return []


def get_ib_lid_port():
    """Get LID and port information for InfiniBand interfaces."""
    lid_port_info = {}
    try:
        ibstat = subprocess.Popen("ibstat", stdout=subprocess.PIPE).stdout.readlines()
        ibstat = [x.decode("utf-8") for x in ibstat]
        
        for index, line in enumerate(ibstat):
            line = line.strip()
            match = re.match("Port [0-9]\:", line)
            if match:
                number = line.split(' ')[1].replace(':', '')
                state = ibstat[index+1].split(':')[1].strip()
                an = re.match("Active", state)
                if an:
                    lid = ibstat[index+4].split(':')[1].strip()
                    lid_port_info[lid] = number
        return lid_port_info
    except Exception as e:
        print(f"Error getting LID/port info: {e}")
        return {}


def get_ib_traffic(interface):
    """Get traffic statistics for a specific InfiniBand interface."""
    try:
        # Get port counters
        result = subprocess.run(['perfquery', f'{interface}:1'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        # Parse relevant counters
        port_xmit_data = None
        port_rcv_data = None
        
        for line in lines:
            if 'PortXmitData:' in line:
                port_xmit_data = int(line.split(':')[1].strip())
            elif 'PortRcvData:' in line:
                port_rcv_data = int(line.split(':')[1].strip())
        
        return port_xmit_data, port_rcv_data
    except subprocess.CalledProcessError:
        print(f"Error: Unable to get traffic data for interface {interface}")
        return None, None


def format_bytes(bytes_count):
    """Format bytes count to human readable format."""
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PiB"


def monitor_ib_traffic(interfaces, interval=1, show_lid=False):
    """Monitor InfiniBand traffic on specified interfaces with enhanced UI."""
    # Initialize previous values
    prev_values = {}
    for iface in interfaces:
        xmit, rcv = get_ib_traffic(iface)
        if xmit is not None and rcv is not None:
            prev_values[iface] = (xmit, rcv)
    
    try:
        while True:
            # Create a PrettyTable for display
            table = PrettyTable()
            if show_lid:
                lid_info = get_ib_lid_port()
                table.field_names = ["Interface", "LID", "Port", "TX Rate", "RX Rate", "Total TX", "Total RX"]
            else:
                table.field_names = ["Interface", "TX Rate", "RX Rate", "Total TX", "Total RX"]
            
            for iface in interfaces:
                xmit, rcv = get_ib_traffic(iface)
                if xmit is not None and rcv is not None:
                    if iface in prev_values:
                        prev_xmit, prev_rcv = prev_values[iface]
                        
                        # Calculate rates (data is in 4-byte units)
                        tx_rate = (xmit - prev_xmit) * 4 / interval
                        rx_rate = (rcv - prev_rcv) * 4 / interval
                        
                        # Format values
                        tx_rate_str = format_bytes(tx_rate) + "/s"
                        rx_rate_str = format_bytes(rx_rate) + "/s"
                        total_tx_str = format_bytes(xmit * 4)
                        total_rx_str = format_bytes(rcv * 4)
                        
                        # Add row to table
                        if show_lid:
                            # Simplified LID lookup
                            lid = "N/A"
                            for l, p in lid_info.items():
                                if p == "1":  # Simplified matching
                                    lid = l
                                    break
                            table.add_row([iface, lid, "1", tx_rate_str, rx_rate_str, total_tx_str, total_rx_str])
                        else:
                            table.add_row([iface, tx_rate_str, rx_rate_str, total_tx_str, total_rx_str])
                    
                    # Update previous values
                    prev_values[iface] = (xmit, rcv)
            
            # Clear screen and display table
            print("\033[2J\033[H", end='')  # Clear screen
            print(f"InfiniBand Traffic Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            print(table)
            print("\nPress Ctrl+C to stop monitoring.")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


def main():
    parser = argparse.ArgumentParser(description='Enhanced InfiniBand traffic monitor')
    parser.add_argument('-i', '--interval', type=int, default=1, 
                        help='Monitoring interval in seconds (default: 1)')
    parser.add_argument('-I', '--interface', type=str, 
                        help='Specific InfiniBand interface to monitor (default: all)')
    parser.add_argument('--lid', action='store_true',
                        help='Show LID information')
    
    args = parser.parse_args()
    
    # Get interfaces to monitor
    if args.interface:
        interfaces = [args.interface]
    else:
        interfaces = get_ib_interfaces()
        if not interfaces:
            print("No InfiniBand interfaces found.")
            sys.exit(1)
    
    # Start monitoring
    monitor_ib_traffic(interfaces, args.interval, args.lid)


if __name__ == "__main__":
    main()