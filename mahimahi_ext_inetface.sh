#!/bin/bash
ip a | grep link- | grep mtu | awk -F': ' '{print $2}' | awk -F':' '{print $1}'