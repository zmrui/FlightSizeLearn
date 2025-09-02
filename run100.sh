#!/bin/bash

for ML in ON OFF
do
    for cca in bbr cubic
    do
        for reorder in reorder
        do
            for bw in 1 10 50 100
            do
                for rtt in 1 10 50 100 
                do
                    echo -n $cca > cca_control
                    echo -n $reorder > reorder_control
                    echo -n $bw > bw_control
                    echo -n $rtt > rtt_control
                    echo -n $ML > ML_control    
                    for i in {1..100}
                    do
                        echo "++++++++Run $cca $reorder $bw $rtt $ML started++++++++"
                        echo "++++++++Run $i started++++++++"
                        ./boot_kvm_script.sh
                        echo "++++++++Run $i finished++++++++"
                    done
                done
            done
        done
    done
done

