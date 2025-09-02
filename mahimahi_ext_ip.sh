#!/bin/bash
ip a | grep "inet " | grep link | awk '{print $2}'