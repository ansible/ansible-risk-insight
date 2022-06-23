set -eo pipefail

SECURITY_UPGRADES=$(apt-show-versions | grep upgradeable | grep security | awk -F':' '{print $1}')
HELD_SECURITY_UPGRADES=$(sort <(echo "$SECURITY_UPGRADES") <(apt-mark showhold) | uniq -d)

if [ ! -z "$HELD_SECURITY_UPGRADES" ]; then
    EXTERNAL_ADDRESS=$(ip route get 8.8.8.8 | awk '{print $NF; exit}')
    echo "Warning: The following packages on host $EXTERNAL_ADDRESS are held packages (and thus can not be upgraded automatically), but also have security upgrades available(!):"
    echo "$HELD_SECURITY_UPGRADES"
fi
