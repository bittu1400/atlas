#!/bin/bash
# Mock script to generate dummy mp4
output_file=$1
duration=$2
ffmpeg -y -f lavfi -i color=c=blue:s=1080x1920:d=$duration -c:v libx264 "$output_file" > /dev/null 2>&1
