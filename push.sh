#!/bin/bash

if [ "$(whoami)" != "antihabit" ]; then
    chmod a+rX -R $(dirname $0)
    sudo -u antihabit env $0
    # todo: restart service here too
else
    echo "I'm $(whoami)!"
    cd ~antihabit/
    if [ -d laptoplocker/ ]; then
        cd laptoplocker/ && git fetch origin && git reset --hard origin/master
    else
        git clone ~lahwran/laptoplocker laptoplocker/
        cd laptoplocker/
    fi
    sudo launchctl unload /Library/LaunchAgents/net.lahwran.sleepenforcer.plist
    sudo launchctl load /Library/LaunchAgents/net.lahwran.sleepenforcer.plist
    tail -f ~antihabit/laptoplocker/log
fi
