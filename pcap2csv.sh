# https://github.com/NUS-SNL/Nebby/blob/e21e193af884375e3cf0b8abcca3fa147f5a5993/analysis/pcap2csv.sh

if [ $# -eq 0 ]
then
echo "This scripts converts .pcap files to a more parse-able .csv format." 
echo "To convert X.pcap to X.csv, run './pcap2csv.sh X' "
exit
fi


echo -e "[${green}Converting recv data to .csv format${plain}]"
#Create seperate traces for TCP and UDP traffic
tshark -r $1 -T fields -o "gui.column.format:\"Time\",\"%Aut\"" -e _ws.col.Time -e frame.time_relative -e tcp.time_relative -e frame.number -e frame.len -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport -e tcp.len -e tcp.seq -e tcp.ack -e tcp.options.timestamp.tsval -e tcp.options.timestamp.tsecr -E header=y -E separator=, -E quote=d -E occurrence=f > $1-tcp.csv
tshark -r $1 -f "udp" > $1-udp.csv
#rm $1