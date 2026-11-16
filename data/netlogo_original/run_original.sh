#!/bin/sh
# usage: NETLOGO=/path/to/NetLogo_Console ./run_original.sh [threads]
set -e
here=$(cd "$(dirname "$0")" && pwd)
threads="${1:-4}"
: "${NETLOGO:?set NETLOGO to the NetLogo_Console executable}"
[ -f "$here/tables/Organized_Anarchy.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Organized Anarchy" --threads "$threads" --table "$here/tables/Organized_Anarchy.csv"
[ -f "$here/tables/Organized_Anarchy_P.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Organized Anarchy P" --threads "$threads" --table "$here/tables/Organized_Anarchy_P.csv"
[ -f "$here/tables/Organized_Anarchy_BP.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Organized Anarchy BP" --threads "$threads" --table "$here/tables/Organized_Anarchy_BP.csv"
[ -f "$here/tables/Organized_Anarchy_P_and_BP.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Organized Anarchy P+BP" --threads "$threads" --table "$here/tables/Organized_Anarchy_P_and_BP.csv"
[ -f "$here/tables/Competent_Hierarchy.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Competent Hierarchy" --threads "$threads" --table "$here/tables/Competent_Hierarchy.csv"
[ -f "$here/tables/Competent_Hierarchy_P.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Competent Hierarchy P" --threads "$threads" --table "$here/tables/Competent_Hierarchy_P.csv"
[ -f "$here/tables/Competent_Hierarchy_BP.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Competent Hierarchy BP" --threads "$threads" --table "$here/tables/Competent_Hierarchy_BP.csv"
[ -f "$here/tables/Competent_Hierarchy_P_and_BP.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Competent Hierarchy P+BP" --threads "$threads" --table "$here/tables/Competent_Hierarchy_P_and_BP.csv"
[ -f "$here/tables/Incompetent_Hierarchy.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Incompetent Hierarchy" --threads "$threads" --table "$here/tables/Incompetent_Hierarchy.csv"
[ -f "$here/tables/Incompetent_Hierarchy_P.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Incompetent Hierarchy P" --threads "$threads" --table "$here/tables/Incompetent_Hierarchy_P.csv"
[ -f "$here/tables/Incompetent_Hierarchy_BP.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Incompetent Hierarchy BP" --threads "$threads" --table "$here/tables/Incompetent_Hierarchy_BP.csv"
[ -f "$here/tables/Incompetent_Hierarchy_P_and_BP.csv" ] || "$NETLOGO" --headless --model "$here/GarbageCan_simplified17_headless.nlogox" --experiment "Incompetent Hierarchy P+BP" --threads "$threads" --table "$here/tables/Incompetent_Hierarchy_P_and_BP.csv"
