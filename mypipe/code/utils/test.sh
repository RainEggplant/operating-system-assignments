echo -e '\e[31;1m* Generating random data file\e[m'
dd if=/dev/urandom of=test64M bs=64M count=1 iflag=fullblock

echo -e '\n\e[31;1m* Sending data file through mypipe\e[m'
dd if=test64M of=/dev/mypipe_in bs=64M count=1 iflag=fullblock &
dd if=/dev/mypipe_out of=recv64M bs=64M count=1 iflag=fullblock
wait

echo -e '\n\e[31;1m* Showing SHA256 of generated and received file\e[m'
sha256sum test64M recv64M

rm test64M recv64M
